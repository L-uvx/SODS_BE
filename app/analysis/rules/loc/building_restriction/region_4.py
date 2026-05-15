from dataclasses import dataclass

from shapely.geometry import Point

from app.analysis.result_helpers import (
    ceil2,
    compute_azimuth_degrees,
    compute_horizontal_angle_range_from_geometry,
)
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.loc.building_restriction.helpers import (
    LocBuildingRestrictionZoneSharedContext,
    build_loc_building_restriction_zone_region_4_geometry,
    build_loc_building_restriction_zone_shared_context,
)
from app.analysis.rules.loc.config import LOC_BUILDING_RESTRICTION_ZONE
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec
from app.analysis.rules.loc.common import _join_loc_standard_names, _resolve_loc_standard_names



@dataclass(slots=True)
class BoundLocBuildingRestrictionZoneRegion4Rule(BoundObstacleRule):
    station: object
    station_point: tuple[float, float]

    # 执行 LOC 建筑物限制区第 4 区判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(
            self.protection_zone.local_geometry
        )
        actual_distance_meters = float(obstacle_shape.distance(Point(self.station_point)))
        base_height_meters = float(getattr(self.station, "altitude", 0.0) or 0.0)
        top_elevation_meters = float(obstacle.get("topElevation") or base_height_meters)
        allowed_height_meters = base_height_meters

        is_compliant = True
        if entered_protection_zone:
            is_compliant = top_elevation_meters <= allowed_height_meters

        over_height_meters = max(0.0, top_elevation_meters - allowed_height_meters)
        if entered_protection_zone:
            limit = ceil2(allowed_height_meters)
            if is_compliant:
                message = f"位于建筑物限制区内,此处限制顶部高程为{limit}米，未超出标准要求"
            else:
                over = ceil2(over_height_meters)
                message = f"位于建筑物限制区内,此处限制顶部高程为{limit}米,超出标准要求{over}米"
        else:
            message = "不位于建筑物限制区内"

        obstacle_centroid = obstacle_shape.centroid
        az = compute_azimuth_degrees(
            self.station_point[0], self.station_point[1],
            obstacle_centroid.x, obstacle_centroid.y,
        )
        min_h, max_h = compute_horizontal_angle_range_from_geometry(
            self.station_point, obstacle_shape,
        )
        relative_height_meters = top_elevation_meters - base_height_meters
        over_distance_meters = over_height_meters if not is_compliant else 0.0

        gb_name, mh_name = _resolve_loc_standard_names("loc_building_restriction_zone")
        joined_names = _join_loc_standard_names(gb_name, mh_name)
        limit = 0.0
        if is_compliant:
            details = (
                f"满足{joined_names}中'障碍物高度不超过台站基准面{limit}m'的规定。"
            )
        else:
            actual = ceil2(top_elevation_meters - base_height_meters)
            over = ceil2(top_elevation_meters - base_height_meters)
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
                "allowedHeightMeters": allowed_height_meters,
                "topElevationMeters": top_elevation_meters,
                "overHeightMeters": over_height_meters,
                "actualDistanceMeters": actual_distance_meters,
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


class LocBuildingRestrictionZoneRegion4Rule(ObstacleRule):
    rule_code = "loc_building_restriction_zone_region_4"
    rule_name = "loc_building_restriction_zone_region_4"
    zone_code = str(LOC_BUILDING_RESTRICTION_ZONE["zone_code"])
    zone_name = str(LOC_BUILDING_RESTRICTION_ZONE["zone_name"])

    # 绑定 LOC 建筑物限制区第 4 区。
    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
        runway_context: dict[str, object],
        shared_context: LocBuildingRestrictionZoneSharedContext | None = None,
    ) -> BoundLocBuildingRestrictionZoneRegion4Rule:
        resolved_shared_context = shared_context or build_loc_building_restriction_zone_shared_context(
            station_point=station_point,
            runway_context=runway_context,
        )
        region_4_geometry = build_loc_building_restriction_zone_region_4_geometry(
            resolved_shared_context
        )
        base_height_meters = float(getattr(station, "altitude", 0.0) or 0.0)
        return BoundLocBuildingRestrictionZoneRegion4Rule(
            protection_zone=build_protection_zone_spec(
                station_id=int(station.id),
                station_type=str(station.station_type),
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                region_code="4",
                region_name="4",
                local_geometry=region_4_geometry.local_geometry,
                vertical_definition={
                    "mode": "flat",
                    "baseReference": "station",
                    "baseHeightMeters": base_height_meters,
                },
            ),
            station=station,
            station_point=station_point,
        )
