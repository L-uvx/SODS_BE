# tests/test_analysis_vor_rules.py
import math
import pytest
from unittest.mock import MagicMock

from shapely.geometry import MultiPolygon, Point, Polygon

from app.analysis.rules.vor.common import build_vor_ring_protection_zone
from app.analysis.rules.vor.elevation_angle._100_200_1_5 import Vor100_200_1_5_Rule
from app.analysis.rules.vor.elevation_angle._200_300_1_5 import Vor200_300_1_5_Rule
from app.analysis.rules.vor.elevation_angle._300_outside_2_5 import Vor300Outside2_5_Rule
from app.analysis.rules.vor.elevation_angle._shared import (
    BoundVorElevationAngleRule,
    compute_horizontal_angular_width,
)
from app.analysis.rules.vor.profile import VorRuleProfile
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
    station.coverage_radius = 1800.0
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


def _point_geometry(x, y):
    return {"type": "Point", "coordinates": [x, y]}


def _polygon_geometry(coordinates):
    closed = list(coordinates)
    if closed[0] != closed[-1]:
        closed.append(closed[0])
    return {"type": "Polygon", "coordinates": [closed]}


def _polar_point(radius, degrees):
    radians = math.radians(degrees)
    return (radius * math.cos(radians), radius * math.sin(radians))


def _sector_like_polygon(inner_radius, outer_radius, start_degrees, end_degrees):
    return Polygon([
        _polar_point(inner_radius, start_degrees),
        _polar_point(outer_radius, start_degrees),
        _polar_point(outer_radius, end_degrees),
        _polar_point(inner_radius, end_degrees),
    ])


# —— _float_or_none ——————————————————————————————


def test_float_or_none_returns_float():
    assert _float_or_none(3.14) == 3.14


def test_float_or_none_returns_none():
    assert _float_or_none(None) is None


# —— horizontal angle helper —————————————————————————


def test_compute_horizontal_angular_width_point_is_zero():
    assert compute_horizontal_angular_width(Point(100.0, 0.0), (0.0, 0.0)) == 0.0


def test_compute_horizontal_angular_width_matches_known_span():
    shape = _sector_like_polygon(120.0, 140.0, 20.0, 50.0)
    width = compute_horizontal_angular_width(shape, (0.0, 0.0))
    assert width == pytest.approx(30.0, abs=0.2)


def test_compute_horizontal_angular_width_handles_wrap_around():
    shape = _sector_like_polygon(120.0, 140.0, 350.0, 370.0)
    width = compute_horizontal_angular_width(shape, (0.0, 0.0))
    assert width == pytest.approx(20.0, abs=0.2)


# —— bind 成功 ———————————————————————————————————


def test_bind_returns_bound_rule():
    station = _make_station()
    rule = VorReflectorMaskAreaRule()
    bound = rule.bind(station=station, station_point=(1000.0, 2000.0))
    assert bound is not None
    assert isinstance(bound, BoundVorReflectorMaskAreaRule)
    assert isinstance(bound.protection_zone.local_geometry, MultiPolygon)


def test_vor_100_200_1_5_bind_returns_bound_rule():
    station = _make_station()
    bound = Vor100_200_1_5_Rule().bind(station=station, station_point=(0.0, 0.0))
    assert bound is not None
    assert isinstance(bound, BoundVorElevationAngleRule)
    assert bound.protection_zone.zone_code == "vor_100_200_1_5_deg"


@pytest.mark.parametrize("field", ["altitude", "reflection_net_hag"])
def test_vor_100_200_1_5_bind_returns_none_when_missing_required_param(field):
    station = _make_station(**{field: None})
    bound = Vor100_200_1_5_Rule().bind(station=station, station_point=(0.0, 0.0))
    assert bound is None


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

    far_radius = 150.0  # 远超 100m 环带外径
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


# —— analyze 超出阴影外缘但在 100m 环带内 ——————————


