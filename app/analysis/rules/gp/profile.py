from dataclasses import dataclass

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.gp.elevation_restriction import (
    GpElevationRestriction1DegRule,
    build_gp_1deg_shared_context,
)
from app.analysis.rules.gp.site_protection import (
    GpSiteProtectionGbRegionARule,
    GpSiteProtectionGbRegionBRule,
    GpSiteProtectionGbRegionCRule,
    GpSiteProtectionMhRegionARule,
    GpSiteProtectionMhRegionBRule,
    GpSiteProtectionMhRegionCRule,
    build_gp_site_protection_shared_context,
)


@dataclass(slots=True)
class GpStationAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class GpRuleProfile:
    # 初始化 GP 最小规则集合。
    def __init__(self) -> None:
        self._elevation_restriction_rules = [GpElevationRestriction1DegRule()]
        self._gb_rules = [
            GpSiteProtectionGbRegionARule(),
            GpSiteProtectionGbRegionBRule(),
            GpSiteProtectionGbRegionCRule(),
        ]
        self._mh_rules = [
            GpSiteProtectionMhRegionARule(),
            GpSiteProtectionMhRegionBRule(),
            GpSiteProtectionMhRegionCRule(),
        ]

    # 执行 GP 场地保护区规则。
    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
        runways: list[dict[str, object]],
    ) -> GpStationAnalysisPayload:
        runway_context = self._resolve_runway_context(station=station, runways=runways)
        if runway_context is None:
            return GpStationAnalysisPayload(rule_results=[], protection_zones=[])

        gb_shared_context = build_gp_site_protection_shared_context(
            station=station,
            station_point=station_point,
            runway_context=runway_context,
            standard_version="GB",
        )
        mh_shared_context = build_gp_site_protection_shared_context(
            station=station,
            station_point=station_point,
            runway_context=runway_context,
            standard_version="MH",
        )
        elevation_restriction_shared_context = build_gp_1deg_shared_context(
            station=station,
            station_point=station_point,
            runway_context=runway_context,
        )

        elevation_restriction_bound_rules = [
            rule.bind(
                station=station,
                shared_context=elevation_restriction_shared_context,
            )
            for rule in self._elevation_restriction_rules
        ]
        gb_bound_rules = [
            rule.bind(station=station, shared_context=gb_shared_context)
            for rule in self._gb_rules
        ]
        mh_bound_rules = [
            rule.bind(station=station, shared_context=mh_shared_context)
            for rule in self._mh_rules
        ]
        bound_rules = [
            *elevation_restriction_bound_rules,
            *gb_bound_rules,
            *mh_bound_rules,
        ]

        results: list[AnalysisRuleResult] = []
        for obstacle in obstacles:
            for rule in bound_rules:
                results.append(rule.analyze(obstacle))

        return GpStationAnalysisPayload(
            rule_results=results,
            protection_zones=[rule.protection_zone for rule in bound_rules],
        )

    # 按跑道号解析 GP 所属跑道上下文。
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


__all__ = [
    "GpRuleProfile",
    "GpStationAnalysisPayload",
]
