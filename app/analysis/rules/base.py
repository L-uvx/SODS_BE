from abc import ABC, abstractmethod

from app.analysis.rule_result import AnalysisRuleResult


class ObstacleRule(ABC):
    rule_name: str
    zone_name: str
    zone_definition: dict[str, object]

    @abstractmethod
    def analyze(self, *args, **kwargs) -> AnalysisRuleResult:
        raise NotImplementedError
