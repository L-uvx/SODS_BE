from shapely.geometry import MultiPolygon, shape
from shapely.geometry.base import BaseGeometry

from app.analysis.rules.gp.site_protection.helpers import (
    GpSiteProtectionSharedContext,
)


GP_CABLE_CATEGORIES = frozenset({"power_or_communication_cable"})
GP_AIRPORT_RING_ROAD_CATEGORIES = frozenset({"airport_ring_road"})
GP_ROAD_OR_RAIL_CATEGORIES = frozenset(
    {"road", "railway_electrified", "railway_non_electrified"}
)


# 判断是否为 GP 线缆类障碍物。
def is_gp_cable_category(category: str) -> bool:
    return category in GP_CABLE_CATEGORIES


# 判断是否为 GP 机场环场路障碍物。
def is_gp_airport_ring_road_category(category: str) -> bool:
    return category in GP_AIRPORT_RING_ROAD_CATEGORIES


# 判断是否为 GP 道路或铁路类障碍物。
def is_gp_road_or_rail_category(category: str) -> bool:
    return category in GP_ROAD_OR_RAIL_CATEGORIES


# 计算障碍物进入保护区后的最小前向投影距离。
def calculate_gp_zone_intersection_min_forward_distance_meters(
    *,
    obstacle_geometry: dict[str, object],
    zone_geometry: MultiPolygon,
    shared_context: GpSiteProtectionSharedContext,
) -> float | None:
    obstacle = shape(obstacle_geometry)
    intersection = zone_geometry.intersection(obstacle)
    if intersection.is_empty:
        return None

    candidate_points = _collect_projection_candidate_points(intersection)
    if not candidate_points:
        representative_point = intersection.representative_point()
        candidate_points = [(representative_point.x, representative_point.y)]

    station_x, station_y = shared_context.station_point
    axis_x, axis_y = shared_context.axis_unit
    return min(
        (point_x - station_x) * axis_x + (point_y - station_y) * axis_y
        for point_x, point_y in candidate_points
    )


def _collect_projection_candidate_points(
    geometry: BaseGeometry,
) -> list[tuple[float, float]]:
    geometry_type = geometry.geom_type

    if geometry_type == "Point":
        return [(float(geometry.x), float(geometry.y))]

    if geometry_type == "LineString":
        return [(float(x), float(y)) for x, y in geometry.coords]

    if geometry_type == "Polygon":
        return [(float(x), float(y)) for x, y in geometry.exterior.coords]

    geoms = getattr(geometry, "geoms", None)
    if geoms is None:
        return []

    candidate_points: list[tuple[float, float]] = []
    for child_geometry in geoms:
        candidate_points.extend(_collect_projection_candidate_points(child_geometry))
    return candidate_points


__all__ = [
    "calculate_gp_zone_intersection_min_forward_distance_meters",
    "is_gp_airport_ring_road_category",
    "is_gp_cable_category",
    "is_gp_road_or_rail_category",
]
