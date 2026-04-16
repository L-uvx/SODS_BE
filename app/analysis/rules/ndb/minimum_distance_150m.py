from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.ndb.common import NdbRule, projected_obstacle_distance_meters


class NdbMinimumDistance150mRule(NdbRule):
    rule_name = "ndb_minimum_distance_150m"
    zone_name = "NDB 150m minimum distance zone"
    zone_definition = {"shape": "circle", "radius_m": 150.0}

    def analyze(
        self,
        *,
        station: object,
        obstacle: dict[str, object],
        station_point: tuple[float, float],
    ) -> AnalysisRuleResult:
        actual_distance_meters = projected_obstacle_distance_meters(
            obstacle_geometry=obstacle["geometry"],
            station_point=station_point,
        )
        required_distance_meters = 150.0
        return AnalysisRuleResult(
            station_id=station.id,
            station_type=str(station.station_type),
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=obstacle["rawObstacleType"],
            global_obstacle_category=str(obstacle["globalObstacleCategory"]),
            rule_name=self.rule_name,
            zone_name=self.zone_name,
            zone_definition=self.zone_definition,
            is_applicable=True,
            is_compliant=actual_distance_meters >= required_distance_meters,
            message=(
                "distance meets minimum threshold"
                if actual_distance_meters >= required_distance_meters
                else "distance below required threshold"
            ),
            metrics={
                "actualDistanceMeters": actual_distance_meters,
                "requiredDistanceMeters": required_distance_meters,
            },
        )
