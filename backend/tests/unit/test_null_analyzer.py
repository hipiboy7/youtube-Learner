"""analysis/null_analyzer 검증 — 등급 A (테스트 먼저). 대응: docs/P0_설계서_Common.md 9절, 요구사항 FR-24."""

from __future__ import annotations

import pytest

from youtube_learner.analysis.null_analyzer import NullAnalyzer
from youtube_learner.constants import AnalysisKind, TranscriptSource
from youtube_learner.domain.interfaces import Analyzer
from youtube_learner.domain.models import TranscriptResult, TranscriptSegment
from youtube_learner.exceptions import AnalyzerNotConfiguredError


@pytest.fixture
def transcript() -> TranscriptResult:
    return TranscriptResult(
        yt_video_id="L81RWsnY-vY", source=TranscriptSource.AUTO, language="ko", engine="yt-dlp",
        segments=[TranscriptSegment(idx=0, start_ms=0, end_ms=1000, text="말")],
    )


class TestNullAnalyzer:
    def test_satisfies_analyzer_protocol_without_inheritance(self):
        """FR-24·FR-16 — 구조적 서브타이핑: 상속 없이 Protocol 을 만족해야 한다."""
        a = NullAnalyzer()
        assert isinstance(a, Analyzer)
        assert Analyzer not in type(a).__mro__

    def test_identity(self):
        a = NullAnalyzer()
        assert a.name == "null" and a.version == "0"

    def test_info_has_no_kinds(self):
        """FR-24 — 아무 분석도 할 수 없다고 말한다."""
        info = NullAnalyzer().info()
        assert info.name == "null" and info.kinds == []

    @pytest.mark.parametrize("kind", list(AnalysisKind))
    def test_analyze_always_raises_not_configured(self, transcript, kind):
        with pytest.raises(AnalyzerNotConfiguredError) as ei:
            NullAnalyzer().analyze(transcript, kind, {})
        assert ei.value.available == ()
