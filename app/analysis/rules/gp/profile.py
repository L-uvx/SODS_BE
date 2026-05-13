from dataclasses import dataclass

import app.analysis.rules.gp.run_area_protection as gp_run_area_protection_module
from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.runway_contexts import resolve_runway_context
from app.analysis.rules.gp.elevation_restriction import (
    GpElevationRestriction1DegRule,
    build_gp_1deg_shared_context,
)
from app.analysis.rules.gp.run_area_protection import (
    GpRunAreaProtectionRegionARule,
    GpRunAreaProtectionRegionBRule,
    build_gp_run_area_shared_context,
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
        self._run_area_rules = [
            GpRunAreaProtectionRegionARule(),
            GpRunAreaProtectionRegionBRule(),
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
        runway_context = resolve_runway_context(station=station, runways=runways)
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
        obstacle_categories = {
            str(obstacle.get("globalObstacleCategory"))
            for obstacle in obstacles
            if obstacle.get("globalObstacleCategory") is not None
        }
        has_obstacles = len(obstacles) > 0
        run_area_shared_context = None
        run_area_rules = []
        if self._run_area_rules and (
            not has_obstacles
            or obstacle_categories
            & gp_run_area_protection_module.SUPPORTED_CATEGORIES
        ):
            run_area_shared_context = build_gp_run_area_shared_context(
                station=station,
                station_point=station_point,
                runway_context=runway_context,
            )
            if run_area_shared_context is not None:
                run_area_rules = [
                    rule.bind(station=station, shared_context=run_area_shared_context)
                    for rule in self._run_area_rules
                ]

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
            if self._is_run_area_applicable(obstacle):
                for rule in run_area_rules:
                    results.append(rule.analyze(obstacle))

        return GpStationAnalysisPayload(
            rule_results=results,
            protection_zones=[
                *[rule.protection_zone for rule in bound_rules],
                *[rule.protection_zone for rule in run_area_rules],
            ],
        )

    # 无条件绑定 GP 全部规则并返回所有保护区（不含障碍物分析）。
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

        protection_zones: list[ProtectionZoneSpec] = []

        gb_shared = build_gp_site_protection_shared_context(
            station=station, station_point=station_point,
            runway_context=runway_context, standard_version="GB",
        )
        mh_shared = build_gp_site_protection_shared_context(
            station=station, station_point=station_point,
            runway_context=runway_context, standard_version="MH",
        )
        elev_shared = build_gp_1deg_shared_context(
            station=station, station_point=station_point,
            runway_context=runway_context,
        )

        for rule in self._gb_rules:
            bound = rule.bind(station=station, shared_context=gb_shared)
            protection_zones.append(bound.protection_zone)

        for rule in self._mh_rules:
            bound = rule.bind(station=station, shared_context=mh_shared)
            protection_zones.append(bound.protection_zone)

        for rule in self._elevation_restriction_rules:
            bound = rule.bind(station=station, shared_context=elev_shared)
            protection_zones.append(bound.protection_zone)

        run_area_shared = build_gp_run_area_shared_context(
            station=station, station_point=station_point,
            runway_context=runway_context,
        )
        if run_area_shared is not None:
            for rule in self._run_area_rules:
                bound = rule.bind(station=station, shared_context=run_area_shared)
                protection_zones.append(bound.protection_zone)

        return protection_zones

    # 校验障碍物是否适用运行保护区规则。
    def _is_run_area_applicable(self, obstacle: dict[str, object]) -> bool:
        category = obstacle.get("globalObstacleCategory")
        return str(category) in gp_run_area_protection_module.SUPPORTED_CATEGORIES


__all__ = [
    "GpRuleProfile",
    "GpStationAnalysisPayload",
]
