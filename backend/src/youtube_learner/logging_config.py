"""JSON 한 줄 로깅 — 대응: docs/P0_설계서_Common.md 6절 (FR-18~FR-19). 등급 B.

stdout 에 한 줄 JSON(운영·사이드카) 또는 사람이 읽는 텍스트(개발). 루트 핸들러를 교체해 중복 출력을 막는다.
외부 로깅 패키지를 쓰지 않는다 — 필드 5개를 내는 데 의존성을 늘릴 이유가 없다.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Mapping, MutableMapping
from datetime import UTC, datetime
from typing import Any

from youtube_learner.config import Settings

#: LogRecord 가 이미 쓰는 이름. extra 가 이 이름을 쓰면 ctx_ 접두를 붙여 충돌을 피한다.
_RESERVED: frozenset[str] = frozenset(
    logging.LogRecord("x", logging.INFO, "", 0, "", None, None).__dict__.keys()
) | {"message", "asctime", "taskName"}

_CONTEXT_TAG = "_ctx_keys"


def _timestamp(record: logging.LogRecord) -> str:
    return datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _extras(record: logging.LogRecord) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _RESERVED and not key.startswith("_")
    }


class JsonFormatter(logging.Formatter):
    """한 줄 JSON: timestamp(UTC, Z) · level · logger · message · extra. 한국어는 그대로(ensure_ascii=False)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": _timestamp(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(_extras(record))
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """개발용: `2026-09-14T04:00:00.000Z INFO    logger  message  {extra}`."""

    def format(self, record: logging.LogRecord) -> str:
        line = f"{_timestamp(record)} {record.levelname:<7} {record.name}  {record.getMessage()}"
        extras = _extras(record)
        if extras:
            line += "  " + json.dumps(extras, ensure_ascii=False, default=str)
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def setup_logging(settings: Settings) -> logging.Logger:
    """루트 로거를 구성한다. 멱등 — 두 번 호출해도 핸들러는 하나다 (uvicorn·huey 중복 출력 방지)."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if settings.log_format == "json" else TextFormatter())
    root.addHandler(handler)
    root.setLevel(settings.log_level)
    return root


class ContextLoggerAdapter(logging.LoggerAdapter):
    """컨텍스트(run_id·stage·yt_video_id)를 extra 에 **병합**한다 — 표준 어댑터는 호출부 extra 를 덮어쓴다."""

    def __init__(self, logger: logging.Logger, context: Mapping[str, Any] | None = None) -> None:
        super().__init__(logger, dict(context or {}))

    def process(self, msg: Any, kwargs: MutableMapping[str, Any]) -> tuple[Any, MutableMapping[str, Any]]:
        merged: dict[str, Any] = {**(self.extra or {}), **(kwargs.get("extra") or {})}
        kwargs["extra"] = {(f"ctx_{key}" if key in _RESERVED else key): value for key, value in merged.items()}
        return msg, kwargs

    def bind(self, **more: Any) -> ContextLoggerAdapter:
        """컨텍스트를 누적한 새 어댑터."""
        return ContextLoggerAdapter(self.logger, {**(self.extra or {}), **more})