def test_analyze_beyond_shadow_radius_within_100m():
    station = _make_station()
    station_point = (0.0, 0.0)
    rule = VorReflectorMaskAreaRule()
    bound = rule.bind(station=station, station_point=station_point)

    d = station.reflection_diameter
    r = station.b_to_center_distance
    h1 = station.reflection_net_hag
    h2 = station.b_antenna_h
    alt = station.altitude
    delta = max(d/2 - r, 0.001)
    slope = -h2 / delta
    intercept = h1 - slope * d/2
    rt_calc = math.tan(math.atan((d/2 - r) / h2)) * h1 + d/2
    shadow_radius = min(rt_calc, 100.0)

    # 障碍物在 80m 处，超出阴影外缘 shadow_radius≈45m，但在 100m 环带内
    obstacle_radius = 80.0
    obstacle_point = Point(station_point[0] + obstacle_radius, station_point[1])

    # x 应被夹到 shadow_radius，限高为 H(shadow_radius)
    allowed_at_shadow = slope * shadow_radius + intercept + alt

    # 障碍物超限应失败
    obstacle = _make_obstacle(
        geometry={"type": "Point", "coordinates": [obstacle_point.x, obstacle_point.y]},
        local_geometry={"type": "Point", "coordinates": [obstacle_point.x, obstacle_point.y]},
        top_elevation=allowed_at_shadow + 5.0,
    )
    result = bound.analyze(obstacle)
    assert result.is_compliant is False
    assert "exceeds" in result.message
    # x 应被夹到 shadow_radius
    assert result.metrics["clampedDistanceMeters"] == pytest.approx(shadow_radius)


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
    assert "shadowRadiusMeters" in result.metrics


# —— 100m-200m 1.5° 仰角区 ————————————————————————


def test_vor_100_200_1_5_analyze_outside_ring_is_compliant():
    bound = Vor100_200_1_5_Rule().bind(
        station=_make_station(), station_point=(0.0, 0.0)
    )

    obstacle = _make_obstacle(
        local_geometry=_point_geometry(250.0, 0.0),
        geometry=_point_geometry(250.0, 0.0),
        top_elevation=50.0,
        category="tree_or_forest",
    )

    result = bound.analyze(obstacle)
    assert result.is_applicable is True
    assert result.is_compliant is True
    assert "outside" in result.message


def test_vor_100_200_1_5_analyze_below_benchmark_plane_is_compliant():
    station = _make_station()
    bound = Vor100_200_1_5_Rule().bind(station=station, station_point=(0.0, 0.0))

    obstacle = _make_obstacle(
        local_geometry=_point_geometry(150.0, 0.0),
        geometry=_point_geometry(150.0, 0.0),
        top_elevation=station.altitude + station.reflection_net_hag - 0.1,
        category="tree_or_forest",
    )

    result = bound.analyze(obstacle)
    assert result.is_compliant is True
    assert "below benchmark" in result.message


def test_vor_100_200_1_5_analyze_vertical_angle_exceeded_is_non_compliant():
    station = _make_station()
    bound = Vor100_200_1_5_Rule().bind(station=station, station_point=(0.0, 0.0))
    base_height = station.altitude + station.reflection_net_hag

    obstacle = _make_obstacle(
        local_geometry=_point_geometry(150.0, 0.0),
        geometry=_point_geometry(150.0, 0.0),
        top_elevation=base_height + 10.0,
        category="tree_or_forest",
    )

    result = bound.analyze(obstacle)
    assert result.is_compliant is False
    assert "elevation angle limit" in result.message
    assert result.metrics["verticalAngleDegrees"] > 1.5


def test_vor_100_200_1_5_analyze_horizontal_angle_exceeded_is_non_compliant():
    station = _make_station()
    bound = Vor100_200_1_5_Rule().bind(station=station, station_point=(0.0, 0.0))
    shape = _sector_like_polygon(120.0, 150.0, 0.0, 10.0)
    base_height = station.altitude + station.reflection_net_hag

    obstacle = _make_obstacle(
        local_geometry=_polygon_geometry(list(shape.exterior.coords)[:-1]),
        geometry=_polygon_geometry(list(shape.exterior.coords)[:-1]),
        top_elevation=base_height + 1.0,
        category="tree_or_forest",
    )

    result = bound.analyze(obstacle)
    assert result.is_compliant is False
    assert "horizontal angle limit" in result.message
    assert result.metrics["horizontalAngularWidthDegrees"] > 7.0


