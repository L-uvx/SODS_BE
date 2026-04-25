from dataclasses import dataclass

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.loc.forward_sector_3000m_15m import (
    LocForwardSector3000m15mRule,
)
from app.analysis.rules.loc.site_protection import LocSiteProtectionRule


@dataclass(slots=True)
class LocStationAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class LocRuleProfile:
    # 初始化 LOC 最小规则集合。
    def __init__(self) -> None:
        self._site_protection_rule = LocSiteProtectionRule()
        self._forward_sector_rule = LocForwardSector3000m15mRule()

    # 执行 LOC 场地保护区规则。
    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
        runways: list[dict[str, object]],
    ) -> LocStationAnalysisPayload:
        runway_context = self._resolve_runway_context(station=station, runways=runways)
        if runway_context is None:
            return LocStationAnalysisPayload(rule_results=[], protection_zones=[])

        site_protection_rule = self._site_protection_rule.bind(
            station=station,
            station_point=station_point,
            runway_context=runway_context,
        )
        forward_sector_rule = self._forward_sector_rule.bind(
            station=station,
            station_point=station_point,
            runway_context=runway_context,
        )

        results: list[AnalysisRuleResult] = []
        protection_zones: list[ProtectionZoneSpec] = [
            site_protection_rule.protection_zone,
            forward_sector_rule.protection_zone,
        ]
        for obstacle in obstacles:
            results.append(site_protection_rule.analyze(obstacle))
            if self._forward_sector_rule.is_applicable(obstacle):
                results.append(forward_sector_rule.analyze(obstacle))
        return LocStationAnalysisPayload(
            rule_results=results,
            protection_zones=protection_zones,
        )

    # 按跑道号解析 LOC 所属跑道上下文。
    def _resolve_runway_context(
        self,
        *,
        station: object,
        runways: list[dict[str, object]],
    ) -> dict[str, object] | None:
        runway_no = getattr(station, "runway_no", None)
        if runway_no is None:
            return None

        for runway in runways:
            if runway.get("runNumber") == runway_no:
                return runway
        return None
