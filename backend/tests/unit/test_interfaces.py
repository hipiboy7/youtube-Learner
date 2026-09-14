"""domain/interfaces 검증 — 등급 A. 대응: docs/P0_설계서_Common.md 5절, 요구사항 FR-16.

interfaces.py 자체는 실행 로직이 없어 커버리지에서 제외되지만, "구조적 서브타이핑이 실제로 작동하는가"는 검증한다:
상속 없는 fake 가 Protocol 을 만족하고, 메서드가 빠진 객체는 만족하지 않아야 한다 (조립 지점의 isinstance 검사 근거).
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path

from youtube_learner.constants import AnalysisKind, TranscriptSource, VideoKind
from youtube_learner.domain.interfaces import Analyzer, SttEngine, TranscriptProvider, VideoListSource
from youtube_learner.domain.models import (
    AnalysisResult,
    AnalyzerInfo,
    ChannelRef,
    TranscriptResult,
    TranscriptSegment,
    Video,
    VideoStub,
)


def _result(video_id: str = "L81RWsnY-vY") -> TranscriptResult:
    return TranscriptResult(
        yt_video_id=video_id, source=TranscriptSource.WHISPER, language="ko", engine="fake",
        segments=[TranscriptSegment(idx=0, start_ms=0, end_ms=1000, text="말")],
    )


class FakeListSource:
    def list_tab(self, channel: ChannelRef, kind: VideoKind) -> Iterator[VideoStub]:
        yield VideoStub(yt_video_id="L81RWsnY-vY", kind=kind, title="t", url="u")


class FakeProvider:
    name = "fake"

    def fetch(self, video: Video, languages: Sequence[str]) -> TranscriptResult | None:
        return None


class FakeStt:
    def transcribe(self, audio_path: Path, language: str | None, on_progress=None) -> TranscriptResult:
        if on_progress:
            on_progress(1.0, "done")
        return _result()


class FakeAnalyzer:
    name = "fake"
    version = "1"

    def info(self) -> AnalyzerInfo:
        return AnalyzerInfo(name=self.name, version=self.version, kinds=[AnalysisKind.SUMMARY])

    def analyze(self, transcript, kind, options) -> AnalysisResult:
        return AnalysisResult(
            yt_video_id=transcript.yt_video_id, analyzer_name=self.name, analyzer_version=self.version, kind=kind,
            language=transcript.language, content={}, created_at=datetime.now(UTC),
        )


class TestStructuralSubtyping:
    def test_fakes_satisfy_protocols_without_inheritance(self):
        """FR-16 — 구현체는 interfaces 를 상속하지 않는다."""
        assert isinstance(FakeListSource(), VideoListSource)
        assert isinstance(FakeProvider(), TranscriptProvider)
        assert isinstance(FakeStt(), SttEngine)
        assert isinstance(FakeAnalyzer(), Analyzer)
        for fake, proto in ((FakeListSource, VideoListSource), (FakeProvider, TranscriptProvider),
                            (FakeStt, SttEngine), (FakeAnalyzer, Analyzer)):
            assert proto not in fake.__mro__

    def test_objects_missing_members_are_rejected(self):
        """FR-16 — 조립 지점의 isinstance 가 주입 실수를 잡을 수 있어야 한다."""
        class NoName:
            def fetch(self, video, languages):
                return None

        class NoAnalyze:
            name = "x"
            version = "1"

            def info(self):
                return None

        assert not isinstance(NoName(), TranscriptProvider)
        assert not isinstance(NoAnalyze(), Analyzer)
        assert not isinstance(object(), VideoListSource)
        assert not isinstance(object(), SttEngine)

    def test_list_source_yields_stubs(self):
        ref = ChannelRef(yt_channel_id=None, handle="@x", url="u")
        stubs = list(FakeListSource().list_tab(ref, VideoKind.SHORT))
        assert stubs[0].kind is VideoKind.SHORT

    def test_provider_none_means_not_available(self):
        """FR-16 — None 은 '이 소스에 없다'(정상). 예외가 아니다."""
        video = Video(yt_video_id="L81RWsnY-vY", kind=VideoKind.LONG, title="t", url="u")
        assert FakeProvider().fetch(video, ["ko"]) is None

    def test_stt_progress_callback_contract(self):
        seen: list[tuple[float, str]] = []
        FakeStt().transcribe(Path("x.m4a"), "ko", on_progress=lambda p, m: seen.append((p, m)))
        assert seen == [(1.0, "done")]
