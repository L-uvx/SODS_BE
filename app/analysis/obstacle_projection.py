from typing import Any

from shapely.geometry import (
    MultiPolygon,
    Point,
    Polygon,
    base,
    mapping,
    shape,
)

from app.analysis.local_coordinate import AirportLocalProjector


# 为台站创建以其自身经纬度为中心的 AEQD 局部投影器。
def create_station_projector(station: Any) -> AirportLocalProjector:
    return AirportLocalProjector(float(station.longitude), float(station.latitude))


# 将障碍物的 WGS84 几何投影到指定台站中心局部米制坐标系。
def project_obstacle_for_station(
    projector: AirportLocalProjector, obstacle: dict[str, Any]
) -> dict[str, Any]:
    geometry = obstacle.get("geometry")
    if geometry is None:
        raise KeyError("obstacle dict missing required key 'geometry'")
    local_geometry = project_geometry_to_projector(projector, geometry)
    result = {**obstacle, "localGeometry": local_geometry}
    return result


# 将 WGS84 经纬度几何投影到任意 AEQD 投影器的局部米制坐标系。
def project_geometry_to_projector(
    projector: AirportLocalProjector, geometry: dict[str, Any]
) -> dict[str, Any]:
    source_geometry = shape(geometry)
    if isinstance(source_geometry, Point):
        x, y = projector.project_point(
            float(source_geometry.x), float(source_geometry.y)
        )
        return {
            "type": "Point",
            "coordinates": [float(x), float(y)],
        }

    if not isinstance(source_geometry, (MultiPolygon, Polygon)):
        raise ValueError(
            f"unsupported geometry type: {type(source_geometry).__name__}, "
            f"expected Point, Polygon, or MultiPolygon"
        )

    multipolygon = source_geometry
    polygons: list[Polygon] = []
    if isinstance(multipolygon, Polygon):
        iterable: list[Polygon] = [multipolygon]
    else:
        iterable = [g for g in multipolygon.geoms if isinstance(g, Polygon)]
    for polygon in iterable:
        shell = [
            projector.project_point(float(lon), float(lat))
            for lon, lat in polygon.exterior.coords
        ]
        holes = [
            [projector.project_point(float(lon), float(lat)) for lon, lat in ring.coords]
            for ring in polygon.interiors
        ]
        polygons.append(Polygon(shell=shell, holes=holes))

    projected = MultiPolygon(polygons)
    projected_mapping = mapping(projected)
    return {
        "type": projected_mapping["type"],
        "coordinates": projected_mapping["coordinates"],
    }
