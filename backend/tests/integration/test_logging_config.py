"""logging_config 검증 — 등급 B. 대응: docs/P0_설계서_Common.md 6절, 요구사항 FR-18~FR-19."""

from __future__ import annotations

import json
import logging

import pytest

from youtube_learner.config import Settings
from youtube_learner.logging_config import ContextLoggerAdapter, setup_logging


@pytest.fixture(autouse=True)
def _restore_root_logger():
    """테스트가 루트 로거를 바꾸므로 끝나면 원상복구한다 (pytest 자체 로깅과 충돌 방지)."""
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    yield
    for handler in list(root.handlers):
        root.removeHandler(handler)
    for handler in saved_handlers:
        root.addHandler(handler)
    root.setLevel(saved_level)


def _settings(tmp_settings: Settings, **override) -> Settings:
    return Settings(data_dir=tmp_settings.data_dir, status_dir=tmp_settings.status_dir, **override)


class TestSetupLogging:
    def test_json_line_fields_and_korean(self, tmp_settings: Settings, capsys: pytest.CaptureFixture[str]):
        """FR-18 — 한 줄 JSON, UTC Z, extra 병합, 한국어 그대로."""
        setup_logging(tmp_settings)
        logging.getLogger("youtube_learner.test").info("채널 동기화 %s", "시작", extra={"yt_video_id": "L81RWsnY-vY"})
        line = capsys.readouterr().out.strip().splitlines()[-1]
        payload = json.loads(line)
        assert payload["level"] == "INFO" and payload["logger"] == "youtube_learner.test"
        assert payload["message"] == "채널 동기화 시작"
        assert payload["timestamp"].endswith("Z") and "T" in payload["timestamp"]
        assert payload["yt_video_id"] == "L81RWsnY-vY"
        assert "채널 동기화" in line  # ensure_ascii=False

    def test_text_format(self, tmp_settings: Settings, capsys: pytest.CaptureFixture[str]):
        setup_logging(_settings(tmp_settings, log_format="text"))
        logging.getLogger("x").warning("경고 메시지", extra={"stage": "sync"})
        line = capsys.readouterr().out.strip().splitlines()[-1]
        assert "WARNING" in line and "경고 메시지" in line and '"stage": "sync"' in line
        with pytest.raises(json.JSONDecodeError):
            json.loads(line)

    def test_idempotent_single_handler(self, tmp_settings: Settings):
        """FR-18 — 두 번 호출해도 핸들러 1개 (중복 출력 방지)."""
        setup_logging(tmp_settings)
        setup_logging(tmp_settings)
        assert len(logging.getLogger().handlers) == 1

    def test_level_applied(self, tmp_settings: Settings, capsys: pytest.CaptureFixture[str]):
        setup_logging(_settings(tmp_settings, log_level="WARNING"))
        logging.getLogger("x").info("보이지 않아야")
        logging.getLogger("x").warning("보여야")
        out = capsys.readouterr().out
        assert "보이지 않아야" not in out and "보여야" in out

    def test_exception_info_included(self, tmp_settings: Settings, capsys: pytest.CaptureFixture[str]):
        setup_logging(tmp_settings)
        try:
            raise ValueError("boom")
        except ValueError:
            logging.getLogger("x").exception("실패")
        payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert "ValueError: boom" in payload["exc_info"]


class TestContextLoggerAdapter:
    def test_merges_context_and_call_extra(self, tmp_settings: Settings, capsys: pytest.CaptureFixture[str]):
        """FR-19 — 표준 어댑터는 호출부 extra 를 덮어쓴다. 우리는 병합한다."""
        setup_logging(tmp_settings)
        adapter = ContextLoggerAdapter(logging.getLogger("x"), {"run_id": "r1", "stage": "sync"})
        adapter.info("msg", extra={"yt_video_id": "v"})
        payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert payload["run_id"] == "r1" and payload["stage"] == "sync" and payload["yt_video_id"] == "v"

    def test_call_extra_wins_on_same_key(self, tmp_settings: Settings, capsys: pytest.CaptureFixture[str]):
        setup_logging(tmp_settings)
        adapter = ContextLoggerAdapter(logging.getLogger("x"), {"stage": "a"})
        adapter.info("msg", extra={"stage": "b"})
        assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["stage"] == "b"

    def test_reserved_key_gets_prefix(self, tmp_settings: Settings, capsys: pytest.CaptureFixture[str]):
        """FR-19 — LogRecord 예약 이름(name·message …)과 충돌하면 ctx_ 접두."""
        setup_logging(tmp_settings)
        adapter = ContextLoggerAdapter(logging.getLogger("x"), {"name": "충돌", "message": "충돌2"})
        adapter.info("본문")
        payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert payload["message"] == "본문" and payload["ctx_name"] == "충돌" and payload["ctx_message"] == "충돌2"

    def test_bind_accumulates(self):
        adapter = ContextLoggerAdapter(logging.getLogger("x"), {"run_id": "r"})
        child = adapter.bind(yt_video_id="v").bind(stage="s")
        assert child.extra == {"run_id": "r", "yt_video_id": "v", "stage": "s"}
        assert adapter.extra == {"run_id": "r"}  # 원본 불변
