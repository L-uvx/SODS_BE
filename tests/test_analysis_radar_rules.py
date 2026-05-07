from unittest.mock import MagicMock

from app.analysis.rules.radar.minimum_distance import RadarMinimumDistanceRule
from app.analysis.rules.radar.profile import RadarRuleProfile
from app.analysis.rules.radar.rotating_reflector_16km import RadarRotatingReflector16kmRule


def _make_station(**overrides):
    station = MagicMock()
    station.id = 1
    station.station_type = "RADAR"
    station.name = "TEST_RADAR"
    station.longitude = 120.0
    station.latitude = 30.0
    station.altitude = 10.0
    station.station_sub_type = "PSR"
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


def _line_geometry(start_x, start_y, end_x, end_y):
    return {
        "type": "LineString",
        "coordinates": [[start_x, start_y], [end_x, end_y]],
    }


def _square_polygon_geometry(center_x, center_y, half_size):
    return {
        "type": "Polygon",
        "coordinates": [[
            [center_x - half_size, center_y - half_size],
            [center_x + half_size, center_y - half_size],
            [center_x + half_size, center_y + half_size],
            [center_x - half_size, center_y + half_size],
            [center_x - half_size, center_y - half_size],
        ]],
    }


def test_radar_profile_returns_b_and_c_results_for_supported_categories() -> None:
    profile = RadarRuleProfile()
    station = _make_station()

    payload = profile.analyze(
        station=station,
        obstacles=[
            _make_obstacle(category="building_general", local_geometry=_point_geometry(300.0, 0.0)),
            _make_obstacle(
                obstacle_id=2,
                category="large_rotating_reflector",
                local_geometry=_point_geometry(15000.0, 0.0),
            ),
        ],
        station_point=(0.0, 0.0),
    )

    assert any(result.rule_code == "radar_minimum_distance_460m" for result in payload.rule_results)
    assert any(result.rule_code == "radar_rotating_reflector_16km" for result in payload.rule_results)


def test_radar_rules_resolve_zone_name_from_display_mapping(monkeypatch) -> None:
    from app.analysis import protection_zone_style

    monkeypatch.setitem(
        protection_zone_style.PROTECTION_ZONE_DISPLAY_NAME_MAPPING,
        "radar_minimum_distance_zone_460m",
        "Radar 映射最小间距",
    )
    monkeypatch.setitem(
        protection_zone_style.PROTECTION_ZONE_DISPLAY_NAME_MAPPING,
        "radar_rotating_reflector_zone_16km",
        "Radar 映射旋转反射体区",
    )

    minimum_distance_zone = RadarMinimumDistanceRule(
        minimum_distance_meters=460.0,
    ).bind(
        station=_make_station(),
        station_point=(0.0, 0.0),
    ).protection_zone
    rotating_reflector_zone = RadarRotatingReflector16kmRule().bind(
        station=_make_station(),
        station_point=(0.0, 0.0),
    ).protection_zone

    assert minimum_distance_zone.zone_name == "Radar 映射最小间距"
    assert rotating_reflector_zone.zone_name == "Radar 映射旋转反射体区"


def test_radar_b_uses_460m_for_building_general() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(category="building_general", local_geometry=_point_geometry(300.0, 0.0), top_elevation=25.0)
        ],
        station_point=(0.0, 0.0),
    )

    result = payload.rule_results[0]
    assert result.rule_code == "radar_minimum_distance_460m"
    assert result.zone_code == "radar_minimum_distance_zone_460m"
    assert result.standards_rule_code == "radar_minimum_distance_460m_standard"
    assert result.metrics["minimumDistanceMeters"] == 460.0
    assert result.metrics["actualDistanceMeters"] == 300.0
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["topElevationMeters"] == 25.0
    assert result.is_compliant is False


