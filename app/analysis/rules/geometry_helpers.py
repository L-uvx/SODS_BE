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
