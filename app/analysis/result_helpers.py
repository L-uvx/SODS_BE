import math

from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry


def ceil2(value: float) -> float:
    return math.ceil(value * 100) / 100


def floor2(value: float) -> float:
    return math.floor(value * 100) / 100


def _normalize_azimuth_degrees(angle: float) -> float:
    return angle % 360.0


def _iter_boundary_coordinates(shape: BaseGeometry):
    if isinstance(shape, Point):
        yield from shape.coords
        return

    if isinstance(shape, Polygon):
        yield from shape.exterior.coords
        return

    if isinstance(shape, MultiPolygon):
        for polygon in shape.geoms:
            yield from _iter_boundary_coordinates(polygon)
        return

    boundary = shape.boundary
    if hasattr(boundary, "geoms"):
        for boundary_part in boundary.geoms:
            yield from boundary_part.coords
        return

    yield from boundary.coords


def compute_azimuth_degrees(
    station_x: float,
    station_y: float,
    target_x: float,
    target_y: float,
) -> float:
    azimuth = 90.0 - math.degrees(
        math.atan2(target_y - station_y, target_x - station_x)
    )
    if azimuth < 0:
        azimuth += 360.0
    return azimuth


def compute_horizontal_angle_range_from_geometry(
    station_point: tuple[float, float],
    geometry: BaseGeometry,
) -> tuple[float, float]:
    sx, sy = station_point
    azimuths: list[float] = []
    for x, y in _iter_boundary_coordinates(geometry):
        azimuth = compute_azimuth_degrees(sx, sy, x, y)
        azimuths.append(azimuth)

    if len(azimuths) <= 1:
        return (0.0, 0.0)

    azimuths.sort()
    gaps: list[tuple[float, int]] = []
    for i in range(len(azimuths) - 1):
        gaps.append((azimuths[i + 1] - azimuths[i], i))
    wrap_gap = (azimuths[0] + 360.0) - azimuths[-1]
    gaps.append((wrap_gap, len(azimuths) - 1))

    max_gap, max_gap_index = max(gaps, key=lambda item: item[0])

    if max_gap_index == len(azimuths) - 1:
        min_degrees = azimuths[0]
        max_degrees = azimuths[-1]
    else:
        min_degrees = azimuths[max_gap_index + 1]
        max_degrees = azimuths[max_gap_index]

    return (min_degrees, max_degrees)


# 计算障碍物相对台站点的最小包络水平夹角。
def compute_horizontal_angular_width(
    shape: BaseGeometry,
    station_point: tuple[float, float],
) -> float:
    min_deg, max_deg = compute_horizontal_angle_range_from_geometry(
        station_point, shape
    )
    if min_deg == 0.0 and max_deg == 0.0:
        return 0.0
    if min_deg <= max_deg:
        return max_deg - min_deg
    return (360.0 - min_deg) + max_deg


def compute_over_distance_meters(actual: float, limit: float) -> float:
    return max(0.0, actual - limit)
