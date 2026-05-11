from dataclasses import dataclass

from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.result_helpers import (
    compute_azimuth_degrees,
    compute_horizontal_angle_range_from_geometry,
    compute_over_distance_meters,
)
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import ObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from shapely.geometry import Point
from app.analysis.rules.gp.clearance import calculate_gp_clearance_limit_height_meters
from app.analysis.rules.gp.site_protection.common import BoundGpSiteProtectionRegionRule
from app.analysis.rules.gp.site_protection.judgement import (
    is_gp_road_or_rail_category,
)
from app.analysis.rules.gp.site_protection.helpers import (
    GpSiteProtectionSharedContext,
    build_gp_site_protection_region_c_geometry,
)
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

        top_elev = float(obstacle["topElevation"])
        base_h = float(
            self.protection_zone.vertical_definition.get("baseHeightMeters", 0.0) or 0.0
        )
        obstacle_centroid = obstacle_shape.centroid
        sp = self.shared_context.station_point
        actual_distance_meters = float(obstacle_shape.distance(Point(sp)))
        az = compute_azimuth_degrees(sp[0], sp[1], obstacle_centroid.x, obstacle_centroid.y)
        min_h, max_h = compute_horizontal_angle_range_from_geometry(sp, obstacle_shape)
        rel_height = top_elev - base_h

        if not entered_protection_zone:
            is_compliant = True
            message = "不在C区范围内"
            over = 0.0
            details = "障碍物未进入GP场地保护区C区。"
        elif is_road_or_rail:
            is_compliant = False
            message = "在C区范围内"
            over = 0.0
            details = f"障碍物进入{self.protection_zone.zone_name}C区。"
        else:
            requires_clearance_evaluation = True
            clearance_limit_height_meters = (
                calculate_gp_clearance_limit_height_meters(
                    runway_context=self.shared_context.runway_context,
                    obstacle=obstacle,
                )
            )
            if clearance_limit_height_meters is None:
                is_compliant = True
                message = "gp clearance evaluation pending"
                over = 0.0
                details = "净空限高暂待评估。"
            else:
                over_height_meters = top_elev - float(clearance_limit_height_meters)
                is_compliant = over_height_meters <= 0.0
                message = (
                    "obstacle within GP clearance limit"
                    if is_compliant
                    else "obstacle exceeds GP clearance limit"
                )
                over = compute_over_distance_meters(top_elev, float(clearance_limit_height_meters))
                if is_compliant:
                    details = f"满足规定要求，障碍物高度{top_elev}m，允许高度{clearance_limit_height_meters}m。"
                else:
                    details = f"不满足规定要求，障碍物高度{top_elev}m，允许高度{clearance_limit_height_meters}m，超出{over}m。"

        return self.build_result(
            obstacle=obstacle,
            is_compliant=is_compliant,
            message=message,
            metrics={
                "enteredProtectionZone": entered_protection_zone,
                "topElevationMeters": top_elev,
                "actualDistanceMeters": actual_distance_meters,
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
                                "allowedHeightMeters": clearance_limit_height_meters,
                                "overHeightMeters": over_height_meters,
                            }
                        ),
                    }
                ),
            },
            over_distance_meters=over,
            azimuth_degrees=az,
            max_horizontal_angle_degrees=max_h,
            min_horizontal_angle_degrees=min_h,
            relative_height_meters=rel_height,
            is_in_radius=entered_protection_zone,
            is_in_zone=entered_protection_zone,
            details=details,
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
            station_point=shared_context.station_point,
            shared_context=shared_context,
        )

    def _resolve_standards_rule_code(self, *, station: object) -> str:
        return self.rule_code


class GpSiteProtectionGbRegionCRule(_GpSiteProtectionRegionCRuleBase):
    rule_code = "gp_site_protection_gb_region_c"
    rule_name = "gp_site_protection_gb_region_c"
    zone_code = "gp_site_protection_gb"
    zone_name = resolve_protection_zone_name(zone_code=zone_code)


class GpSiteProtectionMhRegionCRule(_GpSiteProtectionRegionCRuleBase):
    rule_code = "gp_site_protection_mh_region_c"
    rule_name = "gp_site_protection_mh_region_c"
    zone_code = "gp_site_protection_mh"
    zone_name = resolve_protection_zone_name(zone_code=zone_code)


__all__ = [
    "GpSiteProtectionGbRegionCRule",
    "GpSiteProtectionMhRegionCRule",
]
