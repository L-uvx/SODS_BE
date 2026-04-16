from shapely.geometry import MultiPolygon, Point, shape

from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import ObstacleRule


class NdbRule(ObstacleRule):
    def analyze(self, *args, **kwargs) -> AnalysisRuleResult:  # pragma: no cover
        raise NotImplementedError


def projected_obstacle_distance_meters(
    *,
    obstacle_geometry: dict[str, object],
    station_point: tuple[float, float],
) -> float:
    obstacle_shape = shape(obstacle_geometry)
    if not isinstance(obstacle_shape, MultiPolygon):
        obstacle_shape = MultiPolygon([obstacle_shape])
    return float(obstacle_shape.distance(Point(station_point)))
