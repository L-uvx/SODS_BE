from unittest.mock import MagicMock

import pytest

from app.analysis.local_coordinate import AirportLocalProjector
from app.analysis.rules.radar.minimum_distance import RadarMinimumDistanceRule
from app.analysis.rules.radar.profile import RadarRuleProfile
from app.analysis.rules.radar.rotating_reflector_16km import RadarRotatingReflector16kmRule
from app.analysis.rules.radar.site_protection import RadarSiteProtectionRule
from app.application.polygon_obstacle_import import PolygonObstacleImportService


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


def _find_rule_result(payload, rule_code):
    return next(result for result in payload.rule_results if result.rule_code == rule_code)


def _sector_band_polygon_geometry(inner_radius_m, outer_radius_m, half_angle_degrees):
    import math

    inner_y = inner_radius_m * math.tan(math.radians(half_angle_degrees))
    outer_y = outer_radius_m * math.tan(math.radians(half_angle_degrees))
    return {
        "type": "Polygon",
        "coordinates": [[
            [inner_radius_m, -inner_y],
            [outer_radius_m, -outer_y],
            [outer_radius_m, outer_y],
            [inner_radius_m, inner_y],
            [inner_radius_m, -inner_y],
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


def test_radar_a_skips_obstacle_outside_30km() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(antenna_hag=20.0),
        obstacles=[
            _make_obstacle(
                category="building_general",
                local_geometry=_point_geometry(30001.0, 0.0),
                top_elevation=500.0,
            )
        ],
        station_point=(0.0, 0.0),
    )

    assert not any(result.rule_code == "radar_site_protection" for result in payload.rule_results)


def test_radar_a_passes_when_vertical_angle_is_below_0_25_deg() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(antenna_hag=20.0),
        obstacles=[
            _make_obstacle(
                category="building_general",
                local_geometry=_sector_band_polygon_geometry(10000.0, 10100.0, 2.0),
                top_elevation=70.0,
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = next(result for result in payload.rule_results if result.rule_code == "radar_site_protection")
    assert result.is_compliant is True
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["actualDistanceMeters"] == pytest.approx(10000.0)
    assert result.metrics["verticalMaskAngleDegrees"] <= 0.25
    assert result.metrics["horizontalMaskAngleDegrees"] > 1.5
    assert result.metrics["verticalLimitAngleDegrees"] == 0.25
    assert result.metrics["horizontalLimitAngleDegrees"] == 1.5
    assert result.metrics["limitHeightMeters"] > result.metrics["baseHeightMeters"]


def test_radar_a_passes_when_horizontal_angle_is_not_greater_than_1_5_deg() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(antenna_hag=20.0),
        obstacles=[
            _make_obstacle(
                category="building_general",
                local_geometry=_sector_band_polygon_geometry(10000.0, 10100.0, 0.5),
                top_elevation=400.0,
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = next(result for result in payload.rule_results if result.rule_code == "radar_site_protection")
    assert result.is_compliant is True
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["verticalMaskAngleDegrees"] > 0.25
    assert result.metrics["horizontalMaskAngleDegrees"] <= 1.5
    assert result.metrics["verticalLimitAngleDegrees"] == 0.25
    assert result.metrics["horizontalLimitAngleDegrees"] == 1.5
    assert result.metrics["limitHeightMeters"] < result.metrics["topElevationMeters"]


def test_radar_a_fails_when_vertical_and_horizontal_angles_both_exceed_limits() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(antenna_hag=20.0),
        obstacles=[
            _make_obstacle(
                category="building_general",
                local_geometry=_sector_band_polygon_geometry(10000.0, 10100.0, 2.0),
                top_elevation=400.0,
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = next(result for result in payload.rule_results if result.rule_code == "radar_site_protection")
    assert result.is_compliant is False
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["verticalMaskAngleDegrees"] > 0.25
    assert result.metrics["horizontalMaskAngleDegrees"] > 1.5
    assert result.metrics["verticalLimitAngleDegrees"] == 0.25
    assert result.metrics["horizontalLimitAngleDegrees"] == 1.5
    assert result.metrics["limitHeightMeters"] < result.metrics["topElevationMeters"]
    assert result.metrics["baseHeightMeters"] == 30.0


def test_radar_a_station_point_zero_distance_does_not_crash() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(antenna_hag=20.0),
        obstacles=[
            _make_obstacle(
                category="building_general",
                local_geometry=_point_geometry(0.0, 0.0),
                top_elevation=400.0,
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = next(result for result in payload.rule_results if result.rule_code == "radar_site_protection")
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["actualDistanceMeters"] == 0.0
    assert result.metrics["verticalMaskAngleDegrees"] > result.metrics["verticalLimitAngleDegrees"]
    assert result.is_compliant is True


@pytest.mark.parametrize(
    ("geometry",),
    [
        (_point_geometry(10000.0, 0.0),),
        (_line_geometry(10000.0, 0.0, 10000.0, 0.0),),
    ],
)
def test_radar_a_uses_zero_horizontal_mask_angle_for_point_or_degenerate_geometry(
    geometry,
) -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(antenna_hag=20.0),
        obstacles=[
            _make_obstacle(
                category="building_general",
                local_geometry=geometry,
                top_elevation=400.0,
            )
        ],
        station_point=(0.0, 0.0),
    )

    result = next(result for result in payload.rule_results if result.rule_code == "radar_site_protection")
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["horizontalMaskAngleDegrees"] == pytest.approx(0.0)


def test_radar_a_protection_zone_uses_analytic_surface_vertical_definition() -> None:
    protection_zone = RadarSiteProtectionRule().bind(
        station=_make_station(antenna_hag=20.0),
        station_point=(0.0, 0.0),
        radius_meters=30000.0,
        vertical_limit_angle_degrees=0.25,
        horizontal_limit_angle_degrees=1.5,
    ).protection_zone

    vertical_definition = protection_zone.vertical_definition
    assert vertical_definition["mode"] != "flat"
    assert vertical_definition["mode"] == "analytic_surface"
    assert vertical_definition["surface"]["type"] == "radial_cone_surface"
    assert (
        vertical_definition["surface"]["heightModel"]["type"]
        == "radar_site_protection_mask_angle"
    )
    assert (
        vertical_definition["surface"]["heightModel"]["maskAngleDegrees"]
        == pytest.approx(0.25)
    )
    assert (
        vertical_definition["surface"]["heightModel"]["distanceKilometersCorrectionDivisor"]
        == pytest.approx(16970.0)
    )


def test_radar_a_public_vertical_payload_exposes_mask_angle_correction_model() -> None:
    station = _make_station(antenna_hag=20.0)
    protection_zone = RadarSiteProtectionRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        radius_meters=30000.0,
        vertical_limit_angle_degrees=0.25,
        horizontal_limit_angle_degrees=1.5,
    ).protection_zone
    service = PolygonObstacleImportService(MagicMock())

    payload = service._build_public_protection_zone_vertical_payload(
        projector=AirportLocalProjector(
            reference_longitude=station.longitude,
            reference_latitude=station.latitude,
        ),
        vertical_definition=protection_zone.vertical_definition,
        station_altitude_meters=float(station.altitude),
        station_wgs84=(float(station.longitude), float(station.latitude)),
    )

    assert payload["mode"] == "analytic_surface"
    assert payload["surface"]["type"] == "radial_cone_surface"
    assert payload["surface"]["heightModel"]["type"] == "radar_site_protection_mask_angle"
    assert payload["surface"]["heightModel"]["maskAngleDegrees"] == pytest.approx(0.25)
    assert (
        payload["surface"]["heightModel"]["distanceKilometersCorrectionDivisor"]
        == pytest.approx(16970.0)
    )


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

    result = _find_rule_result(payload, "radar_minimum_distance_460m")
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

    result = _find_rule_result(payload, "radar_minimum_distance_700m")
    assert result.rule_code == "radar_minimum_distance_700m"
    assert result.metrics["minimumDistanceMeters"] == 700.0
    assert result.is_compliant is False


def test_radar_b_uses_800m_for_fm_broadcast() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(category="fm_broadcast", local_geometry=_point_geometry(850.0, 0.0))],
        station_point=(0.0, 0.0),
    )

    result = _find_rule_result(payload, "radar_minimum_distance_800m")
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

    result = _find_rule_result(payload, "radar_minimum_distance_930m")
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

    result = _find_rule_result(payload, "radar_minimum_distance_1000m")
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

    result = _find_rule_result(payload, "radar_minimum_distance_1200m")
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

    result = _find_rule_result(payload, "radar_minimum_distance_1610m")
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

    result = _find_rule_result(payload, "radar_minimum_distance_460m")
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

    result = _find_rule_result(payload, "radar_minimum_distance_460m")
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

    assert not any(result.rule_code.startswith("radar_minimum_distance_") for result in payload.rule_results)
    assert not any(result.rule_code == "radar_rotating_reflector_16km" for result in payload.rule_results)


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

    assert not any(result.rule_code.startswith("radar_minimum_distance_") for result in payload.rule_results)
    assert not any(result.rule_code == "radar_rotating_reflector_16km" for result in payload.rule_results)


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

    assert not any(result.rule_code.startswith("radar_minimum_distance_") for result in payload.rule_results)
    assert not any(result.rule_code == "radar_rotating_reflector_16km" for result in payload.rule_results)


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

    assert not any(result.rule_code.startswith("radar_minimum_distance_") for result in payload.rule_results)
    assert not any(result.rule_code == "radar_rotating_reflector_16km" for result in payload.rule_results)


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

    assert not any(result.rule_code.startswith("radar_minimum_distance_") for result in payload.rule_results)
    assert not any(result.rule_code == "radar_rotating_reflector_16km" for result in payload.rule_results)


def test_radar_profile_reuses_same_zone_for_same_radius() -> None:
    payload = RadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(obstacle_id=1, category="building_general", local_geometry=_point_geometry(300.0, 0.0)),
            _make_obstacle(obstacle_id=2, category="tower", local_geometry=_point_geometry(350.0, 0.0)),
        ],
        station_point=(0.0, 0.0),
    )

    minimum_distance_zones = [
        zone for zone in payload.protection_zones if zone.zone_code == "radar_minimum_distance_zone_460m"
    ]
    assert len(minimum_distance_zones) == 1


def test_radar_protection_zone_vertical_definition_matches_rule_semantics() -> None:
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

    radar_a_zone = next(
        zone for zone in payload.protection_zones if zone.zone_code == "radar_site_protection"
    )
    radar_b_zone = next(
        zone
        for zone in payload.protection_zones
        if zone.zone_code == "radar_minimum_distance_zone_460m"
    )

    assert radar_a_zone.vertical_definition["baseReference"] == "station"
    assert radar_a_zone.vertical_definition["mode"] == "analytic_surface"
    assert (
        radar_a_zone.vertical_definition["surface"]["heightModel"]["type"]
        == "radar_site_protection_mask_angle"
    )
    assert (
        radar_a_zone.vertical_definition["surface"]["heightModel"]["distanceKilometersCorrectionDivisor"]
        == pytest.approx(16970.0)
    )
    assert radar_b_zone.vertical_definition == {
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

    result = _find_rule_result(payload, "radar_rotating_reflector_16km")
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

    result = _find_rule_result(payload, "radar_rotating_reflector_16km")
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

    result = _find_rule_result(payload, "radar_rotating_reflector_16km")
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
