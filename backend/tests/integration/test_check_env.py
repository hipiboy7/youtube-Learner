"""cli/check_env 검증 — 등급 B. 대응: docs/P0_설계서_Common.md 10절, 요구사항 FR-26~FR-27."""

from __future__ import annotations

import json
import subprocess
from collections import namedtuple
from pathlib import Path

import pytest

from youtube_learner.cli import check_env as ce
from youtube_learner.config import Settings

ROOT = Path(__file__).resolve().parents[3]
Usage = namedtuple("Usage", "total used free")


def _completed(stdout: str, code: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["node", "--version"], returncode=code, stdout=stdout, stderr="")


class TestPython:
    def test_ok_in_312_venv(self):
        r = ce.check_python(version=(3, 12, 10), prefix="C:/v", base_prefix="C:/base")
        assert r.level is ce.Level.OK and "3.12.10" in r.detail

    def test_fail_wrong_version(self):
        assert ce.check_python(version=(3, 14, 3), prefix="a", base_prefix="b").level is ce.Level.FAIL

    def test_fail_not_venv(self):
        """FR-26 — 시스템 python(3.12 라도) 은 패키지가 없다."""
        assert ce.check_python(version=(3, 12, 1), prefix="same", base_prefix="same").level is ce.Level.FAIL


class TestImports:
    def test_required_modules_present_here(self):
        results = ce.check_imports()
        assert {r.level for r in results} == {ce.Level.OK}, [r.detail for r in results if r.level is not ce.Level.OK]

    def test_missing_module_fails(self):
        (r,) = ce.check_imports({"definitely_missing_mod_xyz": "x"})
        assert r.level is ce.Level.FAIL and "ModuleNotFoundError" in r.detail


class TestNode:
    def test_ok(self):
        r = ce.check_node(which=lambda _: "C:/nodejs/node.exe", run=lambda *a, **k: _completed("v24.14.0\n"))
        assert r.level is ce.Level.OK and "v24.14.0" in r.detail

    def test_missing_node_fails(self):
        r = ce.check_node(which=lambda _: None)
        assert r.level is ce.Level.FAIL

    def test_old_node_fails(self):
        """FR-26 — Node < 20 은 bgutil·EJS 가 요구하는 버전 미달."""
        r = ce.check_node(which=lambda _: "node", run=lambda *a, **k: _completed("v18.20.0"))
        assert r.level is ce.Level.FAIL and "20" in r.detail

    def test_unreadable_version_fails(self):
        r = ce.check_node(which=lambda _: "node", run=lambda *a, **k: _completed("garbage", code=1))
        assert r.level is ce.Level.FAIL

    def test_run_exception_fails(self):
        def boom(*a, **k):
            raise OSError("cannot exec")

        assert ce.check_node(which=lambda _: "node", run=boom).level is ce.Level.FAIL


class TestBgutil:
    def test_missing_script_fails_with_hint(self, tmp_settings: Settings, tmp_path: Path):
        """완료 기준 — bgutil 스크립트가 없으면 FAIL (T-001 재발 방지)."""
        s = Settings(data_dir=tmp_settings.data_dir, status_dir=tmp_settings.status_dir, bgutil_script_path=tmp_path / "nope.js")
        r = ce.check_bgutil_script(s)
        assert r.level is ce.Level.FAIL and "npm ci" in r.detail

    def test_existing_script_ok(self, tmp_settings: Settings, tmp_path: Path):
        script = tmp_path / "generate_once.js"
        script.write_text("// stub", encoding="utf-8")
        s = Settings(data_dir=tmp_settings.data_dir, status_dir=tmp_settings.status_dir, bgutil_script_path=script)
        assert ce.check_bgutil_script(s).level is ce.Level.OK


class TestPotServer:
    """FR-102 — PO 토큰 상주 서버 검사. 꺼져 있으면 WARN + 띄우는 명령 (T-007)."""

    class _FakeResponse:
        def __init__(self, payload: bytes) -> None:
            self._payload = payload

        def read(self) -> bytes:
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

    def test_ok_when_server_answers_ping(self, tmp_settings: Settings):
        payload = json.dumps({"version": "2.0.0", "server_uptime": 41.7}).encode("utf-8")
        r = ce.check_pot_server(tmp_settings, urlopen=lambda url, timeout: self._FakeResponse(payload))
        assert r.level is ce.Level.OK and "bgutil 2.0.0" in r.detail and "uptime 42s" in r.detail

    def test_warns_with_serve_hint_when_refused(self, tmp_settings: Settings):
        def refuse(url: str, timeout: float):
            raise ConnectionRefusedError("대상 컴퓨터에서 거부했으므로 연결하지 못했습니다")

        r = ce.check_pot_server(tmp_settings, urlopen=refuse)
        assert r.level is ce.Level.WARN and "main.js" in r.detail and "/ping" in r.detail

    def test_warns_when_http_disabled(self, tmp_settings: Settings):
        """거부 케이스 — 끄는 것도 조용히 넘기지 않는다. script 모드의 대가를 알려 준다."""
        s = tmp_settings.model_copy(update={"bgutil_http_enabled": False})
        r = ce.check_pot_server(s, urlopen=lambda *a, **k: pytest.fail("꺼져 있으면 두드리지 않아야 한다"))
        assert r.level is ce.Level.WARN and "T-007" in r.detail

    def test_uses_configured_base_url(self, tmp_settings: Settings):
        seen: list[str] = []

        def capture(url: str, timeout: float):
            seen.append(url)
            return self._FakeResponse(b'{"version":"x"}')

        s = tmp_settings.model_copy(update={"bgutil_http_base_url": "http://127.0.0.1:9999/"})
        ce.check_pot_server(s, urlopen=capture)
        assert seen == ["http://127.0.0.1:9999/ping"]


