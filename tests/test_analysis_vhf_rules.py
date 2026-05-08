from unittest.mock import MagicMock

from app.analysis.protection_zone_style import (
    resolve_protection_zone_name,
    resolve_protection_zone_style,
)
from app.analysis.standards import build_rule_standards
from app.analysis.rules.vhf.profile import VhfRuleProfile


def _make_station(**overrides):
    station = MagicMock()
    station.id = 1
    station.station_type = "VHF"
    station.name = "TEST_VHF"
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


def test_vhf_0_2km_applies_to_110kv_line() -> None:
    payload = VhfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="power_line_high_voltage_110kv",
                local_geometry=_point_geometry(150.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "vhf_minimum_distance_0_2km")
    assert result.is_compliant is False


def test_vhf_0_25km_applies_to_220kv_and_330kv_lines() -> None:
    payload = VhfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                obstacle_id=1,
                category="power_line_high_voltage_220kv",
                local_geometry=_point_geometry(200.0, 0.0),
            ),
            _make_obstacle(
                obstacle_id=2,
                category="power_line_high_voltage_330kv",
                local_geometry=_point_geometry(240.0, 0.0),
            ),
        ],
        station_point=(0.0, 0.0),
    )

    results = [
        result for result in payload.rule_results if result.rule_code == "vhf_minimum_distance_0_25km"
    ]
    assert len(results) == 2
    assert all(result.is_compliant is False for result in results)


def test_vhf_0_3km_applies_to_road_and_500kv_line() -> None:
    payload = VhfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                obstacle_id=1,
                category="road",
                local_geometry=_point_geometry(280.0, 0.0),
            ),
            _make_obstacle(
                obstacle_id=2,
                category="power_line_high_voltage_500kv_and_above",
                local_geometry=_point_geometry(290.0, 0.0),
            ),
        ],
        station_point=(0.0, 0.0),
    )

    results = [
        result for result in payload.rule_results if result.rule_code == "vhf_minimum_distance_0_3km"
    ]
    assert len(results) == 2
    assert all(result.is_compliant is False for result in results)


def test_vhf_0_8km_applies_to_rf_equipment() -> None:
    payload = VhfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="industrial_scientific_medical_rf_equipment",
                local_geometry=_point_geometry(700.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "vhf_minimum_distance_0_8km")
    assert result.is_compliant is False


def test_vhf_1km_applies_to_low_power_fm_broadcast() -> None:
    payload = VhfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="fm_broadcast_1kw_below",
                local_geometry=_point_geometry(900.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "vhf_minimum_distance_1km")
    assert result.is_compliant is False


def test_vhf_6km_applies_to_high_power_fm_broadcast() -> None:
    payload = VhfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="fm_broadcast_above_1kw",
                local_geometry=_point_geometry(5900.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "vhf_minimum_distance_6km")
    assert result.is_compliant is False


def test_vhf_boundary_distance_is_compliant() -> None:
    payload = VhfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="railway_electrified",
                local_geometry=_point_geometry(300.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "vhf_minimum_distance_0_3km")
    assert result.is_compliant is True


def test_vhf_profile_binds_only_present_category_bands() -> None:
    payload = VhfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                obstacle_id=1,
                category="power_line_high_voltage_110kv",
                local_geometry=_point_geometry(150.0, 0.0),
            ),
            _make_obstacle(
                obstacle_id=2,
                category="fm_broadcast_1kw_below",
                local_geometry=_point_geometry(900.0, 0.0),
            ),
        ],
        station_point=(0.0, 0.0),
    )

    assert {zone.rule_code for zone in payload.protection_zones} == {
        "vhf_minimum_distance_0_2km",
        "vhf_minimum_distance_1km",
    }
    assert {result.rule_code for result in payload.rule_results} == {
        "vhf_minimum_distance_0_2km",
        "vhf_minimum_distance_1km",
    }


def test_vhf_profile_skips_unsupported_categories() -> None:
    payload = VhfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(category="building_general", local_geometry=_point_geometry(100.0, 0.0))],
        station_point=(0.0, 0.0),
    )

    assert payload.rule_results == []
    assert payload.protection_zones == []


def test_vhf_standards_name_and_style_are_wired_for_representative_zones() -> None:
    standards_1 = build_rule_standards(
        station_type="VHF",
        rule_name="vhf_minimum_distance_0_2km_110kv_power_line",
        region_code="default",
    )
    standards_2 = build_rule_standards(
        station_type="VHF",
        rule_name="vhf_minimum_distance_6km_fm_broadcast_above_1kw",
        region_code="default",
    )

    assert standards_1.gb is not None
    assert standards_1.gb.code == "AP_VHF_0.2km平面防护间距要求_110kV高压架空输电线路"
    assert standards_1.mh is None
    assert standards_2.gb is not None
    assert standards_2.gb.code == "AP_VHF_6km平面防护间距要求_1kW以上调频广播"
    assert standards_2.mh is None

    assert resolve_protection_zone_name(zone_code="vhf_minimum_distance_0_2km") == "VHF 0.2km最小间距"
    assert resolve_protection_zone_name(zone_code="vhf_minimum_distance_6km") == "VHF 6km最小间距"

    assert resolve_protection_zone_style(
        zone_code="vhf_minimum_distance_0_2km",
        region_code="default",
    )["colorKey"] == "sky_blue"
    assert resolve_protection_zone_style(
        zone_code="vhf_minimum_distance_6km",
        region_code="default",
    )["colorKey"] == "lime_green"


def test_vhf_shared_rule_band_uses_category_specific_standards_rule_code() -> None:
    payload = VhfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                obstacle_id=1,
                category="railway_electrified",
                local_geometry=_point_geometry(280.0, 0.0),
            ),
            _make_obstacle(
                obstacle_id=2,
                category="road",
                local_geometry=_point_geometry(280.0, 0.0),
            ),
            _make_obstacle(
                obstacle_id=3,
                category="power_line_high_voltage_500kv_and_above",
                local_geometry=_point_geometry(280.0, 0.0),
            ),
        ],
        station_point=(0.0, 0.0),
    )

    standards_rule_codes = {
        result.global_obstacle_category: result.standards_rule_code
        for result in payload.rule_results
        if result.rule_code == "vhf_minimum_distance_0_3km"
    }
    assert standards_rule_codes == {
        "railway_electrified": "vhf_minimum_distance_0_3km_electrified_railway",
        "road": "vhf_minimum_distance_0_3km_trunk_road",
        "power_line_high_voltage_500kv_and_above": "vhf_minimum_distance_0_3km_500kv_power_line",
    }

    for standards_rule_code, expected_key in [
        ("vhf_minimum_distance_0_3km_electrified_railway", "AP_VHF_0.3km平面防护间距要求_电气化铁路"),
        ("vhf_minimum_distance_0_3km_trunk_road", "AP_VHF_0.3km平面防护间距要求_干线公路"),
        ("vhf_minimum_distance_0_3km_500kv_power_line", "AP_VHF_0.3km平面防护间距要求_500kV高压架空输电线路"),
    ]:
        standards = build_rule_standards(
            station_type="VHF",
            rule_name=standards_rule_code,
            region_code="default",
        )
        assert standards.gb is not None
        assert standards.gb.code == expected_key
        assert standards.mh is None