def test_vor_100_200_1_5_analyze_within_limits_is_compliant():
    station = _make_station()
    bound = Vor100_200_1_5_Rule().bind(station=station, station_point=(0.0, 0.0))
    shape = _sector_like_polygon(120.0, 150.0, 1.0, 6.0)
    base_height = station.altitude + station.reflection_net_hag

    obstacle = _make_obstacle(
        local_geometry=_polygon_geometry(list(shape.exterior.coords)[:-1]),
        geometry=_polygon_geometry(list(shape.exterior.coords)[:-1]),
        top_elevation=base_height + 2.0,
        category="tree_or_forest",
    )

    result = bound.analyze(obstacle)
    assert result.is_compliant is True
    assert result.metrics["verticalAngleDegrees"] < 1.5
    assert result.metrics["horizontalAngularWidthDegrees"] < 7.0


# —— 200m-300m 1.5° 仰角区 ————————————————————————


def test_vor_200_300_1_5_analyze_vertical_angle_exceeded_is_non_compliant():
    station = _make_station()
    bound = Vor200_300_1_5_Rule().bind(station=station, station_point=(0.0, 0.0))
    base_height = station.altitude + station.reflection_net_hag

    obstacle = _make_obstacle(
        local_geometry=_point_geometry(250.0, 0.0),
        geometry=_point_geometry(250.0, 0.0),
        top_elevation=base_height + 10.0,
        category="building_general",
    )

    result = bound.analyze(obstacle)
    assert result.is_compliant is False
    assert result.metrics["verticalAngleDegrees"] > 1.5


def test_vor_200_300_1_5_analyze_horizontal_angle_exceeded_is_non_compliant():
    station = _make_station()
    bound = Vor200_300_1_5_Rule().bind(station=station, station_point=(0.0, 0.0))
    shape = _sector_like_polygon(220.0, 250.0, 0.0, 12.0)
    base_height = station.altitude + station.reflection_net_hag

    obstacle = _make_obstacle(
        local_geometry=_polygon_geometry(list(shape.exterior.coords)[:-1]),
        geometry=_polygon_geometry(list(shape.exterior.coords)[:-1]),
        top_elevation=base_height + 1.0,
        category="building_general",
    )

    result = bound.analyze(obstacle)
    assert result.is_compliant is False
    assert "horizontal angle limit" in result.message
    assert result.metrics["horizontalAngularWidthDegrees"] > 10.0


def test_vor_200_300_1_5_analyze_within_limits_is_compliant():
    station = _make_station()
    bound = Vor200_300_1_5_Rule().bind(station=station, station_point=(0.0, 0.0))
    shape = _sector_like_polygon(220.0, 250.0, 2.0, 8.0)
    base_height = station.altitude + station.reflection_net_hag

    obstacle = _make_obstacle(
        local_geometry=_polygon_geometry(list(shape.exterior.coords)[:-1]),
        geometry=_polygon_geometry(list(shape.exterior.coords)[:-1]),
        top_elevation=base_height + 3.0,
        category="building_general",
    )

    result = bound.analyze(obstacle)
    assert result.is_compliant is True
    assert result.metrics["verticalAngleDegrees"] < 1.5
    assert result.metrics["horizontalAngularWidthDegrees"] < 10.0


def test_vor_profile_200_300_rule_still_applies_to_35kv_obstacles():
    profile = VorRuleProfile()
    station = _make_station()
    obstacle = _make_obstacle(
        obstacle_id=20,
        category="power_line_high_voltage_35kv",
        local_geometry=_point_geometry(250.0, 0.0),
        geometry=_point_geometry(250.0, 0.0),
        top_elevation=station.altitude + station.reflection_net_hag + 1.0,
    )

    payload = profile.analyze(
        station=station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
    )

    matching_results = [
        result for result in payload.rule_results
        if result.rule_code == "vor_200_300_1_5_deg" and result.obstacle_id == 20
    ]
    assert matching_results
    assert all(result.is_applicable is True for result in matching_results)


