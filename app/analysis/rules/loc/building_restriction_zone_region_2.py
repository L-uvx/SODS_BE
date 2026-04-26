from dataclasses import dataclass

from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.loc.building_restriction_zone_helpers import (
    build_loc_building_restriction_zone_geometry,
)
from app.analysis.rules.loc.config import LOC_BUILDING_RESTRICTION_ZONE
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


@dataclass(slots=True)
class BoundLocBuildingRestrictionZoneRegion2Rule(BoundObstacleRule):
    station: object

    # 执行 LOC 建筑物限制区第 2 区判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(
            self.protection_zone.local_geometry
        )
        base_height_meters = float(getattr(self.station, "altitude", 0.0) or 0.0)
        top_elevation_meters = float(obstacle.get("topElevation") or base_height_meters)

        is_compliant = not entered_protection_zone
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
            message=(
                "obstacle outside loc building restriction zone region 2"
                if is_compliant
                else "obstacle enters loc building restriction zone region 2"
            ),
            metrics={
                "enteredProtectionZone": entered_protection_zone,
                "baseHeightMeters": base_height_meters,
                "topElevationMeters": top_elevation_meters,
            },
        )


class LocBuildingRestrictionZoneRegion2Rule(ObstacleRule):
    rule_code = "loc_building_restriction_zone_region_2"
    rule_name = "loc_building_restriction_zone_region_2"
    zone_code = str(LOC_BUILDING_RESTRICTION_ZONE["zone_code"])
    zone_name = str(LOC_BUILDING_RESTRICTION_ZONE["zone_name"])

    # 绑定 LOC 建筑物限制区第 2 区。
    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
        runway_context: dict[str, object],
    ) -> BoundLocBuildingRestrictionZoneRegion2Rule:
        zone_geometry = build_loc_building_restriction_zone_geometry(
            station_point=station_point,
            runway_context=runway_context,
        )
        base_height_meters = float(getattr(station, "altitude", 0.0) or 0.0)
        return BoundLocBuildingRestrictionZoneRegion2Rule(
            protection_zone=build_protection_zone_spec(
                station_id=int(station.id),
                station_type=str(station.station_type),
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                region_code="2",
                region_name="2",
                local_geometry=zone_geometry.region_geometries["2"],
                vertical_definition={
                    "mode": "flat",
                    "baseReference": "station",
                    "baseHeightMeters": base_height_meters,
                },
            ),
            station=station,
        )
