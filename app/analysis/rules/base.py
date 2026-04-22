from abc import ABC, abstractmethod

from app.analysis.rule_result import AnalysisRuleResult


class ObstacleRule(ABC):
    rule_name: str
    zone_name: str
    zone_definition: dict[str, object]

    # 执行单条障碍物规则的分析判定。
    @abstractmethod
    def analyze(self, *args, **kwargs) -> AnalysisRuleResult:
        raise NotImplementedError
