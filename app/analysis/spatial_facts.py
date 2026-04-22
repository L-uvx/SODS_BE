from typing import Any

from shapely.geometry import MultiPolygon, Polygon, shape

from app.analysis.local_coordinate import AirportLocalProjector
from app.analysis.obstacle_categories import normalize_obstacle_type


# 将经纬度障碍物几何投影到机场局部米制坐标系。
def _project_geometry(
    projector: AirportLocalProjector, geometry: dict[str, Any]
) -> dict[str, Any]:
    multipolygon = shape(geometry)
    polygons: list[Polygon] = []
    for polygon in multipolygon.geoms:
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
    return {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [[float(x), float(y)] for x, y in polygon.exterior.coords],
                *[
                    [[float(x), float(y)] for x, y in ring.coords]
                    for ring in polygon.interiors
                ],
            ]
            for polygon in projected.geoms
        ],
    }


# 构建机场级最小空间事实结果。
def build_airport_spatial_facts(context: Any) -> dict[str, Any]:
    airport = context.airport
    if airport.longitude is None or airport.latitude is None:
        raise ValueError(f"airport {airport.id} is missing coordinates")

    projector = AirportLocalProjector(float(airport.longitude), float(airport.latitude))

    obstacle_items = []
    for obstacle in context.obstacles:
        if isinstance(obstacle, dict):
            obstacle_id = obstacle["id"]
            obstacle_name = obstacle["name"]
            obstacle_type = obstacle.get("obstacle_type")
            raw_payload = obstacle["raw_payload"]
        else:
            obstacle_id = obstacle.id
            obstacle_name = obstacle.name
            obstacle_type = getattr(obstacle, "obstacle_type", None)
            raw_payload = obstacle.raw_payload

        geometry = raw_payload["geometry"]
        obstacle_items.append(
            {
                "obstacleId": obstacle_id,
                "name": obstacle_name,
                "rawObstacleType": obstacle_type,
                "globalObstacleCategory": normalize_obstacle_type(obstacle_type),
                "geometry": geometry,
                "localGeometry": _project_geometry(projector, geometry),
            }
        )

    return {
        "airportId": airport.id,
        "obstacles": obstacle_items,
    }
