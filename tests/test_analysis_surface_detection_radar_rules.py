from unittest.mock import MagicMock

from app.analysis.rules.surface_detection_radar import SurfaceDetectionRadarRuleProfile


def _make_station(**overrides):
    station = MagicMock()
    station.id = 1
    station.station_type = "Surface_Detection_Radar"
    station.name = "TEST_SURFACE_DETECTION_RADAR"
    station.longitude = 120.0
    station.latitude = 30.0
    station.altitude = 10.0
    station.station_sub_type = "PSR"
    station.runway_no = "18"
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
    geometry = local_geometry or {"type": "Point", "coordinates": [300.0, 0.0]}
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


def _make_runway_context(**overrides):
    runway_context = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, 300.0),
        "directionDegrees": 180.0,
        "lengthMeters": 100.0,
        "widthMeters": 45.0,
    }
    runway_context.update(overrides)
    return runway_context


def _find_rule_result(payload, rule_code):
    return next(result for result in payload.rule_results if result.rule_code == rule_code)


def test_surface_detection_radar_skips_when_matching_runway_is_missing() -> None:
    payload = SurfaceDetectionRadarRuleProfile().analyze(
        station=_make_station(runway_no="36"),
        obstacles=[_make_obstacle(local_geometry=_point_geometry(0.0, 150.0), top_elevation=25.0)],
        station_point=(0.0, 0.0),
        runways=[_make_runway_context(runNumber="18")],
    )

    assert payload.rule_results == []
    assert payload.protection_zones == []


def test_triangle_rule_passes_when_obstacle_is_outside_triangle() -> None:
    payload = SurfaceDetectionRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(local_geometry=_point_geometry(200.0, 150.0), top_elevation=25.0)],
        station_point=(0.0, 0.0),
        runways=[_make_runway_context()],
    )

    result = _find_rule_result(payload, "surface_detection_radar_runway_triangle")

    assert result.is_applicable is True
    assert result.is_compliant is True
    assert result.metrics["enteredProtectionZone"] is False
    assert result.metrics["isInRunwayTriangle"] is False
    assert result.metrics["runwayNumber"] == "18"
    assert result.metrics["runwayLengthMeters"] == 100.0
    assert result.metrics["runwayDirectionDegrees"] == 180.0


def test_triangle_rule_fails_when_obstacle_intersects_triangle() -> None:
    payload = SurfaceDetectionRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(local_geometry=_point_geometry(0.0, 150.0), top_elevation=25.0)],
        station_point=(0.0, 0.0),
        runways=[_make_runway_context()],
    )

    result = _find_rule_result(payload, "surface_detection_radar_runway_triangle")

    assert result.is_applicable is True
    assert result.is_compliant is False
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["isInRunwayTriangle"] is True
    assert result.metrics["actualDistanceMeters"] == 150.0

    assert result.over_distance_meters >= 0.0
    assert 0.0 <= result.azimuth_degrees < 360.0
    assert 0.0 <= result.max_horizontal_angle_degrees < 360.0
    assert 0.0 <= result.min_horizontal_angle_degrees < 360.0
    assert isinstance(result.relative_height_meters, float)
    assert isinstance(result.is_in_radius, bool)
    assert isinstance(result.is_in_zone, bool)
    assert isinstance(result.details, str)
    assert len(result.details) > 0


def test_base_radar_result_is_not_applicable_outside_triangle() -> None:
    payload = SurfaceDetectionRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(local_geometry=_point_geometry(200.0, 150.0), top_elevation=25.0)],
        station_point=(0.0, 0.0),
        runways=[_make_runway_context()],
    )

    result = _find_rule_result(payload, "radar_minimum_distance_460m")

    assert result.is_applicable is False
    assert result.metrics["triangleGateApplied"] is True
    assert result.metrics["isInRunwayTriangle"] is False
    assert result.metrics["gatedByRunwayTriangle"] is True


def test_base_radar_result_remains_applicable_inside_triangle() -> None:
    payload = SurfaceDetectionRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(local_geometry=_point_geometry(0.0, 150.0), top_elevation=25.0)],
        station_point=(0.0, 0.0),
        runways=[_make_runway_context()],
    )

    result = _find_rule_result(payload, "radar_minimum_distance_460m")

    assert result.is_applicable is True
    assert result.metrics["triangleGateApplied"] is True
    assert result.metrics["isInRunwayTriangle"] is True
    assert result.metrics["gatedByRunwayTriangle"] is False


def test_gated_radar_b_result_preserves_additional_fields_when_not_in_triangle() -> None:
    """方方 Radar B 最小值规则设置了 is_filter_limit=True，场监 gating 时应保留"""
    payload = SurfaceDetectionRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(obstacle_id=1, local_geometry=_point_geometry(200.0, 150.0), top_elevation=25.0)],
        station_point=(0.0, 0.0),
        runways=[_make_runway_context()],
    )

    result = _find_rule_result(payload, "radar_minimum_distance_460m")

    assert result.is_applicable is False
    assert result.is_filter_limit is True
    assert 0.0 <= result.azimuth_degrees < 360.0
    assert 0.0 <= result.max_horizontal_angle_degrees < 360.0
    assert 0.0 <= result.min_horizontal_angle_degrees < 360.0
    assert isinstance(result.relative_height_meters, float)
    assert isinstance(result.is_in_radius, bool)
    assert isinstance(result.is_in_zone, bool)
    assert result.is_mid is False
    assert result.is_filter_intersect is False
    assert isinstance(result.details, str)
    assert result.over_distance_meters >= 0.0


def test_gated_radar_b_result_preserves_additional_fields_when_in_triangle() -> None:
    """在三角区内 is_applicable 保持为 True，其它字段也应完整保留"""
    payload = SurfaceDetectionRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[_make_obstacle(obstacle_id=1, local_geometry=_point_geometry(0.0, 150.0), top_elevation=25.0)],
        station_point=(0.0, 0.0),
        runways=[_make_runway_context()],
    )

    result = _find_rule_result(payload, "radar_minimum_distance_460m")

    assert result.is_applicable is True
    assert result.is_filter_limit is True
    assert 0.0 <= result.azimuth_degrees < 360.0
    assert 0.0 <= result.max_horizontal_angle_degrees < 360.0
    assert 0.0 <= result.min_horizontal_angle_degrees < 360.0
    assert isinstance(result.relative_height_meters, float)
    assert isinstance(result.is_in_radius, bool)
    assert isinstance(result.is_in_zone, bool)
    assert result.is_mid is False
    assert result.is_filter_intersect is False
    assert isinstance(result.details, str)
    assert result.over_distance_meters >= 0.0


def test_gated_radar_16km_result_preserves_additional_fields() -> None:
    """Radar 16KM 规则同样设置了 is_filter_limit=True，场监 gating 时应保留"""
    payload = SurfaceDetectionRadarRuleProfile().analyze(
        station=_make_station(),
        obstacles=[
            _make_obstacle(
                obstacle_id=1,
                category="large_rotating_reflector",
                local_geometry=_point_geometry(200.0, 150.0),
                top_elevation=88.0,
            )
        ],
        station_point=(0.0, 0.0),
        runways=[_make_runway_context()],
    )

    result = _find_rule_result(payload, "radar_rotating_reflector_16km")
    assert result.is_applicable is False
    assert result.is_filter_limit is True
    assert result.metrics["triangleGateApplied"] is True
    assert result.metrics["gatedByRunwayTriangle"] is True
