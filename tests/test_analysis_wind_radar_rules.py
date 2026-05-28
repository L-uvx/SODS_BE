import math
from unittest.mock import MagicMock

import pytest

from app.analysis.rules.wind_radar.profile import WindRadarRuleProfile


def _make_station(**overrides):
    station = MagicMock()
    station.id = 1
    station.station_type = "WindRadar"
    station.name = "TEST_WIND_RADAR"
    station.longitude = 120.0
    station.latitude = 30.0
    station.altitude = 10.0
    station.antenna_hag = 20.0
    station.coverage_radius = 1800.0
    for key, value in overrides.items():
        setattr(station, key, value)
    return station


def _make_obstacle(
    obstacle_id=1,
    *,
    name="test_obs",
    category="building_general",
    local_geometry=None,
    top_elevation=0.0,
):
    geometry = local_geometry or {"type": "Point", "coordinates": [1000.0, 0.0]}
    return {
        "obstacleId": obstacle_id,
        "name": name,
        "rawObstacleType": "测试障碍物",
        "globalObstacleCategory": category,
        "geometry": geometry,
        "localGeometry": geometry,
        "topElevation": top_elevation,
    }


def _point_geometry(x, y):
    return {"type": "Point", "coordinates": [x, y]}


def _find_rule_result(payload, rule_code):
    return next(result for result in payload.rule_results if result.rule_code == rule_code)


def test_wind_radar_fails_when_angle_exceeds_15deg_threshold() -> None:
    payload = WindRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(local_geometry=_point_geometry(1000.0, 0.0), top_elevation=400.0)],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "wind_radar_elevation_angle_15deg")
    assert result.is_compliant is False

    assert result.over_distance_meters >= 0.0
    assert 0.0 <= result.azimuth_degrees < 360.0
    assert 0.0 <= result.max_horizontal_angle_degrees < 360.0
    assert 0.0 <= result.min_horizontal_angle_degrees < 360.0
    assert isinstance(result.relative_height_meters, float)
    assert isinstance(result.is_in_radius, bool)
    assert isinstance(result.is_in_zone, bool)
    assert isinstance(result.details, str)
    assert len(result.details) > 0


def test_wind_radar_protection_zone_angle_is_15deg() -> None:
    payload = WindRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(local_geometry=_point_geometry(1000.0, 0.0), top_elevation=20.0)],
        station_point=(0.0, 0.0),
    )

    zone = payload.protection_zones[0]
    assert zone.vertical_definition["mode"] == "analytic_surface"
    assert zone.vertical_definition["surface"]["type"] == "radial_cone_surface"
    assert zone.vertical_definition["surface"]["heightModel"]["type"] == "angle_linear_rise"
    assert zone.vertical_definition["surface"]["heightModel"]["angleDegrees"] == 15.0


def test_wind_radar_limit_height_uses_tan_15deg() -> None:
    station = _make_station()
    distance = 1000.0
    expected_allowed = float(station.altitude + station.antenna_hag) + distance * math.tan(
        math.radians(15.0)
    )

    payload = WindRadarRuleProfile().analyze(
        station=station,
        obstacles=[
            _make_obstacle(
                local_geometry=_point_geometry(distance, 0.0), top_elevation=0.0
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "wind_radar_elevation_angle_15deg")
    assert result.is_compliant is True
    assert result.metrics["allowedHeightMeters"] == pytest.approx(expected_allowed, rel=1e-6)
    assert result.metrics["limitAngleDegrees"] == 15.0


def test_wind_radar_14deg_elevation_is_compliant() -> None:
    station = _make_station()
    base_height = float(station.altitude + station.antenna_hag)
    distance = 1000.0
    top = base_height + distance * math.tan(math.radians(14.0))

    payload = WindRadarRuleProfile().analyze(
        station=station,
        obstacles=[
            _make_obstacle(local_geometry=_point_geometry(distance, 0.0), top_elevation=top)
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "wind_radar_elevation_angle_15deg")
    assert result.is_compliant is True


def test_wind_radar_16deg_elevation_is_non_compliant() -> None:
    station = _make_station()
    base_height = float(station.altitude + station.antenna_hag)
    distance = 1000.0
    top = base_height + distance * math.tan(math.radians(16.0))

    payload = WindRadarRuleProfile().analyze(
        station=station,
        obstacles=[
            _make_obstacle(local_geometry=_point_geometry(distance, 0.0), top_elevation=top)
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "wind_radar_elevation_angle_15deg")
    assert result.is_compliant is False