# —— 300m 外 2.5° 仰角区 —————————————————————————


def test_vor_300_outside_2_5_bind_uses_default_outer_radius_when_coverage_missing():
    station = _make_station(coverage_radius=None)
    bound = Vor300Outside2_5_Rule().bind(station=station, station_point=(0.0, 0.0))

    assert bound is not None
    assert bound.outer_radius_m == 2000.0
    assert bound.protection_zone.zone_code == "vor_300_outside_2_5_deg"
    geometry_definition = bound.protection_zone.geometry_definition
    first_ring = geometry_definition["coordinates"][0]
    assert len(first_ring) >= 2


def test_vor_300_outside_2_5_analyze_under_300m_is_delegated():
    bound = Vor300Outside2_5_Rule().bind(
        station=_make_station(), station_point=(0.0, 0.0)
    )
    obstacle = _make_obstacle(
        local_geometry=_point_geometry(250.0, 0.0),
        geometry=_point_geometry(250.0, 0.0),
        top_elevation=100.0,
    )

    result = bound.analyze(obstacle)
    assert result.is_applicable is False
    assert result.is_compliant is True
    assert "delegated to 300m" in result.message


def test_vor_300_outside_2_5_analyze_high_voltage_within_500m_is_delegated():
    bound = Vor300Outside2_5_Rule().bind(
        station=_make_station(), station_point=(0.0, 0.0)
    )
    obstacle = _make_obstacle(
        category="power_line_high_voltage_110kv",
        local_geometry=_point_geometry(450.0, 0.0),
        geometry=_point_geometry(450.0, 0.0),
        top_elevation=100.0,
    )

    result = bound.analyze(obstacle)
    assert result.is_applicable is False
    assert result.is_compliant is True
    assert "delegated to 500m" in result.message


def test_vor_300_outside_2_5_analyze_vertical_angle_exceeded_is_non_compliant():
    station = _make_station()
    bound = Vor300Outside2_5_Rule().bind(station=station, station_point=(0.0, 0.0))
    base_height = station.altitude + station.reflection_net_hag

    obstacle = _make_obstacle(
        local_geometry=_point_geometry(600.0, 0.0),
        geometry=_point_geometry(600.0, 0.0),
        top_elevation=base_height + 30.0,
    )

    result = bound.analyze(obstacle)
    assert result.is_applicable is True
    assert result.is_compliant is False
    assert result.metrics["verticalAngleDegrees"] > 2.5


def test_vor_300_outside_2_5_analyze_within_limit_is_compliant():
    station = _make_station()
    bound = Vor300Outside2_5_Rule().bind(station=station, station_point=(0.0, 0.0))
    base_height = station.altitude + station.reflection_net_hag

    obstacle = _make_obstacle(
        local_geometry=_point_geometry(600.0, 0.0),
        geometry=_point_geometry(600.0, 0.0),
        top_elevation=base_height + 20.0,
    )

    result = bound.analyze(obstacle)
    assert result.is_applicable is True
    assert result.is_compliant is True
    assert result.metrics["verticalAngleDegrees"] < 2.5


# —— profile 集成 ———————————————————————————————————


