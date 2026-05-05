import math

from app.analysis.config import PROTECTION_ZONE_BUILDER_DISCRETIZATION
from shapely.geometry import MultiPolygon, Point, Polygon, shape
from shapely.geometry.base import BaseGeometry


# 统一转为 MultiPolygon，便于规则侧做相交判断。
def ensure_multipolygon(geometry: Polygon | MultiPolygon) -> MultiPolygon:
    if isinstance(geometry, MultiPolygon):
        return geometry
    return MultiPolygon([geometry])


# 解析障碍物平面形状，当前支持 Point 与 Polygon/MultiPolygon。
def resolve_obstacle_shape(obstacle: dict[str, object]) -> BaseGeometry:
    obstacle_shape = shape(obstacle.get("localGeometry") or obstacle["geometry"])
    if not isinstance(obstacle_shape, (Point, Polygon, MultiPolygon)):
        raise TypeError("obstacle geometry must resolve to Point, Polygon or MultiPolygon")
    return obstacle_shape


# 校验规则侧几何输入类型。
def ensure_polygonal_geometry(geometry: BaseGeometry) -> Polygon | MultiPolygon:
    if not isinstance(geometry, (Polygon, MultiPolygon)):
        raise TypeError("geometry must be Polygon or MultiPolygon")
    return geometry


# 按共享圆形步长构建圆形 Polygon（局部米制坐标）。
def build_circle_polygon(
    *, center_point: tuple[float, float], radius_meters: float
):
    step_degrees = float(PROTECTION_ZONE_BUILDER_DISCRETIZATION["circle_step_degrees"])
    points: list[tuple[float, float]] = []
    degrees = 0.0
    while degrees < 360.0:
        radians = math.radians(degrees)
        points.append(
            (
                center_point[0] + math.cos(radians) * radius_meters,
                center_point[1] + math.sin(radians) * radius_meters,
            )
        )
        degrees += step_degrees
    points.append(points[0])
    return shape({"type": "Polygon", "coordinates": [points]})
