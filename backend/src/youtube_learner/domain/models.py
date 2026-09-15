"""도메인 모델 — 대응: docs/P0_설계서_Common.md 4절 (FR-9~FR-15). 등급 A.

pydantic v2, frozen, extra=forbid. 경계(yt-dlp 응답·자막 파일·API 입력)에서 부적합 데이터를 거부하는 것이 목적이다.
이 모듈은 constants 와 표준 라이브러리 외 아무것도 import 하지 않는다.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from youtube_learner.constants import (
    PIPELINE_VERSION,
    YT_CHANNEL_ID_PATTERN,
    YT_VIDEO_ID_PATTERN,
    AnalysisKind,
    TranscriptSource,
    TranscriptStatus,
    VideoKind,
)

_VIDEO_ID_RE = re.compile(YT_VIDEO_ID_PATTERN)
_CHANNEL_ID_RE = re.compile(YT_CHANNEL_ID_PATTERN)


class _Frozen(BaseModel):
    """모든 도메인 모델의 공통 설정. 변경은 model_copy(update=...) 로 새 객체를 만든다."""

    model_config = ConfigDict(frozen=True, extra="forbid")


def _require_video_id(value: str) -> str:
    if not _VIDEO_ID_RE.fullmatch(value):
        raise ValueError(f"유튜브 영상 ID 형식이 아니다(11자 [A-Za-z0-9_-]): {value!r}")
    return value


class ChannelRef(_Frozen):
    """채널 식별. 정체성은 yt_channel_id(UC…)이고 handle 은 표시용 (scope-definition 2.1절)."""

    yt_channel_id: str | None = None
    handle: str | None = None
    url: str

    @field_validator("yt_channel_id")
    @classmethod
    def _check_channel_id(cls, value: str | None) -> str | None:
        if value is not None and not _CHANNEL_ID_RE.fullmatch(value):
            raise ValueError(f"유튜브 채널 ID 형식이 아니다(UC + 22자): {value!r}")
        return value

    @field_validator("handle")
    @classmethod
    def _check_handle(cls, value: str | None) -> str | None:
        if value is not None and (not value.startswith("@") or len(value) < 2):
            raise ValueError(f"핸들은 '@'로 시작하는 1자 이상이어야 한다: {value!r}")
        return value

    @model_validator(mode="after")
    def _require_one_identifier(self) -> ChannelRef:
        if self.yt_channel_id is None and self.handle is None:
            raise ValueError("채널 ID 또는 핸들 중 하나는 있어야 한다")
        return self


class VideoStub(_Frozen):
    """flat 목록 1건. 숏폼은 duration_s 가 없고 두 탭 모두 업로드일이 없다 — 보충은 Video (TechSpike 3.1절)."""

    yt_video_id: str
    kind: VideoKind
    title: str
    url: str
    duration_s: int | None = Field(default=None, ge=0)
    view_count: int | None = Field(default=None, ge=0)
    thumbnail_url: str | None = None

    @field_validator("yt_video_id")
    @classmethod
    def _check_video_id(cls, value: str) -> str:
        return _require_video_id(value)

    @field_validator("title")
    @classmethod
    def _check_title(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("제목이 비어 있다")
        return stripped


class Video(VideoStub):
    """메타 보충까지 끝난 영상. flat 규칙(VideoStub)을 그대로 상속한다."""

    upload_date: date | None = None
    language: str | None = None
    live_status: str | None = None
    metadata_fetched_at: datetime | None = None
    transcript_status: TranscriptStatus = TranscriptStatus.NONE


class TranscriptSegment(_Frozen):
    """스크립트 한 조각. 시간 역행·빈 텍스트는 파싱 오류의 징후라 거부한다."""

    idx: int = Field(ge=0)
    start_ms: int = Field(ge=0)
    end_ms: int
    text: str

    @field_validator("text")
    @classmethod
    def _check_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("세그먼트 텍스트가 비어 있다")
        return stripped

    @model_validator(mode="after")
    def _check_order(self) -> TranscriptSegment:
        if self.end_ms < self.start_ms:
            raise ValueError(f"end_ms({self.end_ms}) 가 start_ms({self.start_ms}) 보다 앞선다")
        return self


class TranscriptResult(_Frozen):
    """스크립트 1건. 출처·엔진·모델·파이프라인 버전을 함께 들고 다닌다 (CLAUDE.md 12절 버전 동반)."""

    yt_video_id: str
    source: TranscriptSource
    language: str
    engine: str
    model_name: str | None = None
    pipeline_version: str = PIPELINE_VERSION
    segments: list[TranscriptSegment] = Field(min_length=1)

    @field_validator("yt_video_id")
    @classmethod
    def _check_video_id(cls, value: str) -> str:
        return _require_video_id(value)

    @model_validator(mode="after")
    def _check_segments(self) -> TranscriptResult:
        for expected, segment in enumerate(self.segments):
            if segment.idx != expected:
                raise ValueError(f"세그먼트 idx 가 연속이 아니다: {expected} 자리에 {segment.idx}")
        for previous, current in zip(self.segments, self.segments[1:], strict=False):
            if current.start_ms < previous.start_ms:
                raise ValueError(f"세그먼트 start_ms 가 역행한다: idx {current.idx}")
        return self

    @property
    def full_text(self) -> str:
        """세그먼트를 공백 하나로 이어 붙인 파생 텍스트. 진실은 세그먼트다."""
        return " ".join(segment.text for segment in self.segments)

    @property
    def duration_ms(self) -> int:
        return self.segments[-1].end_ms


class AnalyzerInfo(_Frozen):
    """분석기 소개. 화면의 분석기 목록에 그대로 나간다."""

    name: str
    version: str
    kinds: list[AnalysisKind]
    description: str = ""


class AnalysisResult(_Frozen):
    """분석 결과 1건 (analyses 테이블 — Phase 5 에 데이터)."""

    yt_video_id: str
    analyzer_name: str
    analyzer_version: str
    kind: AnalysisKind
    language: str
    content: dict[str, Any]
    model_info: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    @field_validator("yt_video_id")
    @classmethod
    def _check_video_id(cls, value: str) -> str:
        return _require_video_id(value)
