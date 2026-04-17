import math

from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.ndb.common import NdbRule, projected_obstacle_distance_meters


class NdbConicalClearance3DegRule(NdbRule):
    rule_name = "ndb_conical_clearance_3deg"
    zone_name = "NDB 3 degree conical clearance zone"
    zone_definition = {
        "shape": "radial_band",
        "min_radius_m": 50.0,
        "max_radius_m": 37040.0,
        "vertical_angle_deg": 3.0,
    }

    def analyze(
        self,
        *,
        station: object,
        obstacle: dict[str, object],
        station_point: tuple[float, float],
        station_altitude: float | None,
    ) -> AnalysisRuleResult:
        actual_distance_meters = projected_obstacle_distance_meters(
            obstacle_geometry=obstacle["geometry"],
            station_point=station_point,
        )
        inner_radius_m = float(self.zone_definition["min_radius_m"])
        outer_radius_m = float(self.zone_definition["max_radius_m"])
        clamped_distance_meters = min(
            max(actual_distance_meters, inner_radius_m),
            outer_radius_m,
        )
        base_height_meters = float(station_altitude or 0.0)
        elevation_angle_degrees = float(self.zone_definition["vertical_angle_deg"])
        allowed_height_meters = base_height_meters + math.tan(
            math.radians(elevation_angle_degrees)
        ) * max(clamped_distance_meters - inner_radius_m, 0.0)
        top_elevation = float(obstacle.get("topElevation") or base_height_meters)

        return AnalysisRuleResult(
            station_id=station.id,
            station_type=str(station.station_type),
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=obstacle["rawObstacleType"],
            global_obstacle_category=str(obstacle["globalObstacleCategory"]),
            rule_name=self.rule_name,
            zone_code=self.rule_name,
            zone_name=self.zone_name,
            region_code="default",
            region_name="default",
            zone_definition=self.zone_definition,
            is_applicable=True,
            is_compliant=top_elevation <= allowed_height_meters,
            message=(
                "top elevation within conical clearance"
                if top_elevation <= allowed_height_meters
                else "top elevation exceeds conical clearance"
            ),
            metrics={
                "actualDistanceMeters": actual_distance_meters,
                "baseHeightMeters": base_height_meters,
                "elevationAngleDegrees": elevation_angle_degrees,
                "allowedHeightMeters": allowed_height_meters,
                "topElevationMeters": top_elevation,
                "innerRadiusMeters": inner_radius_m,
                "outerRadiusMeters": outer_radius_m,
            },
        )
