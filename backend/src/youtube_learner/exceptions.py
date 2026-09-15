"""예외 계층 — 대응: docs/P0_설계서_Common.md 2절 (FR-17). 등급 A.

단일 베이스 아래 외부 서비스·단계별 하위 예외. CLI/API 최상위는 YoutubeLearnerError 로 "예상한 실패"를 잡고,
그 밖은 버그(스택트레이스)로 취급한다. 메시지는 한국어 한 줄, 구조 정보는 속성.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path


class YoutubeLearnerError(Exception):
    """이 프로젝트가 예상한 모든 실패의 베이스."""


class ConfigError(YoutubeLearnerError):
    """설정(.env·config JSON)이 없거나 잘못됐다."""


class YouTubeAccessError(YoutubeLearnerError):
    """YouTube 요청 실패(429·차단·형식 변경). 백오프는 retry_after_s 를 읽는다 — 메시지를 파싱하지 않는다."""

    def __init__(self, message: str, *, status: int | None = None, retry_after_s: float | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.retry_after_s = retry_after_s


class TranscriptUnavailableError(YoutubeLearnerError):
    """모든 소스에서 스크립트를 얻지 못했다 (체인 끝)."""


class SttError(YoutubeLearnerError):
    """음성 인식 엔진 실패(모델 로딩·디코딩·전사)."""


class AnalyzerNotConfiguredError(YoutubeLearnerError):
    """요청한 분석기가 설정되지 않았다. API 는 501 로 매핑한다 (설계서_Architecture 5.2절)."""

    def __init__(self, message: str, *, available: Sequence[str] = ()) -> None:
        super().__init__(message)
        self.available: tuple[str, ...] = tuple(available)


class StorageError(YoutubeLearnerError):
    """DB·파일 저장 계층 실패."""


class OutputExistsError(StorageError):
    """산출물이 이미 있어 덮어쓰지 않는다 (CLAUDE.md 6절 입출력 보존)."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        super().__init__(f"산출물이 이미 있어 덮어쓰지 않는다: {self.path}")
