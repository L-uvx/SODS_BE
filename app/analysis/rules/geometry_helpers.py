from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.geometry.base import BaseGeometry


# 统一转为 MultiPolygon，便于规则侧做相交判断。
def ensure_multipolygon(geometry: Polygon | MultiPolygon) -> MultiPolygon:
    if isinstance(geometry, MultiPolygon):
        return geometry
    return MultiPolygon([geometry])


# 解析障碍物平面形状并统一为 MultiPolygon。
def resolve_obstacle_shape(obstacle: dict[str, object]) -> MultiPolygon:
    obstacle_shape = shape(obstacle.get("localGeometry") or obstacle["geometry"])
    if not isinstance(obstacle_shape, (Polygon, MultiPolygon)):
        raise TypeError("obstacle geometry must resolve to Polygon or MultiPolygon")
    return ensure_multipolygon(obstacle_shape)


# 校验规则侧几何输入类型。
def ensure_polygonal_geometry(geometry: BaseGeometry) -> Polygon | MultiPolygon:
    if not isinstance(geometry, (Polygon, MultiPolygon)):
        raise TypeError("geometry must be Polygon or MultiPolygon")
    return geometry
