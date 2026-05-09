import math
from unittest.mock import MagicMock

import pytest
from shapely.geometry import Point

from app.analysis.protection_zone_style import resolve_protection_zone_style
from app.analysis.standards import build_rule_standards


def _build_profile():
    from app.analysis.rules.mb.profile import MbRuleProfile

    return MbRuleProfile()


def _build_station(**overrides):
    station = MagicMock()
    station.id = 1
    station.station_type = "MB"
    station.name = "MB-1"
    station.longitude = 120.0
    station.latitude = 30.0
    station.altitude = 100.0
    station.runway_no = "18"
    for key, value in overrides.items():
        setattr(station, key, value)
    return station


def _build_runway(**overrides):
    runway = {
        "runNumber": "18",
        "directionDegrees": 180.0,
    }
    runway.update(overrides)
    return runway


def _build_point_obstacle(*, obstacle_id: int, x: float, y: float, top: float):
    point = Point(x, y)
    return {
        "obstacleId": obstacle_id,
        "name": f"obs-{obstacle_id}",
        "rawObstacleType": "building",
        "globalObstacleCategory": "building_general",
        "topElevation": top,
        "localGeometry": point,
        "geometry": point,
    }


def test_mb_profile_returns_empty_without_matching_runway() -> None:
    profile = _build_profile()
    station = _build_station()

    payload = profile.analyze(
        station=station,
        obstacles=[],
        station_point=(0.0, 0.0),
        runways=[],
    )

    assert payload.rule_results == []
    assert payload.protection_zones == []


def test_mb_profile_builds_four_regions_when_runway_resolved() -> None:
    profile = _build_profile()
    station = _build_station()

    payload = profile.analyze(
        station=station,
        obstacles=[],
        station_point=(0.0, 0.0),
        runways=[_build_runway()],
    )

    assert [zone.region_code for zone in payload.protection_zones] == [
        "I",
        "II",
        "III",
        "IV",
    ]


def test_mb_profile_resolves_zone_name_from_display_mapping(monkeypatch) -> None:
    from app.analysis import protection_zone_style

    monkeypatch.setitem(
        protection_zone_style.PROTECTION_ZONE_DISPLAY_NAME_MAPPING,
        "mb_site_protection",
        "MB 映射场地保护区",
    )

    payload = _build_profile().analyze(
        station=_build_station(),
        obstacles=[],
        station_point=(0.0, 0.0),
        runways=[_build_runway()],
    )

    assert payload.protection_zones
    assert all(zone.zone_name == "MB 映射场地保护区" for zone in payload.protection_zones)


def test_mb_region_i_uses_20_degree_limit_with_expected_rule_code() -> None:
    profile = _build_profile()
    station = _build_station()
    obstacle = _build_point_obstacle(obstacle_id=1, x=-20.0, y=0.0, top=108.0)

    payload = profile.analyze(
        station=station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
        runways=[_build_runway()],
    )

    result = next(item for item in payload.rule_results if item.region_code == "I")
    assert result.is_compliant is False
    assert result.rule_code == "mb_site_protection_region_i_iii"
    assert result.metrics["limitAngleDegrees"] == 20.0
    assert result.metrics["allowedHeightMeters"] == pytest.approx(
        station.altitude + math.tan(math.radians(20.0)) * 20.0,
    )

    assert result.over_distance_meters >= 0.0
    assert 0.0 <= result.azimuth_degrees < 360.0
    assert 0.0 <= result.max_horizontal_angle_degrees < 360.0
    assert 0.0 <= result.min_horizontal_angle_degrees < 360.0
    assert isinstance(result.relative_height_meters, float)
    assert isinstance(result.is_in_radius, bool)
    assert isinstance(result.is_in_zone, bool)
    assert isinstance(result.details, str)
    assert len(result.details) > 0


def test_mb_region_ii_uses_45_degree_limit_with_expected_rule_code() -> None:
    profile = _build_profile()
    station = _build_station()
    obstacle = _build_point_obstacle(obstacle_id=2, x=0.0, y=-20.0, top=119.0)

    payload = profile.analyze(
        station=station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
        runways=[_build_runway()],
    )

    result = next(item for item in payload.rule_results if item.region_code == "II")
    assert result.is_compliant is True
    assert result.rule_code == "mb_site_protection_region_ii_iv"
    assert result.metrics["limitAngleDegrees"] == 45.0
    assert result.metrics["allowedHeightMeters"] == pytest.approx(
        station.altitude + math.tan(math.radians(45.0)) * 20.0,
    )


@pytest.mark.parametrize("region_code", ["I", "III"])
def test_mb_region_i_iii_standards_mapping(region_code: str) -> None:
    standards = build_rule_standards(
        station_type="MB",
        rule_name="mb_site_protection_region_i_iii",
        region_code=region_code,
    )

    assert standards.gb
    assert standards.gb[0].code == "GB_MB_指点信标保护区_Ⅰ_Ⅲ"
    assert standards.mh
    assert standards.mh[0].code == "MH_MB_指点信标保护区_Ⅰ_Ⅲ"


def test_mb_region_iv_style_mapping() -> None:
    style = resolve_protection_zone_style(
        zone_code="mb_site_protection",
        region_code="IV",
    )

    assert style["colorKey"] == "teal_green"
