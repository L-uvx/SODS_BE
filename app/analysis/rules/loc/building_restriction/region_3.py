from dataclasses import dataclass

from app.analysis.result_helpers import (
    compute_azimuth_degrees,
    compute_horizontal_angle_range_from_geometry,
)
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.loc.building_restriction.helpers import (
    LocBuildingRestrictionZoneRegion3AnalysisGeometry,
    LocBuildingRestrictionZoneRegion3Geometry,
    LocBuildingRestrictionZoneSharedContext,
    build_loc_building_restriction_zone_region_3_geometry,
    build_loc_building_restriction_zone_shared_context,
    calculate_region_3_worst_allowed_height_meters,
)
from app.analysis.rules.loc.config import LOC_BUILDING_RESTRICTION_ZONE
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec
from app.analysis.rules.loc.common import _join_loc_standard_names, _resolve_loc_standard_names



@dataclass(slots=True)
class BoundLocBuildingRestrictionZoneRegion3Rule(BoundObstacleRule):
    station: object
    station_point: tuple[float, float]
    zone_geometry: LocBuildingRestrictionZoneRegion3AnalysisGeometry

    # 执行 LOC 建筑物限制区第 3 区最不利点判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(
            self.protection_zone.local_geometry
        )
        base_height_meters = float(getattr(self.station, "altitude", 0.0) or 0.0)
        top_elevation_meters = float(obstacle.get("topElevation") or base_height_meters)
        worst_allowed_height_meters = calculate_region_3_worst_allowed_height_meters(
            zone_geometry=self.zone_geometry,
            obstacle_geometry=obstacle_shape,
            station_altitude_meters=base_height_meters,
        )

        is_compliant = True
        message = "obstacle outside loc building restriction zone region 3"
        if entered_protection_zone and worst_allowed_height_meters is not None:
            is_compliant = top_elevation_meters <= worst_allowed_height_meters
            message = (
                "obstacle within region 3 and below allowed height"
                if is_compliant
                else "obstacle within region 3 above allowed height"
            )

        obstacle_centroid = obstacle_shape.centroid
        az = compute_azimuth_degrees(
            self.station_point[0], self.station_point[1],
            obstacle_centroid.x, obstacle_centroid.y,
        )
        min_h, max_h = compute_horizontal_angle_range_from_geometry(
            self.station_point, obstacle_shape,
        )
        relative_height_meters = top_elevation_meters - base_height_meters
        over_distance_meters = (
            max(0.0, top_elevation_meters - (worst_allowed_height_meters or 0.0))
            if not is_compliant
            else 0.0
        )

        gb_name, mh_name = _resolve_loc_standard_names("loc_building_restriction_zone")
        joined_names = _join_loc_standard_names(gb_name, mh_name)
        limit = round((worst_allowed_height_meters or base_height_meters) - base_height_meters, 2)
        if is_compliant:
            details = (
                f"满足{joined_names}中'障碍物高度不超过台站基准面{limit}m'的规定。"
            )
        else:
            actual = round(top_elevation_meters - base_height_meters, 2)
            over = round(top_elevation_meters - (worst_allowed_height_meters or 0.0), 2)
            details = (
                f"不满足{joined_names}中'障碍物高度不超过台站基准面{limit}m'的规定，"
                f"实际高度{actual}m，超出{over}m。"
            )

        return AnalysisRuleResult(
            station_id=self.protection_zone.station_id,
            station_type=self.protection_zone.station_type,
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=obstacle["rawObstacleType"],
            global_obstacle_category=str(obstacle["globalObstacleCategory"]),
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
                "baseHeightMeters": base_height_meters,
                "topElevationMeters": top_elevation_meters,
                "worstAllowedHeightMeters": worst_allowed_height_meters,
            },
            standards_rule_code="loc_building_restriction_zone",
            over_distance_meters=over_distance_meters,
            azimuth_degrees=az,
            max_horizontal_angle_degrees=max_h,
            min_horizontal_angle_degrees=min_h,
            relative_height_meters=relative_height_meters,
            is_in_radius=entered_protection_zone,
            is_in_zone=entered_protection_zone,
            details=details,
        )


class LocBuildingRestrictionZoneRegion3Rule(ObstacleRule):
    rule_code = "loc_building_restriction_zone_region_3"
    rule_name = "loc_building_restriction_zone_region_3"
    zone_code = str(LOC_BUILDING_RESTRICTION_ZONE["zone_code"])
    zone_name = str(LOC_BUILDING_RESTRICTION_ZONE["zone_name"])

    # 绑定 LOC 建筑物限制区第 3 区。
    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
        runway_context: dict[str, object],
        shared_context: LocBuildingRestrictionZoneSharedContext | None = None,
    ) -> BoundLocBuildingRestrictionZoneRegion3Rule:
        resolved_shared_context = (
            shared_context
            or build_loc_building_restriction_zone_shared_context(
                station_point=station_point,
                runway_context=runway_context,
            )
        )
        region_3_geometry = build_loc_building_restriction_zone_region_3_geometry(
            resolved_shared_context
        )
        base_height_meters = float(getattr(station, "altitude", 0.0) or 0.0)
        return BoundLocBuildingRestrictionZoneRegion3Rule(
            protection_zone=build_protection_zone_spec(
                station_id=int(station.id),
                station_type=str(station.station_type),
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                region_code="3",
                region_name="3",
                local_geometry=region_3_geometry.local_geometry,
                vertical_definition={
                    "mode": "analytic_surface",
                    "baseReference": "station",
                    "baseHeightMeters": base_height_meters,
                    "surface": {
                        "type": "loc_building_restriction_zone_region_3",
                        "arcHeightMeters": base_height_meters
                        + resolved_shared_context.arc_height_offset_meters,
                        "alphaDegrees": resolved_shared_context.alpha_degrees,
                        "stationPoint": [
                            resolved_shared_context.station_point[0],
                            resolved_shared_context.station_point[1],
                        ],
                        "apexPoint": [
                            resolved_shared_context.apex_point[0],
                            resolved_shared_context.apex_point[1],
                        ],
                        "rootLeftPoint": [
                            resolved_shared_context.root_left_point[0],
                            resolved_shared_context.root_left_point[1],
                        ],
                        "rootRightPoint": [
                            resolved_shared_context.root_right_point[0],
                            resolved_shared_context.root_right_point[1],
                        ],
                        "arcRadiusMeters": resolved_shared_context.arc_radius_meters,
                        "arcPoints": [
                            [arc_point[0], arc_point[1]]
                            for arc_point in region_3_geometry.arc_points
                        ],
                    },
                },
            ),
            station=station,
            station_point=station_point,
            zone_geometry=_build_region_3_analysis_geometry(
                shared_context=resolved_shared_context,
                region_3_geometry=region_3_geometry,
            ),
        )


def _build_region_3_analysis_geometry(
    *,
    shared_context: LocBuildingRestrictionZoneSharedContext,
    region_3_geometry: LocBuildingRestrictionZoneRegion3Geometry,
) -> LocBuildingRestrictionZoneRegion3AnalysisGeometry:
    return LocBuildingRestrictionZoneRegion3AnalysisGeometry(
        station_point=shared_context.station_point,
        apex_point=shared_context.apex_point,
        arc_height_offset_meters=shared_context.arc_height_offset_meters,
        axis_unit=shared_context.axis_unit,
        station_to_apex_distance_meters=shared_context.station_to_apex_distance_meters,
        arc_points=region_3_geometry.arc_points,
        local_geometry=region_3_geometry.local_geometry,
    )
