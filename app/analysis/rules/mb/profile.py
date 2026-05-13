from dataclasses import dataclass

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.mb.config import MB_SITE_PROTECTION
from app.analysis.rules.mb.site_protection import MbSiteProtectionRule
from app.analysis.rules.runway_contexts import resolve_runway_context


@dataclass(slots=True)
class MbStationAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class MbRuleProfile:
    # 初始化 MB 场地保护区规则集合。
    def __init__(self) -> None:
        self._site_protection_rule = MbSiteProtectionRule()

    # 执行 MB 场地保护区规则。
    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
        runways: list[dict[str, object]],
    ) -> MbStationAnalysisPayload:
        runway_context = resolve_runway_context(station=station, runways=runways)
        if runway_context is None:
            return MbStationAnalysisPayload(rule_results=[], protection_zones=[])

        bound_rules = [
            self._site_protection_rule.bind(
                station=station,
                station_point=station_point,
                runway_direction_degrees=float(runway_context["directionDegrees"]),
                region_definition=region_definition,
            )
            for region_definition in MB_SITE_PROTECTION["regions"]
        ]
        results: list[AnalysisRuleResult] = []
        for obstacle in obstacles:
            for rule in bound_rules:
                results.append(rule.analyze(obstacle))
        return MbStationAnalysisPayload(
            rule_results=results,
            protection_zones=[rule.protection_zone for rule in bound_rules],
        )

    # 无条件绑定 MB 全部规则并返回所有保护区（不含障碍物分析）。
    def bind_protection_zones(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
        runways: list[dict[str, object]],
    ) -> list[ProtectionZoneSpec]:
        runway_context = resolve_runway_context(station=station, runways=runways)
        if runway_context is None:
            return []

        return [
            self._site_protection_rule.bind(
                station=station,
                station_point=station_point,
                runway_direction_degrees=float(runway_context["directionDegrees"]),
                region_definition=region_definition,
            ).protection_zone
            for region_definition in MB_SITE_PROTECTION["regions"]
        ]


__all__ = ["MbRuleProfile", "MbStationAnalysisPayload"]
