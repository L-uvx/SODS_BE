from dataclasses import dataclass

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.ndb.conical_clearance import NdbConicalClearance3DegRule
from app.analysis.rules.ndb.minimum_distance_150m import NdbMinimumDistance150mRule
from app.analysis.rules.ndb.minimum_distance_300m import NdbMinimumDistance300mRule
from app.analysis.rules.ndb.minimum_distance_500m import NdbMinimumDistance500mRule
from app.analysis.rules.ndb.minimum_distance_50m import NdbMinimumDistance50mRule


@dataclass(slots=True)
class NdbStationAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class NdbRuleProfile:
    # 初始化 NDB 分类到规则实例的映射。
    def __init__(self) -> None:
        self._rules = {
            "building_general": NdbMinimumDistance50mRule(),
            "building_hangar": NdbMinimumDistance50mRule(),
            "building_terminal": NdbMinimumDistance50mRule(),
            "road": NdbMinimumDistance50mRule(),
            "airport_ring_road": NdbMinimumDistance50mRule(),
            "tree_or_forest": NdbMinimumDistance50mRule(),
            "railway_electrified": NdbMinimumDistance150mRule(),
            "railway_non_electrified": NdbMinimumDistance150mRule(),
            "power_line_low_voltage_overhead": NdbMinimumDistance150mRule(),
            "power_or_communication_cable": NdbMinimumDistance150mRule(),
            "hill": NdbMinimumDistance300mRule(),
            "embankment": NdbMinimumDistance300mRule(),
            "power_line_high_voltage_35kv_below": NdbMinimumDistance150mRule(),
            "power_line_high_voltage_35kv": NdbMinimumDistance150mRule(),
            "power_line_high_voltage_110kv": NdbMinimumDistance500mRule(),
            "power_line_high_voltage_220kv": NdbMinimumDistance500mRule(),
            "power_line_high_voltage_330kv": NdbMinimumDistance500mRule(),
            "power_line_high_voltage_500kv_and_above": NdbMinimumDistance500mRule(),
        }
        self._conical_rule = NdbConicalClearance3DegRule()

    # 提取规则稳定标识，兼容测试替身对象。
    def _resolve_rule_code(self, rule: object) -> str:
        return str(getattr(rule, "rule_code", getattr(rule, "rule_name")))

    # 按障碍物分类执行 NDB 规则集合。
    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
    ) -> NdbStationAnalysisPayload:
        results: list[AnalysisRuleResult] = []
        station_altitude = float(station.altitude) if station.altitude is not None else None
        bound_rules_by_name: dict[str, object] = {}
        bound_rules_by_category: dict[str, object] = {}
        for category, rule in self._rules.items():
            rule_code = self._resolve_rule_code(rule)
            bound_rule = bound_rules_by_name.get(rule_code)
            if bound_rule is None:
                bound_rule = rule.bind(
                    station=station,
                    station_point=station_point,
                )
                bound_rules_by_name[rule_code] = bound_rule
            bound_rules_by_category[category] = bound_rule

        bound_conical_rule = self._conical_rule.bind(
            station=station,
            station_point=station_point,
            station_altitude=station_altitude,
        )
        protection_zones: list[ProtectionZoneSpec] = []
        for obstacle in obstacles:
            category = str(obstacle["globalObstacleCategory"])
            bound_rule = bound_rules_by_category.get(category)
            if bound_rule is not None:
                results.append(bound_rule.analyze(obstacle))
                if bound_rule.protection_zone not in protection_zones:
                    protection_zones.append(bound_rule.protection_zone)

            results.append(bound_conical_rule.analyze(obstacle))
            if bound_conical_rule.protection_zone not in protection_zones:
                protection_zones.append(bound_conical_rule.protection_zone)
        return NdbStationAnalysisPayload(
            rule_results=results,
            protection_zones=protection_zones,
        )

    # 无条件绑定 NDB 全部规则并返回所有保护区（不含障碍物分析）。
    def bind_protection_zones(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
    ) -> list[ProtectionZoneSpec]:
        station_altitude = (
            float(station.altitude) if station.altitude is not None else None
        )
        protection_zones: list[ProtectionZoneSpec] = []
        seen_rule_codes: set[str] = set()

        for _category, rule in self._rules.items():
            rule_code = self._resolve_rule_code(rule)
            if rule_code in seen_rule_codes:
                continue
            bound_rule = rule.bind(
                station=station,
                station_point=station_point,
            )
            seen_rule_codes.add(rule_code)
            protection_zones.append(bound_rule.protection_zone)

        bound_conical = self._conical_rule.bind(
            station=station,
            station_point=station_point,
            station_altitude=station_altitude,
        )
        protection_zones.append(bound_conical.protection_zone)

        return protection_zones
