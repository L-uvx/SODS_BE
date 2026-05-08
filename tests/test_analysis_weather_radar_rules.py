from unittest.mock import MagicMock

from app.analysis.rules.weather_radar.profile import WeatherRadarRuleProfile


def _make_station(**overrides):
    station = MagicMock()
    station.id = 1
    station.station_type = "WeatherRadar"
    station.name = "TEST_WEATHER_RADAR"
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


def test_weather_radar_450m_applies_to_non_special_categories() -> None:
    payload = WeatherRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(category="building_general", local_geometry=_point_geometry(300.0, 0.0))],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "weather_radar_minimum_distance_450m")
    assert result.is_compliant is False


def test_weather_radar_450m_skips_special_interference_categories() -> None:
    payload = WeatherRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(category="fm_broadcast", local_geometry=_point_geometry(300.0, 0.0))],
        station_point=(0.0, 0.0),
    )

    assert not any(result.rule_code == "weather_radar_minimum_distance_450m" for result in payload.rule_results)


def test_weather_radar_800m_applies_to_special_interference_categories() -> None:
    payload = WeatherRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(category="fm_broadcast", local_geometry=_point_geometry(700.0, 0.0))],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "weather_radar_minimum_distance_800m")
    assert result.is_compliant is False


def test_weather_radar_800m_does_not_apply_to_non_special_category_inside_450m() -> None:
    payload = WeatherRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(category="building_general", local_geometry=_point_geometry(300.0, 0.0))],
        station_point=(0.0, 0.0),
    )

    assert not any(result.rule_code == "weather_radar_minimum_distance_800m" for result in payload.rule_results)


def test_weather_radar_450m_boundary_distance_is_compliant() -> None:
    payload = WeatherRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(category="building_general", local_geometry=_point_geometry(450.0, 0.0))],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "weather_radar_minimum_distance_450m")
    assert result.is_compliant is True


def test_weather_radar_800m_boundary_distance_is_compliant() -> None:
    payload = WeatherRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(category="fm_broadcast", local_geometry=_point_geometry(800.0, 0.0))],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "weather_radar_minimum_distance_800m")
    assert result.is_compliant is True


def test_weather_radar_1deg_skips_obstacle_inside_450m() -> None:
    payload = WeatherRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(category="building_general", local_geometry=_point_geometry(300.0, 0.0))],
        station_point=(0.0, 0.0),
    )

    assert not any(result.rule_code == "weather_radar_elevation_angle_1deg" for result in payload.rule_results)


def test_weather_radar_1deg_skips_special_category_between_450m_and_800m() -> None:
    payload = WeatherRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(category="fm_broadcast", local_geometry=_point_geometry(700.0, 0.0))],
        station_point=(0.0, 0.0),
    )

    assert not any(result.rule_code == "weather_radar_elevation_angle_1deg" for result in payload.rule_results)


def test_weather_radar_1deg_fails_when_elevation_angle_exceeds_1deg() -> None:
    payload = WeatherRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(category="building_general", local_geometry=_point_geometry(1000.0, 0.0), top_elevation=60.0)],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "weather_radar_elevation_angle_1deg")
    assert result.is_compliant is False


def test_weather_radar_1deg_skips_obstacle_outside_coverage_radius() -> None:
    payload = WeatherRadarRuleProfile().analyze(
        station=_make_station(coverage_radius=1500.0),
        obstacles=[_make_obstacle(category="building_general", local_geometry=_point_geometry(1600.0, 0.0), top_elevation=60.0)],
        station_point=(0.0, 0.0),
    )

    assert not any(result.rule_code == "weather_radar_elevation_angle_1deg" for result in payload.rule_results)


def test_weather_radar_1deg_protection_zone_uses_analytic_surface_vertical_definition() -> None:
    payload = WeatherRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(category="building_general", local_geometry=_point_geometry(1000.0, 0.0), top_elevation=20.0)],
        station_point=(0.0, 0.0),
    )

    protection_zone = next(zone for zone in payload.protection_zones if zone.rule_code == "weather_radar_elevation_angle_1deg")
    vertical_definition = protection_zone.vertical_definition
    assert vertical_definition["mode"] == "analytic_surface"
    assert vertical_definition["surface"]["type"] == "radial_cone_surface"
    assert vertical_definition["surface"]["heightModel"]["type"] == "angle_linear_rise"
    assert vertical_definition["surface"]["heightModel"]["angleDegrees"] == 1.0
