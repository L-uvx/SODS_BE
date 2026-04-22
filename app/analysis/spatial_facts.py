from typing import Any

from shapely.geometry import MultiPolygon, Point, shape

from app.analysis.local_coordinate import AirportLocalProjector
from app.analysis.obstacle_categories import normalize_obstacle_type


# 计算障碍物在机场局部坐标系下的包围盒。
def _build_local_bounding_box(
    projector: AirportLocalProjector, geometry: dict[str, Any]
) -> dict[str, float]:
    multipolygon = shape(geometry)
    projected_points: list[tuple[float, float]] = []
    for polygon in multipolygon.geoms:
        for lon, lat in polygon.exterior.coords:
            projected_points.append(projector.project_point(float(lon), float(lat)))

    xs = [point[0] for point in projected_points]
    ys = [point[1] for point in projected_points]
    return {
        "minX": min(xs),
        "minY": min(ys),
        "maxX": max(xs),
        "maxY": max(ys),
    }


# 计算障碍物到机场参考点的最小平面距离。
def _distance_to_airport(
    projector: AirportLocalProjector, geometry: dict[str, Any]
) -> float:
    multipolygon = shape(geometry)
    projected_polygons = []
    for polygon in multipolygon.geoms:
        projected_shell = [
            projector.project_point(float(lon), float(lat))
            for lon, lat in polygon.exterior.coords
        ]
        projected_holes = [
            [
                projector.project_point(float(lon), float(lat))
                for lon, lat in ring.coords
            ]
            for ring in polygon.interiors
        ]
        projected_polygons.append((projected_shell, projected_holes))

    return float(MultiPolygon(projected_polygons).distance(Point(0.0, 0.0)))


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
                "distanceToAirportMeters": _distance_to_airport(projector, geometry),
                "localBoundingBox": _build_local_bounding_box(projector, geometry),
            }
        )

    station_items = []
    for station in context.stations:
        if station.longitude is None or station.latitude is None:
            continue

        local_x, local_y = projector.project_point(
            float(station.longitude), float(station.latitude)
        )
        station_items.append(
            {
                "stationId": station.id,
                "name": station.name,
                "localX": local_x,
                "localY": local_y,
                "altitude": (
                    float(station.altitude) if station.altitude is not None else None
                ),
            }
        )

    return {
        "airportId": airport.id,
        "referencePoint": {
            "longitude": float(airport.longitude),
            "latitude": float(airport.latitude),
        },
        "runwayCount": len(context.runways),
        "stationCount": len(context.stations),
        "obstacles": obstacle_items,
        "stations": station_items,
    }