def test_radar_b_uses_700m_for_110kv_substation() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="high_voltage_substation_110kv",
                local_geometry=_point_geometry(650.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = payload.rule_results[0]
    assert result.rule_code == "radar_minimum_distance_700m"
    assert result.metrics["minimumDistanceMeters"] == 700.0
    assert result.is_compliant is False


def test_radar_b_uses_800m_for_fm_broadcast() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(category="fm_broadcast", local_geometry=_point_geometry(850.0, 0.0))],
        station_point=(0.0, 0.0),
    )

    result = payload.rule_results[0]
    assert result.rule_code == "radar_minimum_distance_800m"
    assert result.metrics["minimumDistanceMeters"] == 800.0
    assert result.is_compliant is True


def test_radar_b_uses_930m_for_weather_radar_station() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(category="weather_radar_station", local_geometry=_point_geometry(920.0, 0.0))
        ],
        station_point=(0.0, 0.0),
    )

    result = payload.rule_results[0]
    assert result.rule_code == "radar_minimum_distance_930m"
    assert result.metrics["minimumDistanceMeters"] == 930.0
    assert result.is_compliant is False


def test_radar_b_uses_1000m_for_500kv_power_line() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="power_line_high_voltage_500kv_and_above",
                local_geometry=_point_geometry(1200.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = payload.rule_results[0]
    assert result.rule_code == "radar_minimum_distance_1000m"
    assert result.metrics["minimumDistanceMeters"] == 1000.0
    assert result.is_compliant is True


def test_radar_b_uses_1200m_for_500kv_substation() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="high_voltage_substation_500kv_and_above",
                local_geometry=_point_geometry(1100.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = payload.rule_results[0]
    assert result.rule_code == "radar_minimum_distance_1200m"
    assert result.metrics["minimumDistanceMeters"] == 1200.0
    assert result.is_compliant is False


def test_radar_b_uses_1610m_for_building_hangar() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(category="building_hangar", local_geometry=_point_geometry(1610.0, 0.0))
        ],
        station_point=(0.0, 0.0),
    )

    result = payload.rule_results[0]
    assert result.rule_code == "radar_minimum_distance_1610m"
    assert result.metrics["minimumDistanceMeters"] == 1610.0
    assert result.metrics["enteredProtectionZone"] is True
    assert result.is_compliant is False


