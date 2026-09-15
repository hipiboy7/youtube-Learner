"""단계 실행 기록 — 대응: docs/P0_설계서_Common.md 7절 (FR-20~FR-21). 등급 A.

진입 즉시 status/<stage>_<run_id>.json 에 started 를 쓰고, 끝나면 succeeded|failed 로 완결한다.
다른 실행이 같은 파일을 쓰려 하면 OutputExistsError (CLAUDE.md 6절). 예외는 기록 후 재전파 — 종료 코드는 CLI 가 정한다.
"""

from __future__ import annotations

import json
import logging
import re
import secrets
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from youtube_learner.config import Settings
from youtube_learner.constants import PACKAGE_NAME, PIPELINE_VERSION, STAGE_NAME_PATTERN, STATUS_FILENAME_PATTERN
from youtube_learner.exceptions import OutputExistsError
from youtube_learner.logging_config import ContextLoggerAdapter

_STAGE_RE = re.compile(STAGE_NAME_PATTERN)


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_run_id(now: datetime | None = None) -> str:
    """`YYYYMMDD-HHMMSS-<8 hex>` (UTC). now 주입은 테스트용."""
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    return f"{moment.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(4)}"


def status_path(settings: Settings, stage: str, run_id: str) -> Path:
    """상태 파일 경로. stage 는 파일명에 들어가므로 [a-z0-9_] 만 허용한다."""
    if not _STAGE_RE.fullmatch(stage):
        raise ValueError(f"stage 이름은 소문자·숫자·밑줄만 허용한다: {stage!r}")
    return settings.status_dir / STATUS_FILENAME_PATTERN.format(stage=stage, run_id=run_id)


def _dump(record: Mapping[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def read_status(path: Path) -> dict[str, Any]:
    """상태 파일을 읽는다. 없으면 FileNotFoundError."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


@contextmanager
def run_context(
    stage: str,
    settings: Settings,
    logger: logging.Logger | None = None,
    *,
    run_id: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> Iterator[tuple[str, ContextLoggerAdapter]]:
    """단계 하나의 실행을 감싼다. (run_id, 컨텍스트 로거) 를 내준다.

    Raises:
        ValueError: stage 이름 규칙 위반 (파일을 만들기 전에 검사).
        OutputExistsError: 같은 run_id 의 상태 파일이 이미 있다.
    """
    resolved_run_id = run_id or new_run_id()
    path = status_path(settings, stage, resolved_run_id)
    settings.status_dir.mkdir(parents=True, exist_ok=True)

    started = datetime.now(UTC)
    record: dict[str, Any] = {
        "stage": stage,
        "run_id": resolved_run_id,
        "status": "started",
        "started_at": _iso(started),
        "finished_at": None,
        "duration_s": None,
        "error": None,
        "pipeline_version": PIPELINE_VERSION,
        "extra": dict(extra or {}),
    }
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:  # "x": 있으면 실패 — 덮어쓰기 금지
            handle.write(_dump(record))
    except FileExistsError:
        raise OutputExistsError(path) from None

    base_logger = logger or logging.getLogger(PACKAGE_NAME)
    adapter = ContextLoggerAdapter(base_logger, {"run_id": resolved_run_id, "stage": stage})
    adapter.info("단계 시작")

    def _finish(status: str, error: dict[str, str] | None) -> None:
        finished = datetime.now(UTC)
        record.update(
            status=status,
            finished_at=_iso(finished),
            duration_s=round((finished - started).total_seconds(), 3),
            error=error,
        )
        path.write_text(_dump(record), encoding="utf-8", newline="\n")

    try:
        yield resolved_run_id, adapter
    except BaseException as exc:
        _finish("failed", {"type": type(exc).__name__, "message": str(exc)})
        adapter.error("단계 실패", extra={"error_type": type(exc).__name__})
        raise
    else:
        _finish("succeeded", None)
        adapter.info("단계 완료", extra={"duration_s": record["duration_s"]})