def test_vor_profile_tree_only_reaches_100_200_rule_and_zone():
    profile = VorRuleProfile()
    station = _make_station()
    obstacle = _make_obstacle(
        category="tree_or_forest",
        local_geometry=_point_geometry(150.0, 0.0),
        geometry=_point_geometry(150.0, 0.0),
        top_elevation=station.altitude + station.reflection_net_hag + 1.0,
    )

    payload = profile.analyze(
        station=station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
    )

    elevation_rule_results = [
        result for result in payload.rule_results
        if result.rule_code in {
            "vor_100_200_1_5_deg",
            "vor_200_300_1_5_deg",
            "vor_300_outside_2_5_deg",
        }
    ]
    elevation_zone_codes = {
        zone.zone_code for zone in payload.protection_zones
        if zone.zone_code in {
            "vor_100_200_1_5_deg",
            "vor_200_300_1_5_deg",
            "vor_300_outside_2_5_deg",
        }
    }

    assert {result.rule_code for result in elevation_rule_results} == {
        "vor_100_200_1_5_deg",
        "vor_200_300_1_5_deg",
        "vor_300_outside_2_5_deg",
    }
    assert elevation_zone_codes == {
        "vor_100_200_1_5_deg",
        "vor_200_300_1_5_deg",
        "vor_300_outside_2_5_deg",
    }
    assert any(
        result.rule_code == "vor_100_200_1_5_deg" and result.is_applicable is True
        for result in elevation_rule_results
    )
    assert any(
        result.rule_code == "vor_300_outside_2_5_deg"
        and result.is_applicable is False
        for result in elevation_rule_results
    )


def test_vor_profile_mixed_categories_include_new_elevation_angle_rules():
    profile = VorRuleProfile()
    station = _make_station(coverage_radius=1200.0)
    obstacles = [
        _make_obstacle(
            obstacle_id=1,
            category="tree_or_forest",
            local_geometry=_point_geometry(150.0, 0.0),
            geometry=_point_geometry(150.0, 0.0),
            top_elevation=station.altitude + station.reflection_net_hag + 1.0,
        ),
        _make_obstacle(
            obstacle_id=2,
            category="building_general",
            local_geometry=_point_geometry(250.0, 0.0),
            geometry=_point_geometry(250.0, 0.0),
            top_elevation=station.altitude + station.reflection_net_hag + 1.0,
        ),
        _make_obstacle(
            obstacle_id=3,
            category="building_general",
            local_geometry=_point_geometry(600.0, 0.0),
            geometry=_point_geometry(600.0, 0.0),
            top_elevation=station.altitude + station.reflection_net_hag + 1.0,
        ),
    ]

    payload = profile.analyze(
        station=station,
        obstacles=obstacles,
        station_point=(0.0, 0.0),
    )

    elevation_rule_results = [
        result for result in payload.rule_results
        if result.rule_code in {
            "vor_100_200_1_5_deg",
            "vor_200_300_1_5_deg",
            "vor_300_outside_2_5_deg",
        }
    ]
    elevation_zone_codes = {
        zone.zone_code for zone in payload.protection_zones
        if zone.zone_code in {
            "vor_100_200_1_5_deg",
            "vor_200_300_1_5_deg",
            "vor_300_outside_2_5_deg",
        }
    }

    assert {result.rule_code for result in elevation_rule_results} == {
        "vor_100_200_1_5_deg",
        "vor_200_300_1_5_deg",
        "vor_300_outside_2_5_deg",
    }
    assert elevation_zone_codes == {
        "vor_100_200_1_5_deg",
        "vor_200_300_1_5_deg",
        "vor_300_outside_2_5_deg",
    }
    assert any(
        result.rule_code == "vor_100_200_1_5_deg" and result.obstacle_id == 1
        for result in elevation_rule_results
    )
    assert any(
        result.rule_code == "vor_200_300_1_5_deg" and result.obstacle_id == 2
        for result in elevation_rule_results
    )
    assert any(
        result.rule_code == "vor_300_outside_2_5_deg"
        and result.obstacle_id == 3
        and result.is_applicable is True
        for result in elevation_rule_results
    )


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
        outer_radius_m=100.0,
        base_height_meters=15.0,
        elevation_angle_degrees=-2.0,
        distance_offset_meters=10.0,
        clamp_end_meters=50.0,
        longitude=120.0,
        latitude=30.0,
    )
    assert spec is not None
    assert spec.vertical_definition["mode"] == "analytic_surface"
    surface = spec.vertical_definition["surface"]
    assert surface["clampRange"]["startMeters"] == 10.0
    assert surface["clampRange"]["endMeters"] == 50.0
    assert surface["heightModel"]["type"] == "angle_linear_rise"
    assert surface["heightModel"]["angleDegrees"] == -2.0
    assert surface["heightModel"]["distanceOffsetMeters"] == 10.0
