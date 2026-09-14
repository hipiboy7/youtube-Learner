"""config 검증 — 등급 B. 대응: docs/P0_설계서_Common.md 3절, 요구사항 FR-1~FR-5, FR-33."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from youtube_learner.config import Settings, get_settings, load_json_config, resource_root
from youtube_learner.exceptions import ConfigError

ROOT = Path(__file__).resolve().parents[3]  # 저장소 루트


class TestDefaults:
    def test_defaults(self, tmp_settings: Settings):
        """FR-1 — 기본값."""
        assert tmp_settings.log_level == "INFO" and tmp_settings.log_format == "json"
        assert tmp_settings.api_host == "127.0.0.1" and tmp_settings.api_port == 8765
        assert tmp_settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]
        assert tmp_settings.ytdlp_js_runtime == "node"
        assert tmp_settings.bgutil_http_enabled is False
        assert tmp_settings.stt_cpu_threads == (os.cpu_count() or 1)
        assert tmp_settings.analyzers == []
        assert tmp_settings.disk_free_warn_gb == 10

    def test_paths_are_absolute_and_tilde_expanded(self, tmp_settings: Settings):
        """FR-2 — 파생 경로는 절대경로, ~ 는 홈으로."""
        assert tmp_settings.data_dir.is_absolute() and tmp_settings.status_dir.is_absolute()
        assert "~" not in str(tmp_settings.bgutil_script_path)
        assert tmp_settings.bgutil_script_path.is_absolute()

    def test_derived_paths(self, tmp_settings: Settings):
        assert tmp_settings.db_path == tmp_settings.data_dir / "youtube_learner.db"
        assert tmp_settings.channels_dir == tmp_settings.data_dir / "channels"
        assert tmp_settings.models_dir == tmp_settings.data_dir / "models"  # HF_HOME 미설정 → DATA_DIR/models

    def test_hf_home_override(self, tmp_path: Path, tmp_settings: Settings):
        s = Settings(data_dir=tmp_settings.data_dir, status_dir=tmp_settings.status_dir, hf_home=tmp_path / "hf")
        assert s.models_dir == (tmp_path / "hf").resolve()

    def test_resource_root_is_backend_dir_with_config(self):
        root = resource_root()
        assert root.name == "backend" and (root / "config").is_dir()

    def test_resolved_config_dir_default(self, tmp_settings: Settings):
        assert tmp_settings.resolved_config_dir == resource_root() / "config"


class TestDotEnv:
    def test_reads_dot_env_from_cwd(self, tmp_path: Path, tmp_settings: Settings):
        """FR-1 — .env 로딩. 빈 값(HF_HOME=)은 미설정으로 본다."""
        (tmp_path / ".env").write_text(
            "DATA_DIR=./mydata\nAPI_PORT=9000\nCORS_ORIGINS=http://a,http://b\nHF_HOME=\nLOG_FORMAT=text\n"
            "ANALYZERS=\nSTT_CPU_THREADS=\n",
            encoding="utf-8",
        )
        s = get_settings()
        assert s.data_dir == (tmp_path / "mydata").resolve()
        assert s.api_port == 9000
        assert s.cors_origins == ["http://a", "http://b"]
        assert s.hf_home is None and s.models_dir == s.data_dir / "models"
        assert s.log_format == "text"
        assert s.analyzers == [] and s.stt_cpu_threads >= 1

    def test_env_var_overrides_dot_env(self, tmp_path: Path, tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch):
        (tmp_path / ".env").write_text("API_PORT=9000\n", encoding="utf-8")
        monkeypatch.setenv("API_PORT", "9100")
        assert get_settings().api_port == 9100

    def test_unknown_keys_ignored(self, tmp_path: Path, tmp_settings: Settings):
        (tmp_path / ".env").write_text("NOT_A_KEY=1\n", encoding="utf-8")
        get_settings()  # 예외 없음


class TestRejects:
    """FR-4 — 잘못된 값은 로딩 시점에 거부한다."""

    @pytest.mark.parametrize(
        ("key", "value"),
        [
            ("LOG_LEVEL", "TRACE"),
            ("LOG_FORMAT", "xml"),
            ("API_PORT", "0"),
            ("API_PORT", "70000"),
            ("STT_CPU_THREADS", "0"),
            ("DISK_FREE_WARN_GB", "-1"),
        ],
    )
    def test_invalid_values(self, tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch, key: str, value: str):
        monkeypatch.setenv(key, value)
        with pytest.raises(ValidationError):
            get_settings()


class TestSideEffects:
    def test_ensure_dirs(self, tmp_settings: Settings):
        """FR-3."""
        tmp_settings.ensure_dirs()
        assert tmp_settings.data_dir.is_dir() and tmp_settings.status_dir.is_dir() and tmp_settings.models_dir.is_dir()
        tmp_settings.ensure_dirs()  # 멱등

    def test_apply_process_env(self, tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch):
        """FR-3 — HF 가 import 시점에 읽는 값을 명시 호출로만 적용한다."""
        for key in ("HF_HOME", "HF_HUB_DISABLE_SYMLINKS_WARNING", "PYTHONUTF8"):
            monkeypatch.delenv(key, raising=False)
        tmp_settings.apply_process_env()
        assert os.environ["HF_HOME"] == str(tmp_settings.models_dir)
        assert os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] == "1"
        assert os.environ["PYTHONUTF8"] == "1"

    def test_constructing_settings_has_no_env_side_effect(self, tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("HF_HOME", raising=False)
        Settings(data_dir=tmp_settings.data_dir, status_dir=tmp_settings.status_dir)
        assert "HF_HOME" not in os.environ


class TestJsonConfig:
    @pytest.mark.parametrize("name", ["stt_default", "ytdlp_default", "sync_default"])
    def test_real_config_files_load_and_strip_comment(self, tmp_settings: Settings, name: str):
        """FR-5·FR-34 — 실제 3종이 _comment 를 갖고 로더를 통과한다."""
        data = load_json_config(name, tmp_settings)
        assert "_comment" not in data and data

    def test_stt_default_values(self, tmp_settings: Settings):
        stt = load_json_config("stt_default", tmp_settings)
        assert stt["model"] == "small" and stt["compute_type"] == "int8" and stt["cpu_threads"] is None
        assert set(stt["presets"]) == {"small", "medium", "large-v3-turbo"} and set(stt["model_repos"]) == set(stt["presets"])

    def test_missing_file(self, tmp_settings: Settings):
        with pytest.raises(ConfigError):
            load_json_config("nope", tmp_settings)

    def test_invalid_json(self, tmp_path: Path, tmp_settings: Settings):
        cfg = tmp_path / "cfg"
        cfg.mkdir()
        (cfg / "bad.json").write_text("{not json", encoding="utf-8")
        s = Settings(data_dir=tmp_settings.data_dir, status_dir=tmp_settings.status_dir, config_dir=cfg)
        with pytest.raises(ConfigError):
            load_json_config("bad", s)

    def test_missing_comment_rejected(self, tmp_path: Path, tmp_settings: Settings):
        """FR-5 — 근거 없는 설정 파일은 거부한다."""
        cfg = tmp_path / "cfg"
        cfg.mkdir()
        (cfg / "nocomment.json").write_text(json.dumps({"model": "small"}), encoding="utf-8")
        s = Settings(data_dir=tmp_settings.data_dir, status_dir=tmp_settings.status_dir, config_dir=cfg)
        with pytest.raises(ConfigError):
            load_json_config("nocomment", s)

    def test_non_object_rejected(self, tmp_path: Path, tmp_settings: Settings):
        cfg = tmp_path / "cfg"
        cfg.mkdir()
        (cfg / "list.json").write_text("[1,2]", encoding="utf-8")
        s = Settings(data_dir=tmp_settings.data_dir, status_dir=tmp_settings.status_dir, config_dir=cfg)
        with pytest.raises(ConfigError):
            load_json_config("list", s)


class TestEnvExample:
    def test_env_example_keys_match_settings_fields(self):
        """FR-33·완료 기준 — .env.example 의 키 집합 == Settings 필드 집합. 키를 추가하면 둘 다 고쳐야 한다."""
        text = (ROOT / ".env.example").read_text(encoding="utf-8")
        keys = {line.split("=", 1)[0].strip() for line in text.splitlines() if line and not line.startswith("#") and "=" in line}
        fields = {name.upper() for name in Settings.model_fields}
        assert keys == fields, f"차이: example-only={keys - fields}, settings-only={fields - keys}"
