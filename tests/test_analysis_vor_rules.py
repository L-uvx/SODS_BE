# tests/test_analysis_vor_rules.py
import math
import pytest
from unittest.mock import MagicMock

from shapely.geometry import MultiPolygon, Point

from app.analysis.rules.vor.common import build_vor_ring_protection_zone
from app.analysis.rules.vor.reflector_mask_area import (
    BoundVorReflectorMaskAreaRule,
    VorReflectorMaskAreaRule,
    _float_or_none,
)


# —— 辅助工具 ————————————————————————————————————


def _make_station(**overrides):
    station = MagicMock()
    station.id = 1
    station.station_type = "VOR"
    station.name = "TEST_VOR"
    station.longitude = 120.0
    station.latitude = 30.0
    station.altitude = 10.0
    station.b_to_center_distance = 3.0
    station.reflection_diameter = 30.0
    station.b_antenna_h = 2.0
    station.reflection_net_hag = 5.0
    for key, value in overrides.items():
        setattr(station, key, value)
    return station


def _make_obstacle(obstacle_id=1, name="test_obs", category="building_general",
                   geometry=None, local_geometry=None, top_elevation=0.0):
    geo = geometry or {"type": "Point", "coordinates": [120.0, 30.0]}
    local = local_geometry or geo
    return {
        "obstacleId": obstacle_id,
        "name": name,
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": category,
        "geometry": geo,
        "localGeometry": local,
        "topElevation": top_elevation,
    }


# —— _float_or_none ——————————————————————————————


def test_float_or_none_returns_float():
    assert _float_or_none(3.14) == 3.14


def test_float_or_none_returns_none():
    assert _float_or_none(None) is None


# —— bind 成功 ———————————————————————————————————


def test_bind_returns_bound_rule():
    station = _make_station()
    rule = VorReflectorMaskAreaRule()
    bound = rule.bind(station=station, station_point=(1000.0, 2000.0))
    assert bound is not None
    assert isinstance(bound, BoundVorReflectorMaskAreaRule)
    assert isinstance(bound.protection_zone.local_geometry, MultiPolygon)


# —— bind 缺参 ———————————————————————————————————


@pytest.mark.parametrize("field", [
    "b_to_center_distance", "reflection_diameter",
    "b_antenna_h", "reflection_net_hag",
])
def test_bind_returns_none_when_missing_parameter(field):
    station = _make_station(**{field: None})
    rule = VorReflectorMaskAreaRule()
    assert rule.bind(station=station, station_point=(0.0, 0.0)) is None


# —— bind D/2 >= rt（环带退化） —————————————————————


def test_bind_returns_none_when_ring_degenerate():
    station = _make_station(
        b_to_center_distance=0.1,
        reflection_diameter=200.0,    # D/2 = 100
        b_antenna_h=10.0,
        reflection_net_hag=0.1,       # rt ≈ D/2 = 100 → outer ≤ inner
    )
    rule = VorReflectorMaskAreaRule()
    assert rule.bind(station=station, station_point=(0.0, 0.0)) is None


# —— analyze 未进入环带 ——————————————————————————


def test_analyze_outside_ring_is_compliant():
    station = _make_station()
    station_point = (0.0, 0.0)
    rule = VorReflectorMaskAreaRule()
    bound = rule.bind(station=station, station_point=station_point)

    d = station.reflection_diameter
    rt_calc = math.tan(math.atan((d/2 - station.b_to_center_distance) / station.b_antenna_h)) * station.reflection_net_hag + d/2
    outer = min(rt_calc, 100.0)
    far_radius = outer + 50.0

    obstacle_point = Point(station_point[0] + far_radius, station_point[1])
    obstacle = _make_obstacle(
        geometry={"type": "Point", "coordinates": [obstacle_point.x, obstacle_point.y]},
        local_geometry={"type": "Point", "coordinates": [obstacle_point.x, obstacle_point.y]},
        top_elevation=0.0,
    )
    result = bound.analyze(obstacle)
    assert result.is_compliant is True
    assert "outside" in result.message


