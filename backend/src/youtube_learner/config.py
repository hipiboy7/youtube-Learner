"""환경별 설정 — 대응: docs/P0_설계서_Common.md 3절 (FR-1~FR-5). 등급 B.

.env 와 환경변수에서 읽는다. 값의 3분류(CLAUDE.md 5절) 중 "환경에 따라 달라지는 값"만 여기 둔다.
파생 경로는 절대경로. 라이브러리가 읽는 환경변수(HF_HOME 등)는 apply_process_env() 를 명시 호출해야 적용된다 —
faster-whisper import 전에 호출하는 것이 계약이다(P2).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from youtube_learner.constants import DB_FILENAME
from youtube_learner.exceptions import ConfigError

_DEFAULT_CORS = ("http://localhost:5173", "http://127.0.0.1:5173")


def _split_csv(value: Any) -> Any:
    """콤마 구분 문자열 → 목록. 이미 목록이면 그대로. 빈 문자열은 빈 목록."""
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


def resource_root() -> Path:
    """리소스(config/ 등)의 루트. 개발: backend/. PyInstaller frozen 번들(P4): 번들 디렉토리."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and frozen_root:
        return Path(frozen_root)
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """환경별 설정. 키 목록은 P0 에서 확정 — 이후 Phase 는 추가만 한다 (FR-1)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # `HF_HOME=` 처럼 비운 키는 미설정으로 본다 → 기본값
        extra="ignore",
        protected_namespaces=(),
        case_sensitive=False,
    )

    data_dir: Path = Path("./data")
    status_dir: Path = Path("./status")
    hf_home: Path | None = None
    config_dir: Path | None = None
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "text"] = "json"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8765, ge=1, le=65535)
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: list(_DEFAULT_CORS))
    ytdlp_js_runtime: str = "node"
    bgutil_script_path: Path = Path("~/bgutil-ytdlp-pot-provider/server/build/generate_once.js")
    bgutil_http_enabled: bool = False
    stt_cpu_threads: int = Field(default_factory=lambda: os.cpu_count() or 1, ge=1)
    analyzers: Annotated[list[str], NoDecode] = Field(default_factory=list)
    disk_free_warn_gb: float = Field(default=10, ge=0)

    @field_validator("cors_origins", "analyzers", mode="before")
    @classmethod
    def _csv_lists(cls, value: Any) -> Any:
        return _split_csv(value)

    @field_validator("data_dir", "status_dir", "hf_home", "config_dir", "bgutil_script_path", mode="after")
    @classmethod
    def _absolute(cls, value: Path | None) -> Path | None:
        if value is None:
            return None
        return Path(value).expanduser().resolve()

    # ── 파생 경로 (FR-2) ──
    @property
    def db_path(self) -> Path:
        return self.data_dir / DB_FILENAME

    @property
    def channels_dir(self) -> Path:
        return self.data_dir / "channels"

    @property
    def models_dir(self) -> Path:
        """Whisper 모델 캐시(HF_HOME). 기본은 DATA_DIR/models — C: 여유·심볼릭 링크 문제 회피 (T-002)."""
        return self.hf_home if self.hf_home is not None else self.data_dir / "models"

    @property
    def resolved_config_dir(self) -> Path:
        return self.config_dir if self.config_dir is not None else resource_root() / "config"

    # ── 부작용 있는 동작 (FR-3) — 명시 호출 ──
    def ensure_dirs(self) -> None:
        """DATA_DIR·STATUS_DIR·HF_HOME 을 만든다. 있으면 무시."""
        for directory in (self.data_dir, self.status_dir, self.models_dir):
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise ConfigError(f"디렉토리를 만들 수 없다: {directory} ({exc})") from exc

    def apply_process_env(self) -> None:
        """라이브러리가 import 시점에 읽는 환경변수를 이 프로세스에 적용한다. faster-whisper import 전에 호출."""
        os.environ["HF_HOME"] = str(self.models_dir)
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        os.environ["PYTHONUTF8"] = "1"


def get_settings() -> Settings:
    """캐시 없음 — 테스트가 환경을 바꿔 여러 번 만든다. 캐시는 API 앱(P1)이 자기 수명 안에서."""
    return Settings()


def load_json_config(name: str, settings: Settings) -> dict[str, Any]:
    """CONFIG_DIR/<name>.json 을 읽는다. "_comment" 필수(근거 동반), 반환값에서는 제거한다 (FR-5)."""
    path = settings.resolved_config_dir / f"{name}.json"
    if not path.is_file():
        raise ConfigError(f"설정 파일이 없다: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"설정 파일을 읽을 수 없다: {path} ({exc})") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"설정 파일의 최상위는 객체여야 한다: {path}")
    if "_comment" not in data:
        raise ConfigError(f"설정 파일에 '_comment'(값의 근거)가 없다: {path}")
    return {key: value for key, value in data.items() if key != "_comment"}
