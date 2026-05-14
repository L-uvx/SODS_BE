from unittest.mock import MagicMock

from app.analysis.rules.adsb.profile import AdsbRuleProfile


def _make_station(**overrides):
    station = MagicMock()
    station.id = 1
    station.station_type = "ADS_B"
    station.name = "TEST_ADSB"
    station.longitude = 120.0
    station.latitude = 30.0
    station.altitude = 10.0
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


def test_adsb_0_5km_applies_to_non_electrified_railway_with_lte_boundary() -> None:
    payload = AdsbRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="railway_non_electrified",
                local_geometry=_point_geometry(500.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "adsb_minimum_distance_0_5km")
    assert result.is_compliant is False
    assert result.metrics["boundaryMode"] == "lte"

    assert result.over_distance_meters >= 0.0
    assert 0.0 <= result.azimuth_degrees < 360.0
    assert 0.0 <= result.max_horizontal_angle_degrees < 360.0
    assert 0.0 <= result.min_horizontal_angle_degrees < 360.0
    assert isinstance(result.relative_height_meters, float)
    assert isinstance(result.is_in_radius, bool)
    assert isinstance(result.is_in_zone, bool)
    assert isinstance(result.details, str)
    assert len(result.details) > 0


def test_adsb_0_5km_applies_to_high_frequency_furnace_with_lt_boundary() -> None:
    payload = AdsbRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="high_frequency_furnace_100kw_below",
                local_geometry=_point_geometry(500.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "adsb_minimum_distance_0_5km")
    assert result.is_compliant is True
    assert result.metrics["boundaryMode"] == "lt"


def test_adsb_0_7km_applies_to_110kv_power_line() -> None:
    payload = AdsbRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="power_line_high_voltage_110kv",
                local_geometry=_point_geometry(650.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "adsb_minimum_distance_0_7km")
    assert result.is_compliant is False


def test_adsb_0_8km_applies_to_220kv_substation() -> None:
    payload = AdsbRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="high_voltage_substation_220kv_or_330kv",
                local_geometry=_point_geometry(750.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "adsb_minimum_distance_0_8km")
    assert result.is_compliant is False


def test_adsb_1km_applies_to_500kv_power_line() -> None:
    payload = AdsbRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="power_line_high_voltage_500kv_and_above",
                local_geometry=_point_geometry(950.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "adsb_minimum_distance_1km")
    assert result.is_compliant is False


def test_adsb_1_2km_applies_to_high_frequency_welding_machine() -> None:
    payload = AdsbRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="high_frequency_welding_machine",
                local_geometry=_point_geometry(1100.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "adsb_minimum_distance_1_2km")
    assert result.is_compliant is False


def test_adsb_profile_binds_only_present_category_bands_in_deterministic_order() -> None:
    payload = AdsbRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                obstacle_id=1,
                category="road",
                local_geometry=_point_geometry(650.0, 0.0),
            ),
            _make_obstacle(
                obstacle_id=2,
                category="power_line_high_voltage_500kv_and_above",
                local_geometry=_point_geometry(950.0, 0.0),
            ),
            _make_obstacle(
                obstacle_id=3,
                category="high_frequency_welding_machine",
                local_geometry=_point_geometry(1100.0, 0.0),
            ),
        ],
        station_point=(0.0, 0.0),
    )

    assert [zone.rule_code for zone in payload.protection_zones] == [
        "adsb_minimum_distance_0_7km",
        "adsb_minimum_distance_1km",
        "adsb_minimum_distance_1_2km",
    ]
    assert {result.rule_code for result in payload.rule_results} == {
        "adsb_minimum_distance_0_7km",
        "adsb_minimum_distance_1km",
        "adsb_minimum_distance_1_2km",
    }


def test_adsb_profile_skips_unsupported_categories() -> None:
    payload = AdsbRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(category="building_general", local_geometry=_point_geometry(100.0, 0.0))],
        station_point=(0.0, 0.0),
    )

    assert payload.rule_results == []
    assert payload.protection_zones == []


def test_adsb_metrics_include_required_fields() -> None:
    payload = AdsbRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="road",
                local_geometry=_point_geometry(650.0, 0.0),
                top_elevation=12.5,
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "adsb_minimum_distance_0_7km")
    assert result.metrics == {
        "enteredProtectionZone": True,
        "actualDistanceMeters": 650.0,
        "minimumDistanceMeters": 700.0,
        "topElevationMeters": 12.5,
        "boundaryMode": "lt",
    }


def test_adsb_shared_rule_band_uses_category_specific_standards_rule_code() -> None:
    payload = AdsbRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                obstacle_id=1,
                category="road",
                local_geometry=_point_geometry(650.0, 0.0),
            ),
            _make_obstacle(
                obstacle_id=2,
                category="power_line_high_voltage_110kv",
                local_geometry=_point_geometry(650.0, 0.0),
            ),
            _make_obstacle(
                obstacle_id=3,
                category="high_voltage_substation_500kv_and_above",
                local_geometry=_point_geometry(1100.0, 0.0),
            ),
            _make_obstacle(
                obstacle_id=4,
                category="high_frequency_welding_machine",
                local_geometry=_point_geometry(1100.0, 0.0),
            ),
        ],
        station_point=(0.0, 0.0),
    )

    standards_rule_codes = {
        result.global_obstacle_category: result.standards_rule_code
        for result in payload.rule_results
    }
    assert standards_rule_codes == {
        "road": "adsb_minimum_distance_0_7km_road",
        "power_line_high_voltage_110kv": "adsb_minimum_distance_0_7km_110kv_power_line",
        "high_voltage_substation_500kv_and_above": "adsb_minimum_distance_1_2km_500kv_substation",
        "high_frequency_welding_machine": "adsb_minimum_distance_1_2km_high_frequency_welding_machine",
    }


def test_adsb_circle_rule_has_is_filter_limit() -> None:
    from app.analysis.rules.adsb.minimum_distance_0_5km import AdsbMinimumDistance0_5kmRule
    bound = AdsbMinimumDistance0_5kmRule().bind(
        station=_make_station(),
        station_point=(0.0, 0.0),
    )
    result = bound.analyze(_make_obstacle(category="railway_non_electrified", local_geometry=_point_geometry(600.0, 0.0)))
    assert result.is_filter_limit is True
