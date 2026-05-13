from dataclasses import dataclass

import app.analysis.rules.loc.building_restriction as loc_building_restriction_module
import app.analysis.rules.loc.run_area_protection as loc_run_area_protection_module
from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.loc.building_restriction.region_1 import (
    LocBuildingRestrictionZoneRegion1Rule,
)
from app.analysis.rules.loc.building_restriction.region_2 import (
    LocBuildingRestrictionZoneRegion2Rule,
)
from app.analysis.rules.loc.building_restriction.region_3 import (
    LocBuildingRestrictionZoneRegion3Rule,
)
from app.analysis.rules.loc.building_restriction.region_4 import (
    LocBuildingRestrictionZoneRegion4Rule,
)
from app.analysis.rules.loc.building_restriction.helpers import (
    build_loc_building_restriction_zone_shared_context,
)
from app.analysis.rules.loc.forward_sector_3000m_15m import (
    LocForwardSector3000m15mRule,
)
from app.analysis.rules.loc.run_area_protection import (
    LocRunAreaProtectionRegionARule,
    LocRunAreaProtectionRegionBRule,
    LocRunAreaProtectionRegionCRule,
    LocRunAreaProtectionRegionDRule,
    build_loc_run_area_shared_context,
)
from app.analysis.rules.loc.site_protection import LocSiteProtectionRule
from app.analysis.rules.runway_contexts import resolve_runway_context



@dataclass(slots=True)
class LocStationAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class LocRuleProfile:
    # 初始化 LOC 最小规则集合。
    def __init__(self) -> None:
        self._site_protection_rule = LocSiteProtectionRule()
        self._forward_sector_rule = LocForwardSector3000m15mRule()
        self._run_area_rules = [
            LocRunAreaProtectionRegionARule(),
            LocRunAreaProtectionRegionBRule(),
            LocRunAreaProtectionRegionCRule(),
            LocRunAreaProtectionRegionDRule(),
        ]
        self._building_restriction_rules = [
            LocBuildingRestrictionZoneRegion1Rule(),
            LocBuildingRestrictionZoneRegion2Rule(),
            LocBuildingRestrictionZoneRegion3Rule(),
            LocBuildingRestrictionZoneRegion4Rule(),
        ]

    # 执行 LOC 场地保护区规则。
    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
        runways: list[dict[str, object]],
    ) -> LocStationAnalysisPayload:
        runway_context = resolve_runway_context(station=station, runways=runways)
        if runway_context is None:
            return LocStationAnalysisPayload(rule_results=[], protection_zones=[])

        obstacle_categories = {
            str(obstacle["globalObstacleCategory"])
            for obstacle in obstacles
            if obstacle.get("globalObstacleCategory") is not None
        }
        has_obstacles = len(obstacles) > 0

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
        run_area_shared_context = None
        run_area_rules = []
        if self._run_area_rules and (
            not has_obstacles
            or obstacle_categories
            & loc_run_area_protection_module.SUPPORTED_CATEGORIES
        ):
            run_area_shared_context = build_loc_run_area_shared_context(
                station=station,
                station_point=station_point,
                runway_context=runway_context,
            )
            if run_area_shared_context is not None:
                run_area_rules = []
                for rule in self._run_area_rules:
                    try:
                        run_area_rules.append(
                            rule.bind(
                                station=station,
                                shared_context=run_area_shared_context,
                            )
                        )
                    except ValueError:
                        continue
        building_restriction_shared_context = None
        building_restriction_rules = []
        if self._building_restriction_rules and (
            not has_obstacles
            or obstacle_categories
            & loc_building_restriction_module.SUPPORTED_CATEGORIES
        ):
            building_restriction_shared_context = (
                build_loc_building_restriction_zone_shared_context(
                    station_point=station_point,
                    runway_context=runway_context,
                )
            )
            building_restriction_rules = [
                rule.bind(
                    station=station,
                    station_point=station_point,
                    runway_context=runway_context,
                    shared_context=building_restriction_shared_context,
                )
                for rule in self._building_restriction_rules
            ]

        results: list[AnalysisRuleResult] = []
        protection_zones: list[ProtectionZoneSpec] = [
            site_protection_rule.protection_zone,
            *(
                [forward_sector_rule.protection_zone]
                if forward_sector_rule is not None
                else []
            ),
            *[rule.protection_zone for rule in run_area_rules],
            *[rule.protection_zone for rule in building_restriction_rules],
        ]
        for obstacle in obstacles:
            results.append(site_protection_rule.analyze(obstacle))
            if forward_sector_rule is not None:
                results.append(forward_sector_rule.analyze(obstacle))
            if self._is_run_area_applicable(obstacle):
                for rule in run_area_rules:
                    results.append(rule.analyze(obstacle))
            if self._is_building_restriction_applicable(obstacle):
                for rule in building_restriction_rules:
                    results.append(rule.analyze(obstacle))
        return LocStationAnalysisPayload(
            rule_results=results,
            protection_zones=protection_zones,
        )

    # 无条件绑定 LOC 全部规则并返回所有保护区（不含障碍物分析）。
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

        bound_site = self._site_protection_rule.bind(
            station=station, station_point=station_point, runway_context=runway_context,
        )
        protection_zones.append(bound_site.protection_zone)

        bound_forward = self._forward_sector_rule.bind(
            station=station, station_point=station_point, runway_context=runway_context,
        )
        protection_zones.append(bound_forward.protection_zone)

        shared_ctx = build_loc_building_restriction_zone_shared_context(
            station_point=station_point,
            runway_context=runway_context,
        )
        for rule in self._building_restriction_rules:
            bound = rule.bind(
                station=station,
                station_point=station_point,
                runway_context=runway_context,
                shared_context=shared_ctx,
            )
            protection_zones.append(bound.protection_zone)

        run_area_shared = build_loc_run_area_shared_context(
            station=station,
            station_point=station_point,
            runway_context=runway_context,
        )
        if run_area_shared is not None:
            for rule in self._run_area_rules:
                try:
                    bound = rule.bind(
                        station=station,
                        shared_context=run_area_shared,
                    )
                    protection_zones.append(bound.protection_zone)
                except ValueError:
                    continue

        return protection_zones

    # 校验障碍物是否适用建筑物限制区规则。
    def _is_building_restriction_applicable(self, obstacle: dict[str, object]) -> bool:
        category = obstacle.get("globalObstacleCategory")
        return str(category) in loc_building_restriction_module.SUPPORTED_CATEGORIES

    # 校验障碍物是否适用运行保护区规则。
    def _is_run_area_applicable(self, obstacle: dict[str, object]) -> bool:
        category = obstacle.get("globalObstacleCategory")
        return str(category) in loc_run_area_protection_module.SUPPORTED_CATEGORIES