class TestDirsDiskConfigModels:
    def test_dirs_ok_and_created(self, tmp_settings: Settings):
        r = ce.check_dirs(tmp_settings)
        assert r.level is ce.Level.OK and tmp_settings.models_dir.is_dir()

    def test_disk_ok_and_warn(self, tmp_settings: Settings):
        ok = ce.check_disk(tmp_settings, disk_usage=lambda _: Usage(100 * 1024**3, 0, 50 * 1024**3))
        warn = ce.check_disk(tmp_settings, disk_usage=lambda _: Usage(100 * 1024**3, 0, 2 * 1024**3))
        assert ok.level is ce.Level.OK and warn.level is ce.Level.WARN and "보류 결정 8" in warn.detail

    def test_config_files_ok(self, tmp_settings: Settings):
        results = ce.check_config_files(tmp_settings)
        assert [r.name for r in results] == [f"config {n}" for n in ce.CONFIG_FILES]
        assert {r.level for r in results} == {ce.Level.OK}

    def test_config_missing_fails(self, tmp_settings: Settings, tmp_path: Path):
        s = Settings(data_dir=tmp_settings.data_dir, status_dir=tmp_settings.status_dir, config_dir=tmp_path / "empty")
        assert {r.level for r in ce.check_config_files(s)} == {ce.Level.FAIL}

    def test_model_cache_warn_then_ok(self, tmp_settings: Settings):
        assert ce.check_model_cache(tmp_settings).level is ce.Level.WARN
        (tmp_settings.models_dir / "hub" / "models--Systran--faster-whisper-small").mkdir(parents=True)
        r = ce.check_model_cache(tmp_settings)
        assert r.level is ce.Level.OK and "Systran--faster-whisper-small" in r.detail


class TestRender:
    def test_text_ready(self):
        text, code = ce.render([ce.CheckResult("a", ce.Level.OK, "x"), ce.CheckResult("b", ce.Level.WARN, "y")])
        assert code == 0 and text.splitlines()[-1] == "==> READY"
        assert text.splitlines()[0] == "[OK] a — x"

    def test_text_not_ready_counts_failures(self):
        text, code = ce.render([ce.CheckResult("a", ce.Level.FAIL, "x"), ce.CheckResult("b", ce.Level.FAIL, "y")])
        assert code == 1 and text.splitlines()[-1] == "==> NOT READY (2 failures)"

    def test_strict_turns_warn_into_failure(self):
        _, code = ce.render([ce.CheckResult("b", ce.Level.WARN, "y")], strict=True)
        assert code == 1

    def test_json(self):
        text, code = ce.render([ce.CheckResult("a", ce.Level.OK, "x")], as_json=True)
        payload = json.loads(text)
        assert payload["ready"] is True and payload["results"][0] == {"name": "a", "level": "OK", "detail": "x"}


class TestThisMachine:
    def test_run_checks_has_no_failures_here(self, tmp_settings: Settings):
        """완료 기준 — 이 VM 은 READY 여야 한다 (bgutil 빌드·Node 24·3.12 venv). WARN(디스크·모델 캐시) 은 허용."""
        results = ce.run_checks(tmp_settings)
        failures = [r for r in results if r.level is ce.Level.FAIL]
        assert not failures, [f"{r.name}: {r.detail}" for r in failures]
        text, code = ce.render(results)
        assert code == 0 and text.endswith("==> READY")

    def test_bgutil_removed_makes_not_ready(self, tmp_settings: Settings, tmp_path: Path):
        s = Settings(data_dir=tmp_settings.data_dir, status_dir=tmp_settings.status_dir, bgutil_script_path=tmp_path / "gone.js")
        text, code = ce.render(ce.run_checks(s))
        assert code == 1 and "NOT READY" in text.splitlines()[-1]

    def test_main_json_exit_code(self, tmp_settings: Settings, capsys: pytest.CaptureFixture[str]):
        code = ce.main(["--json"])
        payload = json.loads(capsys.readouterr().out)
        assert code in (0, 1) and payload["ready"] == (code == 0)

    def test_wrapper_script_exists(self):
        """FR-27."""
        assert (ROOT / "scripts" / "check_env.ps1").is_file()
