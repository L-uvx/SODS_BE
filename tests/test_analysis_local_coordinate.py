from app.analysis.local_coordinate import AirportLocalProjector


def test_projector_returns_origin_for_reference_point() -> None:
    projector = AirportLocalProjector(104.123456, 30.123456)
    x, y = projector.project_point(104.123456, 30.123456)

    assert round(x, 6) == 0.0
    assert round(y, 6) == 0.0


def test_projector_preserves_relative_direction() -> None:
    projector = AirportLocalProjector(104.0, 30.0)
    east_x, east_y = projector.project_point(104.001, 30.0)
    north_x, north_y = projector.project_point(104.0, 30.001)

    assert east_x > 0
    assert abs(east_y) < 5
    assert north_y > 0
    assert abs(north_x) < 5
