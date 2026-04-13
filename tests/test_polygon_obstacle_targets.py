from app.application.polygon_obstacle_targets import (
    calculate_minimum_target_distance_km,
)


def test_calculate_minimum_target_distance_is_zero_when_airport_is_inside_polygon() -> (
    None
):
    obstacle_geometries = [
        {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [103.0, 30.0],
                        [103.01, 30.0],
                        [103.01, 30.01],
                        [103.0, 30.01],
                        [103.0, 30.0],
                    ]
                ]
            ],
        }
    ]

    distance_km = calculate_minimum_target_distance_km(
        airport_longitude=103.005,
        airport_latitude=30.005,
        obstacle_geometries=obstacle_geometries,
    )

    assert distance_km == 0.0
