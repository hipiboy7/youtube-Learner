"""설계 고정값 — 대응: docs/P0_설계서_Common.md 1절 (FR-6~FR-8). 등급 A.

값의 3분류(CLAUDE.md 5절) 중 "설계상 고정된 값"만 둔다 — 바뀌면 데이터 재생성·마이그레이션이 필요한 값.
환경별 값은 config.Settings, 실행마다 조절하는 값은 backend/config/*.json.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class VideoKind(StrEnum):
    """영상 구분. 판정 기준은 채널 탭 소속이다 — 길이가 아니다 (scope-definition 2.2절)."""

    LONG = "long"
    SHORT = "short"
    LIVE = "live"  # v1 목록 대상 아님. 값만 예약 (scope-definition 9절)


class TranscriptSource(StrEnum):
    """스크립트 출처. 우선순위 manual → auto → whisper. translated 는 옵션 (scope-definition 5절)."""

    MANUAL = "manual"
    AUTO = "auto"
    TRANSLATED = "translated"
    WHISPER = "whisper"


class TranscriptStatus(StrEnum):
    """영상의 스크립트 확보 상태 (videos.transcript_status)."""

    NONE = "none"
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class AnalysisKind(StrEnum):
    """분석 종류. v1 은 슬롯만 — 구현은 Phase 5 (scope-definition 2.4절)."""

    SUMMARY = "summary"
    KEYPOINTS = "keypoints"
    CHAPTERS = "chapters"


#: yt-dlp 자동자막 중 원어 트랙의 키 접미사. 예 "ko-orig" (TechSpike 3.2절 실측 2026-09-14)
ORIGINAL_CAPTION_SUFFIX: Final[str] = "-orig"
#: 원어 후보가 여럿일 때의 우선순위. 없는 언어를 만들어 달라는 뜻이 아니다 (scope-definition 5.2절)
LANG_PRIORITY_DEFAULT: Final[tuple[str, ...]] = ("ko",)
#: 스크립트 레코드에 동반 저장되는 파이프라인 규칙 버전. 정규화 규칙이 바뀌면 올린다 (CLAUDE.md 12절)
PIPELINE_VERSION: Final[str] = "1"
DB_FILENAME: Final[str] = "youtube_learner.db"
STATUS_FILENAME_PATTERN: Final[str] = "{stage}_{run_id}.json"
YT_VIDEO_ID_PATTERN: Final[str] = r"^[A-Za-z0-9_-]{11}$"
YT_CHANNEL_ID_PATTERN: Final[str] = r"^UC[A-Za-z0-9_-]{22}$"
STAGE_NAME_PATTERN: Final[str] = r"^[a-z0-9_]+$"
PACKAGE_NAME: Final[str] = "youtube_learner"
#: 사용자가 외부 AI 챗에서 받아 붙여 넣은 요약·정리의 analyses.analyzer_name / analyzer_version (scope-definition 2.4절, v1 수동 흐름)
MANUAL_ANALYZER_NAME: Final[str] = "manual"
MANUAL_ANALYZER_VERSION: Final[str] = "user"


def split_caption_key(key: str) -> tuple[str, bool]:
    """yt-dlp 자막 트랙 키를 (언어, 원어 여부)로 나눈다.

    "ko-orig" → ("ko", True), "ko" → ("ko", False), "pt-BR" → ("pt-BR", False).

    Raises:
        ValueError: 키가 비어 있거나 접미사만 있는 경우.
    """
    stripped = key.strip()
    if not stripped:
        raise ValueError("자막 트랙 키가 비어 있다")
    if stripped.endswith(ORIGINAL_CAPTION_SUFFIX):
        language = stripped[: -len(ORIGINAL_CAPTION_SUFFIX)]
        if not language:
            raise ValueError(f"언어 코드가 없는 트랙 키다: {key!r}")
        return language, True
    return stripped, False


def original_caption_key(language: str) -> str:
    """언어 코드로 원어 자동자막 트랙 키를 만든다. "ko" → "ko-orig".

    Raises:
        ValueError: 언어 코드가 비어 있는 경우.
    """
    stripped = language.strip()
    if not stripped:
        raise ValueError("언어 코드가 비어 있다")
    return f"{stripped}{ORIGINAL_CAPTION_SUFFIX}"
