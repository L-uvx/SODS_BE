from dataclasses import dataclass

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.adsb.config import (
    ADS_B_RULE_CODES_IN_BIND_ORDER,
    ADS_B_RULE_CODE_BY_CATEGORY,
)
from app.analysis.rules.adsb.minimum_distance_0_5km import AdsbMinimumDistance0_5kmRule
from app.analysis.rules.adsb.minimum_distance_0_7km import AdsbMinimumDistance0_7kmRule
from app.analysis.rules.adsb.minimum_distance_0_8km import AdsbMinimumDistance0_8kmRule
from app.analysis.rules.adsb.minimum_distance_1km import AdsbMinimumDistance1kmRule
from app.analysis.rules.adsb.minimum_distance_1_2km import AdsbMinimumDistance1_2kmRule


@dataclass(slots=True)
class AdsbStationAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class AdsbRuleProfile:
    # 按障碍物分类执行 ADS-B 圆形最小间距规则。
    def __init__(self) -> None:
        ordered_rules = [
            AdsbMinimumDistance0_5kmRule(),
            AdsbMinimumDistance0_7kmRule(),
            AdsbMinimumDistance0_8kmRule(),
            AdsbMinimumDistance1kmRule(),
            AdsbMinimumDistance1_2kmRule(),
        ]
        self._rules_by_code = {rule.rule_code: rule for rule in ordered_rules}

    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
    ) -> AdsbStationAnalysisPayload:
        rule_results: list[AnalysisRuleResult] = []
        protection_zones: list[ProtectionZoneSpec] = []
        bound_rules_by_code: dict[str, object] = {}
        obstacle_categories = {
            str(obstacle["globalObstacleCategory"])
            for obstacle in obstacles
            if obstacle.get("globalObstacleCategory") is not None
        }
        required_rule_codes = {
            ADS_B_RULE_CODE_BY_CATEGORY[category]
            for category in obstacle_categories
            if category in ADS_B_RULE_CODE_BY_CATEGORY
        }

        for rule_code in ADS_B_RULE_CODES_IN_BIND_ORDER:
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
            rule_code = ADS_B_RULE_CODE_BY_CATEGORY.get(category)
            if rule_code is None:
                continue
            bound_rule = bound_rules_by_code[rule_code]
            rule_results.append(bound_rule.analyze(obstacle))

        return AdsbStationAnalysisPayload(
            rule_results=rule_results,
            protection_zones=protection_zones,
        )
