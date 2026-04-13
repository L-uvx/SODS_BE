from pyproj import Transformer
from shapely.geometry import MultiPolygon, Point, shape
from shapely.ops import transform


_PROJECT_TO_METERS = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:3857",
    always_xy=True,
).transform


def calculate_minimum_target_distance_km(
    *,
    airport_longitude: float,
    airport_latitude: float,
    obstacle_geometries: list[dict[str, object]],
) -> float:
    airport_point = transform(
        _PROJECT_TO_METERS, Point(airport_longitude, airport_latitude)
    )
    minimum_distance_meters: float | None = None

    for geometry in obstacle_geometries:
        obstacle_shape = shape(geometry)
        if not isinstance(obstacle_shape, MultiPolygon):
            obstacle_shape = MultiPolygon([obstacle_shape])
        projected_obstacle = transform(_PROJECT_TO_METERS, obstacle_shape)
        distance_meters = airport_point.distance(projected_obstacle)
        if minimum_distance_meters is None or distance_meters < minimum_distance_meters:
            minimum_distance_meters = distance_meters

    if minimum_distance_meters is None:
        return 0.0

    return round(minimum_distance_meters / 1000, 2)
