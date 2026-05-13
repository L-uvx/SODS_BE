from dataclasses import dataclass

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.wind_radar.elevation_angle_15deg import WindRadarElevationAngle15degRule


@dataclass(slots=True)
class WindRadarStationAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class WindRadarRuleProfile:
    # 执行 WindRadar 15deg 规则。
    def __init__(self) -> None:
        self._elevation_angle_15deg_rule = WindRadarElevationAngle15degRule()

    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
    ) -> WindRadarStationAnalysisPayload:
        rule_results: list[AnalysisRuleResult] = []
        protection_zones: list[ProtectionZoneSpec] = []
        bound_rule = self._elevation_angle_15deg_rule.bind(
            station=station,
            station_point=station_point,
        )
        if bound_rule is None:
            return WindRadarStationAnalysisPayload(
                rule_results=rule_results,
                protection_zones=protection_zones,
            )

        protection_zones.append(bound_rule.protection_zone)
        for obstacle in obstacles:
            rule_results.append(bound_rule.analyze(obstacle))

        return WindRadarStationAnalysisPayload(
            rule_results=rule_results,
            protection_zones=protection_zones,
        )

    # 无条件绑定 WindRadar 规则并返回保护区（不含障碍物分析）。
    def bind_protection_zones(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
    ) -> list[ProtectionZoneSpec]:
        bound = self._elevation_angle_15deg_rule.bind(
            station=station, station_point=station_point,
        )
        if bound is None:
            return []
        return [bound.protection_zone]
