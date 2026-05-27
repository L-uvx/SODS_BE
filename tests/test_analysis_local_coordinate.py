from app.analysis.local_coordinate import AirportLocalProjector


def test_projector_returns_origin_for_reference_point() -> None:
    projector = AirportLocalProjector(104.123456, 30.123456)
    ox, oy = projector.project_point(104.123456, 30.123456)
    x, y = projector.project_point(104.123456, 30.123456)

    assert round(x - ox, 6) == 0.0
    assert round(y - oy, 6) == 0.0


def test_projector_preserves_relative_direction() -> None:
    projector = AirportLocalProjector(104.0, 30.0)
    origin_x, origin_y = projector.project_point(104.0, 30.0)
    east_x, east_y = projector.project_point(104.001, 30.0)
    north_x, north_y = projector.project_point(104.0, 30.001)

    # 相对坐标方向
    rel_east_x = east_x - origin_x
    rel_east_y = east_y - origin_y
    rel_north_x = north_x - origin_x
    rel_north_y = north_y - origin_y

    assert rel_east_x > 0
    assert abs(rel_east_y) < 5
    assert rel_north_y > 0
    assert abs(rel_north_x) < 5
