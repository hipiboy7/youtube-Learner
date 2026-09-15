"""NullAnalyzer — 대응: docs/P0_설계서_Common.md 9절 (FR-24). 등급 A.

"분석기가 설정되지 않았다"를 None 검사 대신 같은 인터페이스의 예외로 말하는 Null 객체.
API(P1)는 AnalyzerNotConfiguredError 를 501 로 매핑한다. Analyzer Protocol 을 상속 없이 만족한다.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, NoReturn

from youtube_learner.constants import AnalysisKind
from youtube_learner.domain.models import AnalyzerInfo, TranscriptResult
from youtube_learner.exceptions import AnalyzerNotConfiguredError

NULL_ANALYZER_NAME = "null"


class NullAnalyzer:
    """아무 분석도 하지 않는다. 화면 목록(available)에는 나가지 않는다."""

    name = NULL_ANALYZER_NAME
    version = "0"

    def info(self) -> AnalyzerInfo:
        return AnalyzerInfo(
            name=self.name,
            version=self.version,
            kinds=[],
            description="분석기가 설정되지 않은 상태. 구현체는 Phase 5 에서 추가된다 (scope-definition 2.4절)",
        )

    def analyze(
        self,
        transcript: TranscriptResult,
        kind: AnalysisKind,
        options: Mapping[str, Any],
    ) -> NoReturn:
        raise AnalyzerNotConfiguredError(
            f"설정된 분석기가 없어 '{kind}' 분석을 할 수 없다 — .env ANALYZERS 를 확인한다 (Phase 5)",
            available=(),
        )
