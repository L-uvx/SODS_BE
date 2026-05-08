from dataclasses import dataclass

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.vhf.config import (
    VHF_RULE_CODES_IN_BIND_ORDER,
    VHF_RULE_CODE_BY_CATEGORY,
)
from app.analysis.rules.vhf.minimum_distance_0_2km import VhfMinimumDistance0_2kmRule
from app.analysis.rules.vhf.minimum_distance_0_25km import VhfMinimumDistance0_25kmRule
from app.analysis.rules.vhf.minimum_distance_0_3km import VhfMinimumDistance0_3kmRule
from app.analysis.rules.vhf.minimum_distance_0_8km import VhfMinimumDistance0_8kmRule
from app.analysis.rules.vhf.minimum_distance_1km import VhfMinimumDistance1kmRule
from app.analysis.rules.vhf.minimum_distance_6km import VhfMinimumDistance6kmRule


@dataclass(slots=True)
class VhfStationAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class VhfRuleProfile:
    # 按障碍物分类执行 VHF 圆形最小间距规则。
    def __init__(self) -> None:
        ordered_rules = [
            VhfMinimumDistance0_2kmRule(),
            VhfMinimumDistance0_25kmRule(),
            VhfMinimumDistance0_3kmRule(),
            VhfMinimumDistance0_8kmRule(),
            VhfMinimumDistance1kmRule(),
            VhfMinimumDistance6kmRule(),
        ]
        self._rules_by_code = {rule.rule_code: rule for rule in ordered_rules}

    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
    ) -> VhfStationAnalysisPayload:
        rule_results: list[AnalysisRuleResult] = []
        protection_zones: list[ProtectionZoneSpec] = []
        bound_rules_by_code: dict[str, object] = {}
        obstacle_categories = {
            str(obstacle["globalObstacleCategory"])
            for obstacle in obstacles
            if obstacle.get("globalObstacleCategory") is not None
        }
        required_rule_codes = {
            VHF_RULE_CODE_BY_CATEGORY[category]
            for category in obstacle_categories
            if category in VHF_RULE_CODE_BY_CATEGORY
        }

        for rule_code in VHF_RULE_CODES_IN_BIND_ORDER:
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
            rule_code = VHF_RULE_CODE_BY_CATEGORY.get(category)
            if rule_code is None:
                continue
            bound_rule = bound_rules_by_code[rule_code]
            rule_results.append(bound_rule.analyze(obstacle))

        return VhfStationAnalysisPayload(
            rule_results=rule_results,
            protection_zones=protection_zones,
        )
