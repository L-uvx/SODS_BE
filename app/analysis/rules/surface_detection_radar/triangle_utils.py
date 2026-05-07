import math

from shapely.geometry import MultiPolygon, Polygon

from app.analysis.rules.geometry_helpers import ensure_multipolygon


# 按台站跑道号匹配跑道上下文。
def find_matching_runway(
    *,
    station: object,
    runways: list[dict[str, object]],
) -> dict[str, object] | None:
    station_runway_no = getattr(station, "runway_no", None)
    if station_runway_no is None:
        return None

    for runway in runways:
        if str(runway.get("runNumber")) == str(station_runway_no):
            return runway

    return None


# 构建跑道三角区几何。
def build_runway_triangle_geometry(
    *,
    station_point: tuple[float, float],
    runway: dict[str, object],
) -> MultiPolygon:
    center_x, center_y = runway["localCenterPoint"]
    direction_radians = math.radians(float(runway["directionDegrees"]))
    half_length = float(runway["lengthMeters"]) / 2.0
    axis_x = math.sin(direction_radians)
    axis_y = math.cos(direction_radians)
    runway_front = (
        float(center_x) + axis_x * half_length,
        float(center_y) + axis_y * half_length,
    )
    runway_back = (
        float(center_x) - axis_x * half_length,
        float(center_y) - axis_y * half_length,
    )
    triangle = Polygon([station_point, runway_front, runway_back, station_point])
    return ensure_multipolygon(triangle)
