from dataclasses import dataclass

from app.application.polygon_obstacle_excel_parser import PolygonObstacle


class PolygonObstacleGeometryError(ValueError):
    pass


@dataclass(frozen=True)
class BuiltPolygonObstacleGeometry:
    coordinates: list[list[list[list[float]]]]
    wkt: str


def _close_ring(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if points[0] == points[-1]:
        return points
    return [*points, points[0]]


def build_multipolygon_geometry(
    obstacle: PolygonObstacle,
) -> BuiltPolygonObstacleGeometry:
    unique_points = {
        (point.longitude_decimal, point.latitude_decimal) for point in obstacle.points
    }
    if len(unique_points) < 3:
        raise PolygonObstacleGeometryError(
            f"obstacle {obstacle.name} must contain at least 3 distinct points"
        )

    ring = _close_ring(
        [(point.longitude_decimal, point.latitude_decimal) for point in obstacle.points]
    )
    coordinates = [[[list(point) for point in ring]]]
    joined_points = ", ".join(f"{longitude} {latitude}" for longitude, latitude in ring)
    wkt = f"MULTIPOLYGON ((({joined_points})))"
    return BuiltPolygonObstacleGeometry(coordinates=coordinates, wkt=wkt)
