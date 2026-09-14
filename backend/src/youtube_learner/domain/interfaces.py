"""Protocol 4종 — 대응: docs/P0_설계서_Common.md 5절 (FR-16), 설계서_Architecture 2.2절. 커버리지 측정 제외.

변경 가능성이 가장 높은 네 축(영상 목록 소스·스크립트 소스·STT 엔진·분석기)을 구조적 인터페이스 뒤에 둔다.
구현체는 이 모듈을 상속하지 않는다. 조립 지점은 isinstance 로 주입 실수를 기동 시 잡는다.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from youtube_learner.constants import AnalysisKind, VideoKind
from youtube_learner.domain.models import AnalysisResult, AnalyzerInfo, ChannelRef, TranscriptResult, Video, VideoStub

#: (0.0~1.0 진행률, 사람이 읽을 메시지)
ProgressCallback = Callable[[float, str], None]


@runtime_checkable
class VideoListSource(Protocol):
    """채널 탭의 영상 목록을 flat 으로 낸다. 구현: yt-dlp 탭(P1). 후보: YouTube Data API (보류 결정 7)."""

    def list_tab(self, channel: ChannelRef, kind: VideoKind) -> Iterator[VideoStub]: ...


@runtime_checkable
class TranscriptProvider(Protocol):
    """한 소스에서 스크립트를 시도한다. None 은 "이 소스에 없다"(정상, 다음으로), 예외는 "시도했는데 실패"."""

    @property
    def name(self) -> str: ...

    def fetch(self, video: Video, languages: Sequence[str]) -> TranscriptResult | None: ...


@runtime_checkable
class SttEngine(Protocol):
    """오디오 파일을 스크립트로. 엔진별 세그먼트 표현을 도메인 모델로 정규화하는 책임은 구현체에 있다."""

    def transcribe(
        self,
        audio_path: Path,
        language: str | None,
        on_progress: ProgressCallback | None = None,
    ) -> TranscriptResult: ...


@runtime_checkable
class Analyzer(Protocol):
    """분석 슬롯. v1 은 NullAnalyzer 만, 구현체는 Phase 5 (scope-definition 2.4절)."""

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def info(self) -> AnalyzerInfo: ...

    def analyze(
        self,
        transcript: TranscriptResult,
        kind: AnalysisKind,
        options: Mapping[str, Any],
    ) -> AnalysisResult: ...
