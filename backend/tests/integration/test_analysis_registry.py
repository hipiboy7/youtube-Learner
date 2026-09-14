"""analysis/registry 검증 — 등급 B. 대응: docs/P0_설계서_Common.md 9절, 요구사항 FR-25."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from youtube_learner.analysis.null_analyzer import NullAnalyzer
from youtube_learner.analysis.registry import AnalyzerRegistry, build_registry
from youtube_learner.config import Settings
from youtube_learner.constants import AnalysisKind
from youtube_learner.domain.models import AnalysisResult, AnalyzerInfo
from youtube_learner.exceptions import AnalyzerNotConfiguredError, ConfigError


class FakeExtractive:
    """Analyzer Protocol 을 상속 없이 만족하는 테스트용 구현 (P5 구현체의 모양)."""

    name = "extractive"
    version = "test"

    def info(self) -> AnalyzerInfo:
        return AnalyzerInfo(name=self.name, version=self.version, kinds=[AnalysisKind.SUMMARY], description="테스트")

    def analyze(self, transcript, kind, options) -> AnalysisResult:
        return AnalysisResult(
            yt_video_id=transcript.yt_video_id, analyzer_name=self.name, analyzer_version=self.version, kind=kind,
            language=transcript.language, content={"summary": transcript.full_text[:20]},
            created_at=datetime.now(UTC),
        )


class TestRegistry:
    def test_null_only_registry_exposes_nothing(self):
        """FR-25 — null 은 내부 표현. names/available 에 나가지 않는다."""
        reg = AnalyzerRegistry()
        reg.register(NullAnalyzer())
        assert reg.names() == [] and reg.available() == []
        assert isinstance(reg.get("null"), NullAnalyzer)

    def test_get_unknown_raises_with_available(self):
        reg = AnalyzerRegistry()
        reg.register(NullAnalyzer())
        reg.register(FakeExtractive())
        with pytest.raises(AnalyzerNotConfiguredError) as ei:
            reg.get("ollama")
        assert ei.value.available == ("extractive",)

    def test_duplicate_name_rejected(self):
        reg = AnalyzerRegistry()
        reg.register(FakeExtractive())
        with pytest.raises(ConfigError):
            reg.register(FakeExtractive())

    def test_non_analyzer_rejected(self):
        reg = AnalyzerRegistry()
        with pytest.raises(ConfigError):
            reg.register(object())  # type: ignore[arg-type]

    def test_real_analyzer_listed(self):
        reg = AnalyzerRegistry()
        reg.register(NullAnalyzer())
        reg.register(FakeExtractive())
        assert reg.names() == ["extractive"]
        assert [info.name for info in reg.available()] == ["extractive"]


class TestBuildRegistry:
    def test_default_settings_gives_null_only(self, tmp_settings: Settings):
        """완료 기준 — available() 빈 목록, get('summary') 는 AnalyzerNotConfiguredError."""
        reg = build_registry(tmp_settings)
        assert reg.available() == []
        with pytest.raises(AnalyzerNotConfiguredError) as ei:
            reg.get("summary")
        assert ei.value.available == ()

    def test_unimplemented_name_fails_loudly(self, tmp_settings: Settings):
        """FR-25 — .env ANALYZERS=ollama 를 조용히 무시하지 않는다."""
        s = Settings(data_dir=tmp_settings.data_dir, status_dir=tmp_settings.status_dir, analyzers=["ollama"])
        with pytest.raises(ConfigError, match="ollama"):
            build_registry(s)
