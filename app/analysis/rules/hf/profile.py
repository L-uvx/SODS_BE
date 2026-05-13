from dataclasses import dataclass

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.hf.config import (
    HF_EXPLICITLY_UNSUPPORTED_CATEGORIES,
    HF_RULE_CODE_BY_CATEGORY,
    HF_RULE_CODES_IN_BIND_ORDER,
)
from app.analysis.rules.hf.minimum_distance_0_8km import HfMinimumDistance0_8kmRule
from app.analysis.rules.hf.minimum_distance_1km import HfMinimumDistance1kmRule
from app.analysis.rules.hf.minimum_distance_1_3km import HfMinimumDistance1_3kmRule
from app.analysis.rules.hf.minimum_distance_1_8km import HfMinimumDistance1_8kmRule
from app.analysis.rules.hf.minimum_distance_2km import HfMinimumDistance2kmRule
from app.analysis.rules.hf.minimum_distance_4km import HfMinimumDistance4kmRule
from app.analysis.rules.hf.minimum_distance_5km import HfMinimumDistance5kmRule
from app.analysis.rules.hf.minimum_distance_10km import HfMinimumDistance10kmRule
from app.analysis.rules.hf.minimum_distance_15km import HfMinimumDistance15kmRule
from app.analysis.rules.hf.minimum_distance_20km import HfMinimumDistance20kmRule


@dataclass(slots=True)
class HfStationAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class HfRuleProfile:
    # 按障碍物分类执行 HF 圆形最小间距规则。
    def __init__(self) -> None:
        ordered_rules = [
            HfMinimumDistance0_8kmRule(),
            HfMinimumDistance1kmRule(),
            HfMinimumDistance1_3kmRule(),
            HfMinimumDistance1_8kmRule(),
            HfMinimumDistance2kmRule(),
            HfMinimumDistance4kmRule(),
            HfMinimumDistance5kmRule(),
            HfMinimumDistance10kmRule(),
            HfMinimumDistance15kmRule(),
            HfMinimumDistance20kmRule(),
        ]
        self._rules_by_code = {rule.rule_code: rule for rule in ordered_rules}

    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
    ) -> HfStationAnalysisPayload:
        rule_results: list[AnalysisRuleResult] = []
        protection_zones: list[ProtectionZoneSpec] = []
        bound_rules_by_code: dict[str, object] = {}
        obstacle_categories = {
            str(obstacle["globalObstacleCategory"])
            for obstacle in obstacles
            if obstacle.get("globalObstacleCategory") is not None
        }
        required_rule_codes = {
            HF_RULE_CODE_BY_CATEGORY[category]
            for category in obstacle_categories
            if category in HF_RULE_CODE_BY_CATEGORY
        }

        for rule_code in HF_RULE_CODES_IN_BIND_ORDER:
            if rule_code not in required_rule_codes:
                continue
            bound_rule = self._rules_by_code[rule_code].bind(
                station=station,
                station_point=station_point,
            )
            bound_rules_by_code[rule_code] = bound_rule
            protection_zones.append(bound_rule.protection_zone)

        for obstacle in obstacles:
            category = str(obstacle["globalObstacleCategory"])
            if category in HF_EXPLICITLY_UNSUPPORTED_CATEGORIES:
                continue
            rule_code = HF_RULE_CODE_BY_CATEGORY.get(category)
            if rule_code is None:
                continue
            bound_rule = bound_rules_by_code[rule_code]
            rule_results.append(bound_rule.analyze(obstacle))

        return HfStationAnalysisPayload(
            rule_results=rule_results,
            protection_zones=protection_zones,
        )

    # 无条件绑定 HF 全部规则并返回所有保护区（不含障碍物分析）。
    def bind_protection_zones(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
    ) -> list[ProtectionZoneSpec]:
        protection_zones: list[ProtectionZoneSpec] = []
        for rule_code in HF_RULE_CODES_IN_BIND_ORDER:
            bound_rule = self._rules_by_code[rule_code].bind(
                station=station,
                station_point=station_point,
            )
            protection_zones.append(bound_rule.protection_zone)
        return protection_zones
