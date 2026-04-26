from dataclasses import dataclass

from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.loc.building_restriction_zone_helpers import (
    LocBuildingRestrictionZoneGeometry,
    build_loc_building_restriction_zone_geometry,
    calculate_region_3_worst_allowed_height_meters,
)
from app.analysis.rules.loc.config import LOC_BUILDING_RESTRICTION_ZONE
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


@dataclass(slots=True)
class BoundLocBuildingRestrictionZoneRegion3Rule(BoundObstacleRule):
    station: object
    zone_geometry: LocBuildingRestrictionZoneGeometry

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
    ) -> BoundLocBuildingRestrictionZoneRegion3Rule:
        zone_geometry = build_loc_building_restriction_zone_geometry(
            station_point=station_point,
            runway_context=runway_context,
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
                local_geometry=zone_geometry.region_geometries["3"],
                vertical_definition={
                    "mode": "analytic_surface",
                    "baseReference": "station",
                    "baseHeightMeters": base_height_meters,
                    "surface": {
                        "type": "loc_building_restriction_zone_region_3",
                        "arcHeightMeters": base_height_meters
                        + zone_geometry.arc_height_offset_meters,
                        "alphaDegrees": zone_geometry.alpha_degrees,
                        "stationPoint": [station_point[0], station_point[1]],
                        "apexPoint": [
                            zone_geometry.apex_point[0],
                            zone_geometry.apex_point[1],
                        ],
                        "rootLeftPoint": [
                            zone_geometry.root_left_point[0],
                            zone_geometry.root_left_point[1],
                        ],
                        "rootRightPoint": [
                            zone_geometry.root_right_point[0],
                            zone_geometry.root_right_point[1],
                        ],
                        "arcRadiusMeters": zone_geometry.arc_radius_meters,
                        "arcPoints": [
                            [arc_point[0], arc_point[1]]
                            for arc_point in zone_geometry.arc_points
                        ],
                    },
                },
            ),
            station=station,
            zone_geometry=zone_geometry,
        )
