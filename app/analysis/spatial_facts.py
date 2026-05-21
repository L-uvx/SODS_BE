from typing import Any

from app.analysis.local_coordinate import AirportLocalProjector
from app.analysis.obstacle_categories import normalize_obstacle_type
from app.analysis.obstacle_projection import project_geometry_to_projector


# 构建机场级最小空间事实结果。
def build_airport_spatial_facts(context: Any) -> dict[str, Any]:
    airport = context.airport
    if airport.longitude is None or airport.latitude is None:
        raise ValueError(f"airport {airport.id} is missing coordinates")

    projector = AirportLocalProjector(float(airport.longitude), float(airport.latitude))

    stations = []
    for station in context.stations:
        if station.longitude is None or station.latitude is None:
            continue

        local_x, local_y = projector.project_point(
            float(station.longitude), float(station.latitude)
        )
        stations.append(
            {
                "stationId": station.id,
                "name": station.name,
                "localX": float(local_x),
                "localY": float(local_y),
            }
        )

    obstacle_items = []
    for obstacle in context.obstacles:
        if isinstance(obstacle, dict):
            obstacle_id = obstacle["id"]
            obstacle_name = obstacle["name"]
            obstacle_type = obstacle.get("obstacle_type")
            obstacle_top_elevation = obstacle.get("top_elevation")
            raw_payload = obstacle["raw_payload"]
        else:
            obstacle_id = obstacle.id
            obstacle_name = obstacle.name
            obstacle_type = getattr(obstacle, "obstacle_type", None)
            obstacle_top_elevation = getattr(obstacle, "top_elevation", None)
            raw_payload = obstacle.raw_payload

        geometry = raw_payload.get("geometry")
        local_geometry = raw_payload.get("localGeometry")
        if geometry is None and local_geometry is None:
            raise KeyError("obstacle raw_payload must contain geometry or localGeometry")
        if local_geometry is None:
            local_geometry = project_geometry_to_projector(projector, geometry)

        obstacle_items.append(
            {
                "obstacleId": obstacle_id,
                "name": obstacle_name,
                "rawObstacleType": obstacle_type,
                "globalObstacleCategory": normalize_obstacle_type(obstacle_type),
                "topElevation": (
                    float(obstacle_top_elevation)
                    if obstacle_top_elevation is not None
                    else None
                ),
                "geometry": geometry,
                "localGeometry": local_geometry,
            }
        )

    return {
        "airportId": airport.id,
        "stationCount": len(getattr(context, "stations", [])),
        "stations": stations,
        "obstacles": obstacle_items,
    }