def test_radar_b_treats_line_touching_boundary_as_entered() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="building_general",
                local_geometry=_line_geometry(460.0, -10.0, 460.0, 10.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = payload.rule_results[0]
    assert result.rule_code == "radar_minimum_distance_460m"
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["actualDistanceMeters"] == 460.0
    assert result.is_compliant is False


def test_radar_b_treats_polygon_touching_boundary_as_entered() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="building_general",
                local_geometry=_square_polygon_geometry(470.0, 0.0, 10.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = payload.rule_results[0]
    assert result.rule_code == "radar_minimum_distance_460m"
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["actualDistanceMeters"] == 460.0
    assert result.is_compliant is False


def test_radar_b_does_not_apply_to_high_frequency_furnace_above_100kw() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="high_frequency_furnace_above_100kw",
                local_geometry=_point_geometry(100.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    assert payload.rule_results == []
    assert payload.protection_zones == []


def test_radar_b_does_not_apply_to_high_voltage_substation_other() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="high_voltage_substation_other",
                local_geometry=_point_geometry(100.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    assert payload.rule_results == []
    assert payload.protection_zones == []


def test_radar_b_does_not_apply_to_industrial_electric_welding_above_10kw() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="industrial_electric_welding_above_10kw",
                local_geometry=_point_geometry(100.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    assert payload.rule_results == []
    assert payload.protection_zones == []


def test_radar_b_does_not_apply_to_uhf_therapy_equipment_above_1kw() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="uhf_therapy_equipment_above_1kw",
                local_geometry=_point_geometry(100.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    assert payload.rule_results == []
    assert payload.protection_zones == []


def test_radar_b_does_not_apply_to_agricultural_power_equipment_above_1kw() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="agricultural_power_equipment_above_1kw",
                local_geometry=_point_geometry(100.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    assert payload.rule_results == []
    assert payload.protection_zones == []


def test_radar_profile_reuses_same_zone_for_same_radius() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(obstacle_id=1, category="building_general", local_geometry=_point_geometry(300.0, 0.0)),
            _make_obstacle(obstacle_id=2, category="tower", local_geometry=_point_geometry(350.0, 0.0)),
        ],
        station_point=(0.0, 0.0),
    )

    assert len(payload.protection_zones) == 1
    assert payload.protection_zones[0].zone_code == "radar_minimum_distance_zone_460m"


def test_radar_protection_zone_vertical_definition_uses_station_base_reference() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="building_general",
                local_geometry=_point_geometry(300.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    assert payload.protection_zones[0].vertical_definition == {
        "mode": "flat",
        "baseReference": "station",
        "baseHeightMeters": 0.0,
    }


def test_radar_c_only_applies_to_large_rotating_reflector() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="large_rotating_reflector",
                local_geometry=_point_geometry(1000.0, 0.0),
            ),
            _make_obstacle(
                obstacle_id=2,
                category="building_general",
                local_geometry=_point_geometry(1000.0, 0.0),
            ),
        ],
        station_point=(0.0, 0.0),
    )

    reflector_results = [
        result for result in payload.rule_results if result.rule_code == "radar_rotating_reflector_16km"
    ]
    assert len(reflector_results) == 1
    assert reflector_results[0].global_obstacle_category == "large_rotating_reflector"


def test_radar_c_fails_when_rotating_reflector_is_inside_16km() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="large_rotating_reflector",
                local_geometry=_point_geometry(15999.0, 0.0),
                top_elevation=88.0,
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = payload.rule_results[0]
    assert result.rule_code == "radar_rotating_reflector_16km"
    assert result.zone_code == "radar_rotating_reflector_zone_16km"
    assert result.standards_rule_code == "radar_rotating_reflector_16km_standard"
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["actualDistanceMeters"] == 15999.0
    assert result.metrics["topElevationMeters"] == 88.0
    assert result.is_compliant is False


def test_radar_c_passes_when_rotating_reflector_is_outside_16km() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                category="large_rotating_reflector",
                local_geometry=_point_geometry(16001.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = payload.rule_results[0]
    assert result.rule_code == "radar_rotating_reflector_16km"
    assert result.metrics["enteredProtectionZone"] is False
    assert result.is_compliant is True


def test_radar_c_treats_boundary_as_entered() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(station_sub_type="SSR"),
        obstacles=[
            _make_obstacle(
                category="large_rotating_reflector",
                local_geometry=_point_geometry(16000.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = payload.rule_results[0]
    assert result.rule_code == "radar_rotating_reflector_16km"
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["actualDistanceMeters"] == 16000.0
    assert result.is_compliant is False


def test_radar_rules_do_not_branch_by_station_sub_type() -> None:
    psr_payload = RadarRuleProfile().analyze(
        station=_make_station(station_sub_type="PSR"),
        obstacles=[
            _make_obstacle(
                category="large_rotating_reflector",
                local_geometry=_point_geometry(15999.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )
    ssr_payload = RadarRuleProfile().analyze(
        station=_make_station(station_sub_type="SSR"),
        obstacles=[
            _make_obstacle(
                category="large_rotating_reflector",
                local_geometry=_point_geometry(15999.0, 0.0),
            )
        ],
        station_point=(0.0, 0.0),
    )

    assert psr_payload.rule_results[0].rule_code == ssr_payload.rule_results[0].rule_code
    assert psr_payload.rule_results[0].is_compliant == ssr_payload.rule_results[0].is_compliant
    assert psr_payload.rule_results[0].metrics == ssr_payload.rule_results[0].metrics


def test_radar_c_does_not_return_result_for_non_whitelist_category() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(category="tower", local_geometry=_point_geometry(1000.0, 0.0))],
        station_point=(0.0, 0.0),
    )

    assert not any(result.rule_code == "radar_rotating_reflector_16km" for result in payload.rule_results)
