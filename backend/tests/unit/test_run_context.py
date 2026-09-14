"""workflow/run_context 검증 — 등급 A (테스트 먼저). 대응: docs/P0_설계서_Common.md 7절, 요구사항 FR-20~FR-21."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_learner.constants import PIPELINE_VERSION
from youtube_learner.exceptions import OutputExistsError, YouTubeAccessError
from youtube_learner.workflow.run_context import new_run_id, read_status, run_context, status_path

RUN_ID_RE = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{8}$")


class TestRunId:
    def test_format(self):
        """FR-20 — YYYYMMDD-HHMMSS-<8 hex>."""
        assert RUN_ID_RE.match(new_run_id())

    def test_injected_time_is_used_in_utc(self):
        rid = new_run_id(now=datetime(2026, 9, 14, 4, 30, 0, tzinfo=UTC))
        assert rid.startswith("20260914-043000-")

    def test_two_ids_differ(self):
        assert new_run_id() != new_run_id()


class TestStatusPath:
    def test_uses_pattern_under_status_dir(self, tmp_settings):
        p = status_path(tmp_settings, "sync_channel", "20260914-043000-deadbeef")
        assert p == tmp_settings.status_dir / "sync_channel_20260914-043000-deadbeef.json"

    def test_rejects_bad_stage_name(self, tmp_settings):
        """FR-21 — stage 는 파일명에 들어간다. 공백·한글·슬래시 금지."""
        with pytest.raises(ValueError):
            status_path(tmp_settings, "Sync Channel", "x")


class TestRunContext:
    def test_started_record_written_on_enter(self, tmp_settings):
        """FR-20 — 진입 즉시 started. 강제 종료돼도 흔적이 남는다."""
        with run_context("sync_channel", tmp_settings) as (run_id, logger):
            p = status_path(tmp_settings, "sync_channel", run_id)
            rec = read_status(p)
            assert rec["status"] == "started"
            assert rec["finished_at"] is None and rec["duration_s"] is None and rec["error"] is None
            assert logger is not None

    def test_succeeded_record_on_exit(self, tmp_settings):
        with run_context("sync_channel", tmp_settings, extra={"channel": "세바시"}) as (run_id, _):
            pass
        rec = read_status(status_path(tmp_settings, "sync_channel", run_id))
        assert rec["status"] == "succeeded"
        assert rec["stage"] == "sync_channel" and rec["run_id"] == run_id
        assert rec["finished_at"] is not None and rec["duration_s"] >= 0
        assert rec["pipeline_version"] == PIPELINE_VERSION
        assert rec["extra"] == {"channel": "세바시"}

    def test_failed_record_and_reraise(self, tmp_settings):
        """FR-20 — 예외는 기록 후 재전파. 종료 코드는 CLI 가 정한다."""
        with pytest.raises(YouTubeAccessError):
            with run_context("fetch_transcript", tmp_settings) as (run_id, _):
                raise YouTubeAccessError("429", status=429)
        rec = read_status(status_path(tmp_settings, "fetch_transcript", run_id))
        assert rec["status"] == "failed"
        assert rec["error"] == {"type": "YouTubeAccessError", "message": "429"}
        assert rec["finished_at"] is not None

    def test_refuses_to_overwrite_existing_run(self, tmp_settings):
        """FR-21 — 다른 실행이 같은 파일을 쓰면 OutputExistsError (CLAUDE.md 6절 덮어쓰기 금지)."""
        rid = "20260914-043000-deadbeef"
        tmp_settings.ensure_dirs()
        status_path(tmp_settings, "sync_channel", rid).write_text("{}", encoding="utf-8")
        with pytest.raises(OutputExistsError):
            with run_context("sync_channel", tmp_settings, run_id=rid):
                pass

    def test_creates_status_dir_if_missing(self, tmp_settings):
        assert not tmp_settings.status_dir.exists()
        with run_context("sync_channel", tmp_settings) as (run_id, _):
            pass
        assert status_path(tmp_settings, "sync_channel", run_id).exists()

    def test_logger_adapter_carries_run_id_and_stage(self, tmp_settings):
        with run_context("sync_channel", tmp_settings) as (run_id, logger):
            assert logger.extra["run_id"] == run_id
            assert logger.extra["stage"] == "sync_channel"

    def test_file_is_utf8_lf_and_keeps_korean(self, tmp_settings):
        """FR-21·비기능 — ensure_ascii=False, LF, 키 정렬."""
        with run_context("sync_channel", tmp_settings, extra={"채널": "세바시"}) as (run_id, _):
            pass
        raw = status_path(tmp_settings, "sync_channel", run_id).read_bytes()
        assert b"\r\n" not in raw
        assert "세바시".encode() in raw
        data = json.loads(raw)
        assert list(data.keys()) == sorted(data.keys())

    def test_rejects_bad_stage_before_writing(self, tmp_settings):
        with pytest.raises(ValueError):
            with run_context("bad stage", tmp_settings):
                pass
        assert not tmp_settings.status_dir.exists() or not any(tmp_settings.status_dir.iterdir())


class TestReadStatus:
    def test_roundtrip_keys(self, tmp_settings):
        with run_context("sync_channel", tmp_settings) as (run_id, _):
            pass
        rec = read_status(status_path(tmp_settings, "sync_channel", run_id))
        assert set(rec) == {
            "stage", "run_id", "status", "started_at", "finished_at",
            "duration_s", "error", "pipeline_version", "extra",
        }

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            read_status(tmp_path / "nope.json")