# —— analyze 进入环带且高度合规 ——————————————————


def test_analyze_inside_ring_height_ok():
    station = _make_station()
    station_point = (0.0, 0.0)
    rule = VorReflectorMaskAreaRule()
    bound = rule.bind(station=station, station_point=station_point)

    mid_radius = 20.0  # between D/2=15 and outer
    obstacle_point = Point(station_point[0] + mid_radius, station_point[1])
    obstacle = _make_obstacle(
        geometry={"type": "Point", "coordinates": [obstacle_point.x, obstacle_point.y]},
        local_geometry={"type": "Point", "coordinates": [obstacle_point.x, obstacle_point.y]},
        top_elevation=station.altitude - 1.0,  # 远低于保护区限高
    )
    result = bound.analyze(obstacle)
    assert result.is_compliant is True


# —— analyze 进入环带且超限 ——————————————————————


def test_analyze_inside_ring_height_exceeded():
    station = _make_station()
    station_point = (0.0, 0.0)
    rule = VorReflectorMaskAreaRule()
    bound = rule.bind(station=station, station_point=station_point)

    mid_radius = 20.0
    obstacle_point = Point(station_point[0] + mid_radius, station_point[1])

    d = station.reflection_diameter
    r = station.b_to_center_distance
    h1 = station.reflection_net_hag
    h2 = station.b_antenna_h
    alt = station.altitude
    delta = max(d/2 - r, 0.001)
    slope = -h2 / delta
    intercept = h1 - slope * d/2
    allowed_at_mid = slope * mid_radius + intercept + alt

    obstacle = _make_obstacle(
        geometry={"type": "Point", "coordinates": [obstacle_point.x, obstacle_point.y]},
        local_geometry={"type": "Point", "coordinates": [obstacle_point.x, obstacle_point.y]},
        top_elevation=allowed_at_mid + 10.0,
    )
    result = bound.analyze(obstacle)
    assert result.is_compliant is False
    assert "exceeds" in result.message


# —— analyze 度量字段 —————————————————————————————


def test_analyze_metrics_populated():
    station = _make_station()
    station_point = (0.0, 0.0)
    rule = VorReflectorMaskAreaRule()
    bound = rule.bind(station=station, station_point=station_point)

    mid_radius = 20.0
    obstacle_point = Point(station_point[0] + mid_radius, station_point[1])
    obstacle = _make_obstacle(
        geometry={"type": "Point", "coordinates": [obstacle_point.x, obstacle_point.y]},
        local_geometry={"type": "Point", "coordinates": [obstacle_point.x, obstacle_point.y]},
        top_elevation=5.0,
    )
    result = bound.analyze(obstacle)
    assert result.metrics is not None
    assert "maxDistanceMeters" in result.metrics
    assert "clampedDistanceMeters" in result.metrics
    assert "allowedHeightMeters" in result.metrics
    assert "topElevationMeters" in result.metrics


# —— build_vor_ring_protection_zone ——————————————


def test_ring_protection_zone_is_annular():
    spec = build_vor_ring_protection_zone(
        station_id=1,
        station_type="VOR",
        rule_code="test_rule",
        rule_name="test_rule",
        zone_code="test_zone",
        zone_name="test_zone",
        region_code="default",
        region_name="default",
        station_point=(0.0, 0.0),
        inner_radius_m=10.0,
        outer_radius_m=50.0,
        base_height_meters=15.0,
        slope_meters_per_meter=-0.1,
        start_distance_meters=10.0,
        longitude=120.0,
        latitude=30.0,
    )
    assert spec is not None
    assert spec.vertical_definition["mode"] == "analytic_surface"
    surface = spec.vertical_definition["surface"]
    assert surface["clampRange"]["startMeters"] == 10.0
    assert surface["clampRange"]["endMeters"] == 50.0
    assert surface["heightModel"]["type"] == "linear_ramp"
    assert surface["heightModel"]["slopeMetersPerMeter"] == -0.1
