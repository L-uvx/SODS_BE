from dataclasses import dataclass

from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.loc.building_restriction.helpers import (
    LocBuildingRestrictionZoneSharedContext,
    build_loc_building_restriction_zone_region_2_geometry,
    build_loc_building_restriction_zone_shared_context,
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
        allowed_height_meters = float(
            self.protection_zone.vertical_definition["baseHeightMeters"]
        )
        base_height_meters = float(getattr(self.station, "altitude", 0.0) or 0.0)
        top_elevation_meters = float(obstacle.get("topElevation") or base_height_meters)

        is_compliant = True
        message = "obstacle outside region 2"
        if entered_protection_zone:
            is_compliant = top_elevation_meters <= allowed_height_meters
            message = (
                "obstacle within region 2 and below allowed height"
                if is_compliant
                else "obstacle within region 2 above allowed height"
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
        shared_context: LocBuildingRestrictionZoneSharedContext | None = None,
    ) -> BoundLocBuildingRestrictionZoneRegion2Rule:
        resolved_shared_context = shared_context or build_loc_building_restriction_zone_shared_context(
            station_point=station_point,
            runway_context=runway_context,
        )
        region_2_geometry = build_loc_building_restriction_zone_region_2_geometry(
            resolved_shared_context
        )
        base_height_meters = float(getattr(station, "altitude", 0.0) or 0.0) + float(
            LOC_BUILDING_RESTRICTION_ZONE["region_1_2_height_offset_m"]
        )
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
                local_geometry=region_2_geometry.local_geometry,
                vertical_definition={
                    "mode": "flat",
                    "baseReference": "station",
                    "baseHeightMeters": base_height_meters,
                },
            ),
            station=station,
        )
