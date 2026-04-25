from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult


class ObstacleRule(ABC):
    rule_code: str
    rule_name: str
    zone_code: str
    zone_name: str

    # 绑定单个台站上下文并返回可复用的已绑定规则。
    @abstractmethod
    def bind(self, *args, **kwargs) -> "BoundObstacleRule":
        raise NotImplementedError


@dataclass(slots=True)
class BoundObstacleRule(ABC):
    protection_zone: ProtectionZoneSpec

    # 执行已绑定保护区的单条障碍物规则判定。
    @abstractmethod
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        raise NotImplementedError
