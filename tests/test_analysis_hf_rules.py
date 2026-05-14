from unittest.mock import MagicMock

from app.analysis.protection_zone_style import (
    resolve_protection_zone_name,
    resolve_protection_zone_style,
)
from app.analysis.standards import build_rule_standards
from app.analysis.rules.hf.profile import HfRuleProfile


def _make_station(**overrides):
    station = MagicMock()
    station.id = 1
    station.station_type = "HF"
    station.name = "TEST_HF"
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


def test_hf_0_8km_applies_to_electrified_railway() -> None:
    payload = HfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="railway_electrified",
                local_geometry=_point_geometry(700.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "hf_minimum_distance_0_8km")
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


def test_hf_5km_applies_to_rf_equipment() -> None:
    payload = HfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="industrial_scientific_medical_rf_equipment",
                local_geometry=_point_geometry(4500.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "hf_minimum_distance_5km")
    assert result.is_compliant is False


def test_hf_20km_applies_to_above_200kw_medium_long_wave() -> None:
    payload = HfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="radio_emitter_medium_long_wave_above_200kw",
                local_geometry=_point_geometry(19000.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "hf_minimum_distance_20km")
    assert result.is_compliant is False


def test_hf_rf_equipment_uses_exact_5km_threshold() -> None:
    payload = HfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="industrial_scientific_medical_rf_equipment",
                local_geometry=_point_geometry(4900.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "hf_minimum_distance_5km")
    assert result.is_compliant is False


def test_hf_boundary_distance_is_compliant() -> None:
    payload = HfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="power_line_high_voltage_110kv",
                local_geometry=_point_geometry(1000.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "hf_minimum_distance_1km")
    assert result.is_compliant is True


def test_hf_profile_binds_only_present_category_bands_in_deterministic_order() -> None:
    payload = HfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                obstacle_id=1,
                category="industrial_scientific_medical_rf_equipment",
                local_geometry=_point_geometry(4500.0, 0.0),
            ),
            _make_obstacle(
                obstacle_id=2,
                category="power_line_high_voltage_110kv",
                local_geometry=_point_geometry(900.0, 0.0),
            ),
            _make_obstacle(
                obstacle_id=3,
                category="radio_emitter_medium_long_wave_above_200kw",
                local_geometry=_point_geometry(19000.0, 0.0),
            ),
        ],
        station_point=(0.0, 0.0),
    )

    assert [zone.rule_code for zone in payload.protection_zones] == [
        "hf_minimum_distance_1km",
        "hf_minimum_distance_5km",
        "hf_minimum_distance_20km",
    ]
    assert {result.rule_code for result in payload.rule_results} == {
        "hf_minimum_distance_1km",
        "hf_minimum_distance_5km",
        "hf_minimum_distance_20km",
    }


def test_hf_profile_skips_unsupported_categories() -> None:
    payload = HfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(category="building_general", local_geometry=_point_geometry(100.0, 0.0))],
        station_point=(0.0, 0.0),
    )

    assert payload.rule_results == []
    assert payload.protection_zones == []


def test_hf_profile_explicitly_skips_short_wave_other_category() -> None:
    payload = HfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="radio_emitter_short_wave_other",
                local_geometry=_point_geometry(1000.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    assert payload.rule_results == []
    assert payload.protection_zones == []


def test_hf_standards_name_and_style_are_wired_for_representative_zones() -> None:
    standards_1 = build_rule_standards(
        station_type="HF",
        rule_name="hf_minimum_distance_0_8km_electrified_railway",
        region_code="default",
    )
    standards_2 = build_rule_standards(
        station_type="HF",
        rule_name="hf_minimum_distance_20km_medium_long_wave_above_200kw",
        region_code="default",
    )

    assert standards_1.gb
    assert standards_1.gb[0].code == "AP_HF_0.8km平面防护间距要求_电气化铁路"
    assert standards_1.mh == []
    assert standards_2.gb
    assert standards_2.gb[0].code == "AP_HF_20km平面防护间距要求_200kW以上中波和长波发射台"
    assert standards_2.mh == []

    assert resolve_protection_zone_name(zone_code="hf_minimum_distance_0_8km") == "HF 0.8km最小间距"
    assert resolve_protection_zone_name(zone_code="hf_minimum_distance_20km") == "HF 20km最小间距"

    assert resolve_protection_zone_style(
        zone_code="hf_minimum_distance_0_8km",
        region_code="default",
    )["colorKey"] == "sky_blue"
    assert resolve_protection_zone_style(
        zone_code="hf_minimum_distance_20km",
        region_code="default",
    )["colorKey"] == "pink_rose"


def test_hf_shared_rule_band_uses_category_specific_standards_rule_code() -> None:
    payload = HfRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                obstacle_id=1,
                category="power_line_high_voltage_110kv",
                local_geometry=_point_geometry(900.0, 0.0),
            ),
            _make_obstacle(
                obstacle_id=2,
                category="road",
                local_geometry=_point_geometry(900.0, 0.0),
            ),
            _make_obstacle(
                obstacle_id=3,
                category="industrial_scientific_medical_rf_equipment",
                local_geometry=_point_geometry(4900.0, 0.0),
            ),
            _make_obstacle(
                obstacle_id=4,
                category="radio_emitter_short_wave_outside_quarter_power_angle_25_to_120kw",
                local_geometry=_point_geometry(4900.0, 0.0),
            ),
        ],
        station_point=(0.0, 0.0),
    )

    standards_rule_codes = {
        result.global_obstacle_category: result.standards_rule_code
        for result in payload.rule_results
        if result.rule_code in {"hf_minimum_distance_1km", "hf_minimum_distance_5km"}
    }
    assert standards_rule_codes == {
        "power_line_high_voltage_110kv": "hf_minimum_distance_1km_110kv_power_line",
        "road": "hf_minimum_distance_1km_road",
        "industrial_scientific_medical_rf_equipment": "hf_minimum_distance_5km_rf_equipment",
        "radio_emitter_short_wave_outside_quarter_power_angle_25_to_120kw": "hf_minimum_distance_5km_short_wave_outside_quarter_25_to_120kw",
    }

    for standards_rule_code, expected_key in [
        ("hf_minimum_distance_1km_110kv_power_line", "AP_HF_1km平面防护间距要求_110kV高压架空输电线路"),
        ("hf_minimum_distance_1km_road", "AP_HF_1km平面防护间距要求_道路/公路"),
        ("hf_minimum_distance_5km_rf_equipment", "AP_HF_5km平面防护间距要求_工、科、医射频设备"),
        ("hf_minimum_distance_5km_short_wave_outside_quarter_25_to_120kw", "AP_HF_5km平面防护间距要求_25到120kW短波发射台（通信方向1/4功率角外）"),
    ]:
        standards = build_rule_standards(
            station_type="HF",
            rule_name=standards_rule_code,
            region_code="default",
        )
        assert standards.gb
        assert standards.gb[0].code == expected_key
        assert standards.mh == []


def test_hf_circle_rule_has_is_filter_limit() -> None:
    from app.analysis.rules.hf.minimum_distance_1km import HfMinimumDistance1kmRule
    bound = HfMinimumDistance1kmRule().bind(
        station=_make_station(),
        station_point=(0.0, 0.0),
    )
    result = bound.analyze(_make_obstacle(category="road", local_geometry=_point_geometry(1500.0, 0.0)))
    assert result.is_filter_limit is True
