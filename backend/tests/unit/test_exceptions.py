"""exceptions 계층 검증 — 등급 A (테스트 먼저). 대응: docs/P0_설계서_Common.md 2절, 요구사항 FR-17."""

from __future__ import annotations

from pathlib import Path

import pytest

from youtube_learner import exceptions as ex


class TestHierarchy:
    @pytest.mark.parametrize(
        "cls",
        [
            ex.ConfigError,
            ex.YouTubeAccessError,
            ex.TranscriptUnavailableError,
            ex.SttError,
            ex.AnalyzerNotConfiguredError,
            ex.StorageError,
            ex.OutputExistsError,
        ],
    )
    def test_all_derive_from_single_base(self, cls):
        """FR-17 — CLI/API 최상위가 except YoutubeLearnerError 하나로 '예상한 실패'를 구분한다."""
        assert issubclass(cls, ex.YoutubeLearnerError)
        assert issubclass(cls, Exception)

    def test_output_exists_is_storage_error(self):
        assert issubclass(ex.OutputExistsError, ex.StorageError)

    def test_base_is_not_builtin_subclass_of_value_error(self):
        """우리 예외를 ValueError 로 잡는 코드가 생기지 않게 — 계층을 분리한다."""
        assert not issubclass(ex.YoutubeLearnerError, ValueError)


class TestAttributes:
    def test_youtube_access_error_carries_status_and_retry_after(self):
        """FR-17 — 429 백오프는 예외에서 대기 시간을 읽는다 (메시지 파싱 금지)."""
        e = ex.YouTubeAccessError("자막 요청이 거절됐다", status=429, retry_after_s=12.5)
        assert e.status == 429
        assert e.retry_after_s == 12.5
        assert str(e) == "자막 요청이 거절됐다"

    def test_youtube_access_error_defaults(self):
        e = ex.YouTubeAccessError("차단")
        assert e.status is None and e.retry_after_s is None

    def test_analyzer_not_configured_lists_available(self):
        e = ex.AnalyzerNotConfiguredError("분석기가 설정되지 않았다", available=["extractive", "ollama"])
        assert e.available == ("extractive", "ollama")
        assert isinstance(e.available, tuple)

    def test_analyzer_not_configured_default_available_is_empty(self):
        assert ex.AnalyzerNotConfiguredError("없음").available == ()

    def test_output_exists_error_has_path_and_message(self):
        p = Path("status/sync_x.json")
        e = ex.OutputExistsError(p)
        assert e.path == p
        assert "status" in str(e) and "sync_x.json" in str(e)

    def test_can_raise_and_catch_by_base(self):
        with pytest.raises(ex.YoutubeLearnerError):
            raise ex.SttError("모델 로딩 실패")
