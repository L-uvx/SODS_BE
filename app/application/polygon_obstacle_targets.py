from math import atan2, cos, radians, sin, sqrt


EARTH_RADIUS_METERS = 6371008.8


def _haversine_distance_meters(
    longitude_a: float,
    latitude_a: float,
    longitude_b: float,
    latitude_b: float,
) -> float:
    longitude_delta = radians(longitude_b - longitude_a)
    latitude_delta = radians(latitude_b - latitude_a)
    latitude_a_radians = radians(latitude_a)
    latitude_b_radians = radians(latitude_b)

    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(latitude_a_radians)
        * cos(latitude_b_radians)
        * sin(longitude_delta / 2) ** 2
    )
    central_angle = 2 * atan2(sqrt(haversine), sqrt(1 - haversine))
    return EARTH_RADIUS_METERS * central_angle


def calculate_minimum_target_distance_km(
    *,
    airport_longitude: float,
    airport_latitude: float,
    obstacle_geometries: list[dict[str, object]],
) -> float:
    minimum_distance_meters: float | None = None

    for geometry in obstacle_geometries:
        for polygon in geometry["coordinates"]:
            for ring in polygon:
                for point_longitude, point_latitude in ring:
                    distance_meters = _haversine_distance_meters(
                        airport_longitude,
                        airport_latitude,
                        point_longitude,
                        point_latitude,
                    )
                    if (
                        minimum_distance_meters is None
                        or distance_meters < minimum_distance_meters
                    ):
                        minimum_distance_meters = distance_meters

    if minimum_distance_meters is None:
        return 0.0

    return round(minimum_distance_meters / 1000, 2)
