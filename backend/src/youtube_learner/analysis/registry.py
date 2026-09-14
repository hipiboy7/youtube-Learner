"""분석기 레지스트리 — 대응: docs/P0_설계서_Common.md 9절 (FR-25). 등급 B.

이름 → Analyzer. v1 은 NullAnalyzer 만 등록된다. P5 완료 기준("analysis/ 밖 수정 없음")을 지키는 자리:
구현체 추가 = 이 패키지 안에 파일 추가 + build_registry 의 이름→팩토리 표 한 줄.
"""

from __future__ import annotations

from youtube_learner.analysis.null_analyzer import NULL_ANALYZER_NAME, NullAnalyzer
from youtube_learner.config import Settings
from youtube_learner.domain.interfaces import Analyzer
from youtube_learner.domain.models import AnalyzerInfo
from youtube_learner.exceptions import AnalyzerNotConfiguredError, ConfigError


class AnalyzerRegistry:
    def __init__(self) -> None:
        self._items: dict[str, Analyzer] = {}

    def register(self, analyzer: Analyzer) -> None:
        """같은 이름 재등록은 ConfigError — 조용히 덮어쓰면 어느 구현이 살았는지 모른다."""
        if not isinstance(analyzer, Analyzer):
            raise ConfigError(f"Analyzer Protocol 을 만족하지 않는다: {type(analyzer).__name__}")
        if analyzer.name in self._items:
            raise ConfigError(f"분석기 이름이 중복된다: {analyzer.name!r}")
        self._items[analyzer.name] = analyzer

    def get(self, name: str) -> Analyzer:
        try:
            return self._items[name]
        except KeyError:
            raise AnalyzerNotConfiguredError(f"분석기 {name!r} 이 설정되지 않았다", available=self.names()) from None

    def names(self) -> list[str]:
        """사용 가능한 분석기 이름. null 은 내부 표현이라 뺀다."""
        return [name for name in self._items if name != NULL_ANALYZER_NAME]

    def available(self) -> list[AnalyzerInfo]:
        return [analyzer.info() for name, analyzer in self._items.items() if name != NULL_ANALYZER_NAME]


def build_registry(settings: Settings) -> AnalyzerRegistry:
    """설정으로 레지스트리를 조립한다. 미구현 이름은 기동 시 시끄럽게 실패한다 — 조용히 무시하면 몇 시간을 찾는다."""
    registry = AnalyzerRegistry()
    registry.register(NullAnalyzer())
    for name in settings.analyzers:
        raise ConfigError(f"분석기 {name!r} 은 아직 구현되지 않았다 — 구현체는 Phase 5 (.env ANALYZERS 를 비운다)")
    return registry
