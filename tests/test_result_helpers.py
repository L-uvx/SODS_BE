import math

import pytest
from shapely import wkt

from app.analysis.result_helpers import (
    _iter_boundary_coordinates,
    _normalize_azimuth_degrees,
    compute_azimuth_degrees,
    compute_horizontal_angle_range_from_geometry,
    compute_over_distance_meters,
)


@pytest.mark.parametrize(
    ("angle", "expected"),
    [
        (0.0, 0.0),
        (360.0, 0.0),
        (450.0, 90.0),
        (-90.0, 270.0),
    ],
)
def test_normalize_azimuth_degrees(angle, expected):
    assert _normalize_azimuth_degrees(angle) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("station", "target", "expected"),
    [
        ((0, 0), (1, 0), 90.0),
        ((0, 0), (0, 1), 0.0),
        ((0, 0), (-1, 0), 270.0),
        ((0, 0), (0, -1), 180.0),
        ((0, 0), (1, 1), 45.0),
    ],
)
def test_compute_azimuth_degrees(station, target, expected):
    result = compute_azimuth_degrees(station[0], station[1], target[0], target[1])
    assert result == pytest.approx(expected, abs=1e-9)


def test_iter_boundary_coordinates_point():
    pt = wkt.loads("POINT (10 20)")
    coords = list(_iter_boundary_coordinates(pt))
    assert coords == [(10.0, 20.0)]


def test_iter_boundary_coordinates_polygon():
    poly = wkt.loads("POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))")
    coords = list(_iter_boundary_coordinates(poly))
    assert len(coords) == 5
    assert (0.0, 0.0) in coords
    assert (1.0, 0.0) in coords


def test_iter_boundary_coordinates_multipolygon():
    mp = wkt.loads("MULTIPOLYGON (((0 0, 1 0, 1 1, 0 1, 0 0)), ((2 2, 3 2, 3 3, 2 3, 2 2)))")
    coords = list(_iter_boundary_coordinates(mp))
    assert len(coords) == 10


class TestComputeHorizontalAngleRangeFromGeometry:
    # 正常区间：所有点集中，不跨越 360°
    def test_normal_range(self):
        pt = (0, 0)
        poly = wkt.loads("POLYGON ((1 1, 1 0.5, 0.5 0.5, 0.5 1, 1 1))")
        min_h, max_h = compute_horizontal_angle_range_from_geometry(pt, poly)
        assert min_h == pytest.approx(26.565, abs=0.5)
        assert max_h == pytest.approx(63.435, abs=0.5)

    # 单点：返回 (0, 0)
    def test_point(self):
        pt = (0, 0)
        point = wkt.loads("POINT (10 0)")
        min_h, max_h = compute_horizontal_angle_range_from_geometry(pt, point)
        assert min_h == 0.0
        assert max_h == 0.0

    # 跨越 360° 的障碍物多边形
    def test_wrap_across_360(self):
        station = (0, 0)

        p1 = _azimuth_point(station, 358)
        p2 = _azimuth_point(station, 357)
        p3 = _azimuth_point(station, 2)
        p4 = _azimuth_point(station, 1)

        poly = _polygon_from_points([p1, p2, p3, p4])
        min_h, max_h = compute_horizontal_angle_range_from_geometry(station, poly)

        assert min_h == pytest.approx(357, abs=1)
        assert max_h == pytest.approx(2, abs=1)

    # 跨越 0° 的另一场景
    def test_wrap_near_0(self):
        station = (0, 0)
        p1 = _azimuth_point(station, 359)
        p2 = _azimuth_point(station, 0.5)
        p3 = _azimuth_point(station, 1)

        poly = _polygon_from_points([p1, p2, p3])
        min_h, max_h = compute_horizontal_angle_range_from_geometry(station, poly)

        assert min_h == pytest.approx(359, abs=0.5)
        assert max_h == pytest.approx(1, abs=0.5)

    # 覆盖所有方位 360°：应有最大 gap 使得范围仍保持
    def test_full_circle(self):
        station = (0, 0)
        pts = [_azimuth_point(station, a) for a in range(0, 360, 30)]
        poly = _polygon_from_points(pts)
        min_h, max_h = compute_horizontal_angle_range_from_geometry(station, poly)
        assert min_h == pytest.approx(0, abs=0.5)
        assert max_h == pytest.approx(330, abs=0.5)


def _azimuth_point(station, angle_deg: float, distance: float = 10.0):
    rad = math.radians(angle_deg)
    dx = distance * math.sin(rad)
    dy = distance * math.cos(rad)
    return (station[0] + dx, station[1] + dy)


def _polygon_from_points(points):
    coords = [(x, y) for x, y in points]
    coords.append(coords[0])
    poly_wkt = "POLYGON ((" + ", ".join(f"{x} {y}" for x, y in coords) + "))"
    return wkt.loads(poly_wkt)


class TestComputeOverDistanceMeters:
    def test_within_limit(self):
        assert compute_over_distance_meters(5.0, 10.0) == 0.0

    def test_equal(self):
        assert compute_over_distance_meters(10.0, 10.0) == 0.0

    def test_exceeds(self):
        assert compute_over_distance_meters(15.0, 10.0) == 5.0
