from dataclasses import dataclass

from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import ObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.gp.clearance import calculate_gp_clearance_limit_height_meters
from app.analysis.rules.gp.site_protection.judgement import (
    is_gp_road_or_rail_category,
)
from app.analysis.rules.gp.site_protection.helpers import (
    GpSiteProtectionSharedContext,
    build_gp_site_protection_region_c_geometry,
)
from app.analysis.rules.gp.site_protection.region_a import BoundGpSiteProtectionRegionRule
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


@dataclass(slots=True)
class BoundGpSiteProtectionRegionCRule(BoundGpSiteProtectionRegionRule):
    shared_context: GpSiteProtectionSharedContext

    # 执行 GP 场地保护区 C 区最小真实判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(
            self.protection_zone.local_geometry
        )
        global_obstacle_category = str(obstacle["globalObstacleCategory"])
        is_road_or_rail = is_gp_road_or_rail_category(global_obstacle_category)
        requires_clearance_evaluation = False
        clearance_limit_height_meters = None
        over_height_meters = None

        if not entered_protection_zone:
            is_compliant = True
            message = "obstacle outside GP site protection region C"
        elif is_road_or_rail:
            is_compliant = False
            message = "road or rail obstacle enters GP region C"
        else:
            requires_clearance_evaluation = True
            clearance_limit_height_meters = (
                calculate_gp_clearance_limit_height_meters(
                    runway_context=self.shared_context.runway_context,
                    obstacle=obstacle,
                )
            )
            if clearance_limit_height_meters is None:
                is_compliant = False
                message = "gp clearance limit unavailable"
            else:
                over_height_meters = float(obstacle["topElevation"]) - float(
                    clearance_limit_height_meters
                )
                is_compliant = over_height_meters <= 0.0
                message = (
                    "obstacle within GP clearance limit"
                    if is_compliant
                    else "obstacle exceeds GP clearance limit"
                )

        return AnalysisRuleResult(
            station_id=self.protection_zone.station_id,
            station_type=self.protection_zone.station_type,
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=(
                None
                if obstacle.get("rawObstacleType") is None
                else str(obstacle["rawObstacleType"])
            ),
            global_obstacle_category=global_obstacle_category,
            rule_code=self.protection_zone.rule_code,
            rule_name=self.protection_zone.rule_name,
            zone_code=self.protection_zone.zone_code,
            zone_name=self.protection_zone.zone_name,
            region_code=self.protection_zone.region_code,
            region_name=self.protection_zone.region_name,
            is_applicable=True,
            is_compliant=is_compliant,
            message=message,
            metrics={
                "enteredProtectionZone": entered_protection_zone,
                "isRoadOrRail": is_road_or_rail,
                "requiresClearanceEvaluation": requires_clearance_evaluation,
                **(
                    {}
                    if not entered_protection_zone or is_road_or_rail
                    else {
                        **(
                            {}
                            if clearance_limit_height_meters is None
                            else {
                                "clearanceLimitHeightMeters": clearance_limit_height_meters,
                                "overHeightMeters": over_height_meters,
                            }
                        ),
                    }
                ),
            },
            standards_rule_code=self.standards_rule_code,
        )


class _GpSiteProtectionRegionCRuleBase(ObstacleRule):
    region_code = "C"
    region_name = "C"

    # 绑定 GP 场地保护区 C 区。
    def bind(
        self,
        *,
        station: object,
        shared_context: GpSiteProtectionSharedContext,
    ) -> BoundGpSiteProtectionRegionCRule:
        region_geometry = build_gp_site_protection_region_c_geometry(shared_context)
        return BoundGpSiteProtectionRegionCRule(
            protection_zone=build_protection_zone_spec(
                station_id=int(station.id),
                station_type=str(station.station_type),
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                region_code=self.region_code,
                region_name=self.region_name,
                local_geometry=region_geometry.local_geometry,
                vertical_definition={
                    "mode": "flat",
                    "baseReference": "station",
                    "baseHeightMeters": float(getattr(station, "altitude", 0.0) or 0.0),
                },
            ),
            station_sub_type=(
                None
                if getattr(station, "station_sub_type", None) is None
                else str(getattr(station, "station_sub_type"))
            ),
            standards_rule_code=self._resolve_standards_rule_code(station=station),
            shared_context=shared_context,
        )

    def _resolve_standards_rule_code(self, *, station: object) -> str:
        return self.rule_code


class GpSiteProtectionGbRegionCRule(_GpSiteProtectionRegionCRuleBase):
    rule_code = "gp_site_protection_gb_region_c"
    rule_name = "gp_site_protection_gb_region_c"
    zone_code = "gp_site_protection_gb"
    zone_name = "GP site protection (GB)"


class GpSiteProtectionMhRegionCRule(_GpSiteProtectionRegionCRuleBase):
    rule_code = "gp_site_protection_mh_region_c"
    rule_name = "gp_site_protection_mh_region_c"
    zone_code = "gp_site_protection_mh"
    zone_name = "GP site protection (MH)"


__all__ = [
    "GpSiteProtectionGbRegionCRule",
    "GpSiteProtectionMhRegionCRule",
]
