from shapely.geometry import MultiPolygon, Point, shape

from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import ObstacleRule


class NdbRule(ObstacleRule):
    # 执行单条 NDB 规则的分析判定。
    def analyze(self, *args, **kwargs) -> AnalysisRuleResult:  # pragma: no cover
        raise NotImplementedError


# 优先使用局部坐标障碍物几何，缺失时回退到原始几何。
def resolve_ndb_obstacle_geometry(obstacle: dict[str, object]) -> dict[str, object]:
    return obstacle.get("localGeometry") or obstacle["geometry"]


# 计算障碍物到台站点位的平面距离。
def projected_obstacle_distance_meters(
    *,
    obstacle_geometry: dict[str, object],
    station_point: tuple[float, float],
) -> float:
    obstacle_shape = shape(obstacle_geometry)
    if not isinstance(obstacle_shape, MultiPolygon):
        obstacle_shape = MultiPolygon([obstacle_shape])
    return float(obstacle_shape.distance(Point(station_point)))
