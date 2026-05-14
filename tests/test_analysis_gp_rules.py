import importlib
import math

import pytest
from shapely.geometry import LineString
from shapely.geometry import MultiPolygon
from shapely.geometry import Point
from shapely.geometry import Polygon
from unittest.mock import patch

from app.analysis.protection_zone_style import resolve_protection_zone_style


def _make_gp_station(**overrides: object) -> object:
    payload = {
        "id": 301,
        "station_type": "GP",
        "altitude": 500.0,
        "runway_no": "18",
        "station_sub_type": "I",
        "distance_to_runway": 360.0,
        "distance_v_to_runway": 180.0,
        "downward_angle": 3.0,
        "frequency": 330.0,
        "coverage_radius": 18520.0,
        "antenna_height": 6.0,
        "antenna_hag": 4.0,
    }
    payload.update(overrides)
    return type("Station", (), payload)()


def test_gp_parameter_resolution_defaults_antenna_type_to_m() -> None:
    helpers = importlib.import_module("app.analysis.rules.gp.site_protection.helpers")

    assert helpers.resolve_gp_antenna_type(_make_gp_station()) == "M"


def test_gp_parameter_resolution_accepts_explicit_antenna_type() -> None:
    helpers = importlib.import_module("app.analysis.rules.gp.site_protection.helpers")

    assert helpers.resolve_gp_antenna_type(_make_gp_station(antenna_type="O")) == "O"
    assert helpers.resolve_gp_antenna_type(_make_gp_station(antenna_type="B")) == "B"


def test_gp_effective_antenna_height_uses_max_height_and_hag() -> None:
    helpers = importlib.import_module("app.analysis.rules.gp.site_protection.helpers")

    assert (
        helpers.resolve_gp_effective_antenna_height_meters(
            _make_gp_station(antenna_height=5.0, antenna_hag=8.0)
        )
        == 8.0
    )


def test_station_model_does_not_require_db_column_for_gp_antenna_type() -> None:
    from app.models.station import Station

    assert "antenna_type" not in Station.__table__.columns.keys()


def test_gp_parameter_resolution_returns_distinct_zone_codes_for_gb_and_mh() -> None:
    helpers = importlib.import_module("app.analysis.rules.gp.site_protection.helpers")

    gb = helpers.resolve_gp_site_protection_parameters(
        standard_version="GB",
    )
    mh = helpers.resolve_gp_site_protection_parameters(
        standard_version="MH",
    )

    assert gb.zone_code == "gp_site_protection_gb"
    assert mh.zone_code == "gp_site_protection_mh"


def test_gp_style_mapping_keeps_same_region_color_strategy_between_standards() -> None:
    helpers = importlib.import_module("app.analysis.rules.gp.site_protection.helpers")

    gb = helpers.resolve_gp_site_protection_parameters(
        standard_version="GB",
    )
    mh = helpers.resolve_gp_site_protection_parameters(
        standard_version="MH",
    )

    for region_code, expected_color_key in {
        "A": "sky_blue",
        "B": "teal_green",
        "C": "danger_red",
    }.items():
        assert resolve_protection_zone_style(
            zone_code=gb.zone_code,
            region_code=region_code,
        )["colorKey"] == expected_color_key
        assert resolve_protection_zone_style(
            zone_code=mh.zone_code,
            region_code=region_code,
        )["colorKey"] == expected_color_key


def test_gp_1deg_style_mapping_uses_explicit_color() -> None:
    assert resolve_protection_zone_style(
        zone_code="gp_elevation_restriction_1deg",
        region_code="default",
    )["colorKey"] == "amber_orange"


def test_gp_run_area_style_mapping_uses_explicit_region_colors() -> None:
    assert resolve_protection_zone_style(
        zone_code="gp_run_area_protection",
        region_code="A",
    )["colorKey"] == "danger_red"
    assert resolve_protection_zone_style(
        zone_code="gp_run_area_protection",
        region_code="B",
    )["colorKey"] == "teal_green"


def test_gp_shared_context_uses_reverse_runway_direction_as_forward_axis() -> None:
    helpers = importlib.import_module("app.analysis.rules.gp.site_protection.helpers")
    shared_context = helpers.build_gp_site_protection_shared_context(
        station=_make_gp_station(),
        station_point=(0.0, 0.0),
        runway_context={
            "runNumber": "18",
            "directionDegrees": 0.0,
            "widthMeters": 45.0,
            "lengthMeters": 600.0,
            "localCenterPoint": (0.0, -600.0),
        },
        standard_version="GB",
    )

    assert shared_context.axis_unit == (0.0, -1.0)


def test_gp_region_a_builds_core_trapezoid_as_multipolygon() -> None:
    helpers = importlib.import_module("app.analysis.rules.gp.site_protection.helpers")
    shared_context = helpers.build_gp_site_protection_shared_context(
        station=_make_gp_station(distance_v_to_runway=180.0),
        station_point=(0.0, 0.0),
        runway_context={
            "runNumber": "18",
            "directionDegrees": 0.0,
            "widthMeters": 40.0,
            "lengthMeters": 600.0,
            "localCenterPoint": (0.0, -600.0),
        },
        standard_version="GB",
    )

    geometry = helpers.build_gp_site_protection_region_a_geometry(shared_context)

    assert isinstance(geometry.local_geometry, MultiPolygon)
    polygon = geometry.local_geometry.geoms[0]
    coordinates = list(polygon.exterior.coords)
    assert coordinates == [
        (30.0, 0.0),
        (60.0, -360.0),
        (-160.0, -360.0),
        (-160.0, 0.0),
        (30.0, 0.0),
    ]


def test_gp_region_b_uses_different_forward_lengths_for_gb_and_mh() -> None:
    helpers = importlib.import_module("app.analysis.rules.gp.site_protection.helpers")
    runway_context = {
        "runNumber": "18",
        "directionDegrees": 0.0,
        "widthMeters": 40.0,
        "lengthMeters": 600.0,
        "localCenterPoint": (0.0, -600.0),
    }
    station = _make_gp_station(distance_v_to_runway=180.0)
    gb_context = helpers.build_gp_site_protection_shared_context(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway_context,
        standard_version="GB",
    )
    mh_context = helpers.build_gp_site_protection_shared_context(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway_context,
        standard_version="MH",
    )

    gb_geometry = helpers.build_gp_site_protection_region_b_geometry(gb_context)
    mh_geometry = helpers.build_gp_site_protection_region_b_geometry(mh_context)

    gb_bounds = gb_geometry.local_geometry.bounds
    mh_bounds = mh_geometry.local_geometry.bounds
    assert gb_bounds == (-160.0, -900.0, 60.0, -360.0)
    assert mh_bounds == (-160.0, -600.0, 60.0, -360.0)


def test_gp_region_c_mirrors_side_when_distance_v_to_runway_changes_sign() -> None:
    helpers = importlib.import_module("app.analysis.rules.gp.site_protection.helpers")
    runway_context = {
        "runNumber": "18",
        "directionDegrees": 0.0,
        "widthMeters": 40.0,
        "lengthMeters": 600.0,
        "localCenterPoint": (0.0, -600.0),
    }
    positive_context = helpers.build_gp_site_protection_shared_context(
        station=_make_gp_station(distance_v_to_runway=180.0),
        station_point=(0.0, 0.0),
        runway_context=runway_context,
        standard_version="GB",
    )
    negative_context = helpers.build_gp_site_protection_shared_context(
        station=_make_gp_station(distance_v_to_runway=-180.0),
        station_point=(0.0, 0.0),
        runway_context=runway_context,
        standard_version="GB",
    )

    positive_bounds = helpers.build_gp_site_protection_region_c_geometry(
        positive_context
    ).local_geometry.bounds
    negative_bounds = helpers.build_gp_site_protection_region_c_geometry(
        negative_context
    ).local_geometry.bounds

    assert positive_bounds == (30.0, -900.0, 120.0, 0.0)
    assert negative_bounds == (-120.0, -900.0, -30.0, 0.0)


def test_gp_judgement_recognizes_cable_categories() -> None:
    judgement = importlib.import_module(
        "app.analysis.rules.gp.site_protection.judgement"
    )

    assert judgement.is_gp_cable_category("power_or_communication_cable") is True
    assert judgement.is_gp_cable_category("power_line_high_voltage_overhead") is False


def test_gp_judgement_recognizes_airport_ring_road_category() -> None:
    judgement = importlib.import_module(
        "app.analysis.rules.gp.site_protection.judgement"
    )

    assert judgement.is_gp_airport_ring_road_category("airport_ring_road") is True
    assert judgement.is_gp_airport_ring_road_category("road") is False


def test_gp_judgement_recognizes_road_or_rail_categories() -> None:
    judgement = importlib.import_module(
        "app.analysis.rules.gp.site_protection.judgement"
    )

    assert judgement.is_gp_road_or_rail_category("road") is True
    assert judgement.is_gp_road_or_rail_category("railway_electrified") is True
    assert judgement.is_gp_road_or_rail_category("railway_non_electrified") is True
    assert judgement.is_gp_road_or_rail_category("building_general") is False


def test_gp_judgement_calculates_region_intersection_forward_distance_for_point() -> None:
    helpers = importlib.import_module("app.analysis.rules.gp.site_protection.helpers")
    judgement = importlib.import_module(
        "app.analysis.rules.gp.site_protection.judgement"
    )
    shared_context = helpers.build_gp_site_protection_shared_context(
        station=_make_gp_station(distance_v_to_runway=180.0),
        station_point=(0.0, 0.0),
        runway_context={
            "runNumber": "18",
            "directionDegrees": 0.0,
            "widthMeters": 40.0,
            "lengthMeters": 600.0,
            "localCenterPoint": (0.0, -600.0),
        },
        standard_version="GB",
    )
    region_geometry = helpers.build_gp_site_protection_region_b_geometry(shared_context)

    distance = judgement.calculate_gp_zone_intersection_min_forward_distance_meters(
        obstacle_geometry={
            "type": "Point",
            "coordinates": [60.0, -500.0],
        },
        zone_geometry=region_geometry.local_geometry,
        shared_context=shared_context,
    )

    assert distance == 500.0


def test_gp_judgement_returns_none_when_obstacle_stays_outside_zone() -> None:
    helpers = importlib.import_module("app.analysis.rules.gp.site_protection.helpers")
    judgement = importlib.import_module(
        "app.analysis.rules.gp.site_protection.judgement"
    )
    shared_context = helpers.build_gp_site_protection_shared_context(
        station=_make_gp_station(distance_v_to_runway=180.0),
        station_point=(0.0, 0.0),
        runway_context={
            "runNumber": "18",
            "directionDegrees": 0.0,
            "widthMeters": 40.0,
            "lengthMeters": 600.0,
            "localCenterPoint": (0.0, -600.0),
        },
        standard_version="GB",
    )
    region_geometry = helpers.build_gp_site_protection_region_b_geometry(shared_context)

    distance = judgement.calculate_gp_zone_intersection_min_forward_distance_meters(
        obstacle_geometry={
            "type": "Point",
            "coordinates": [80.0, 200.0],
        },
        zone_geometry=region_geometry.local_geometry,
        shared_context=shared_context,
    )

    assert distance is None


def test_gp_judgement_calculates_min_forward_distance_for_partial_linestring_intersection() -> None:
    helpers = importlib.import_module("app.analysis.rules.gp.site_protection.helpers")
    judgement = importlib.import_module(
        "app.analysis.rules.gp.site_protection.judgement"
    )
    shared_context = helpers.build_gp_site_protection_shared_context(
        station=_make_gp_station(distance_v_to_runway=180.0),
        station_point=(0.0, 0.0),
        runway_context={
            "runNumber": "18",
            "directionDegrees": 0.0,
            "widthMeters": 40.0,
            "lengthMeters": 600.0,
            "localCenterPoint": (0.0, -600.0),
        },
        standard_version="GB",
    )
    region_geometry = helpers.build_gp_site_protection_region_b_geometry(shared_context)

    distance = judgement.calculate_gp_zone_intersection_min_forward_distance_meters(
        obstacle_geometry={
            "type": "LineString",
            "coordinates": [
                [60.0, -700.0],
                [60.0, -500.0],
            ],
        },
        zone_geometry=region_geometry.local_geometry,
        shared_context=shared_context,
    )

    assert distance == 500.0


def test_gp_judgement_uses_segment_minimum_for_polygon_intersection() -> None:
    helpers = importlib.import_module("app.analysis.rules.gp.site_protection.helpers")
    judgement = importlib.import_module(
        "app.analysis.rules.gp.site_protection.judgement"
    )
    shared_context = helpers.build_gp_site_protection_shared_context(
        station=_make_gp_station(distance_v_to_runway=180.0),
        station_point=(0.0, 0.0),
        runway_context={
            "runNumber": "18",
            "directionDegrees": 0.0,
            "widthMeters": 40.0,
            "lengthMeters": 600.0,
            "localCenterPoint": (0.0, -600.0),
        },
        standard_version="GB",
    )
    region_geometry = helpers.build_gp_site_protection_region_b_geometry(shared_context)

    distance = judgement.calculate_gp_zone_intersection_min_forward_distance_meters(
        obstacle_geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [60.0, -700.0],
                    [60.0, -500.0],
                    [80.0, -700.0],
                    [60.0, -700.0],
                ]
            ],
        },
        zone_geometry=region_geometry.local_geometry,
        shared_context=shared_context,
    )

    assert distance == pytest.approx(500.0)


def test_gp_judgement_geometry_evaluation_helper_minimizes_metric_across_polygon_segments() -> None:
    geometry_evaluation = importlib.import_module(
        "app.analysis.rules.geometry_evaluation"
    )

    result = geometry_evaluation.evaluate_geometry_metric(
        geometry=Polygon(
            [
                (0.0, 0.0),
                (10.0, 10.0),
                (20.0, 0.0),
                (0.0, 0.0),
            ]
        ),
        point_metric=lambda point: point.y,
        collect_point_candidates=False,
    )

    assert result.min_metric == pytest.approx(0.0)


def test_gp_clearance_helper_returns_none_by_default() -> None:
    clearance = importlib.import_module("app.analysis.rules.gp.clearance")

    assert (
        clearance.calculate_gp_clearance_limit_height_meters(
            runway_context={"runNumber": "18"},
            obstacle={
                "obstacleId": 900,
                "name": "Test Obstacle",
                "topElevation": 510.0,
            },
        )
        is None
    )


def test_gp_region_a_binder_builds_gb_zone_spec() -> None:
    region_a_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_a"
    )

    bound_rule = region_a_module.GpSiteProtectionGbRegionARule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="GB"),
    )

    assert bound_rule.protection_zone.zone_code == "gp_site_protection_gb"
    assert bound_rule.protection_zone.region_code == "A"
    assert bound_rule.protection_zone.rule_code == "gp_site_protection_gb_region_a"


def test_gp_region_a_binder_builds_mh_zone_spec() -> None:
    region_a_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_a"
    )

    bound_rule = region_a_module.GpSiteProtectionMhRegionARule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="MH"),
    )

    assert bound_rule.protection_zone.zone_code == "gp_site_protection_mh"
    assert bound_rule.protection_zone.region_code == "A"
    assert bound_rule.protection_zone.rule_code == "gp_site_protection_mh_region_a"


def test_gp_region_b_binder_builds_gb_zone_spec() -> None:
    region_b_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_b"
    )

    bound_rule = region_b_module.GpSiteProtectionGbRegionBRule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="GB"),
    )

    assert bound_rule.protection_zone.zone_code == "gp_site_protection_gb"
    assert bound_rule.protection_zone.region_code == "B"
    assert bound_rule.protection_zone.rule_code == "gp_site_protection_gb_region_b"


def test_gp_region_b_binder_builds_mh_zone_spec() -> None:
    region_b_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_b"
    )

    bound_rule = region_b_module.GpSiteProtectionMhRegionBRule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="MH"),
    )

    assert bound_rule.protection_zone.zone_code == "gp_site_protection_mh"
    assert bound_rule.protection_zone.region_code == "B"
    assert bound_rule.protection_zone.rule_code == "gp_site_protection_mh_region_b"


def test_gp_region_c_binder_builds_gb_zone_spec() -> None:
    region_c_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_c"
    )

    bound_rule = region_c_module.GpSiteProtectionGbRegionCRule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="GB"),
    )

    assert bound_rule.protection_zone.zone_code == "gp_site_protection_gb"
    assert bound_rule.protection_zone.region_code == "C"
    assert bound_rule.protection_zone.rule_code == "gp_site_protection_gb_region_c"


def test_gp_region_c_binder_builds_mh_zone_spec() -> None:
    region_c_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_c"
    )

    bound_rule = region_c_module.GpSiteProtectionMhRegionCRule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="MH"),
    )

    assert bound_rule.protection_zone.zone_code == "gp_site_protection_mh"
    assert bound_rule.protection_zone.region_code == "C"
    assert bound_rule.protection_zone.rule_code == "gp_site_protection_mh_region_c"


def test_gp_region_c_road_entering_region_is_non_compliant() -> None:
    region_c_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_c"
    )

    bound_rule = region_c_module.GpSiteProtectionGbRegionCRule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="GB"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 21,
            "name": "Road In Region C",
            "rawObstacleType": "道路",
            "globalObstacleCategory": "road",
            "topElevation": 510.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [60.0, -100.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [60.0, -100.0],
            },
        }
    )

    assert result.is_compliant is False
    assert result.message == "在C区范围内"
    assert result.metrics == {
        "enteredProtectionZone": True,
        "topElevationMeters": 510.0,
        "actualDistanceMeters": pytest.approx(116.61903789690601, rel=1e-9),
        "isRoadOrRail": True,
        "requiresClearanceEvaluation": False,
    }
    assert result.standards_rule_code == "gp_site_protection_gb_region_c"


def test_gp_region_c_electrified_rail_entering_region_is_non_compliant() -> None:
    region_c_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_c"
    )

    bound_rule = region_c_module.GpSiteProtectionGbRegionCRule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="GB"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 22,
            "name": "Electrified Rail In Region C",
            "rawObstacleType": "电气化铁路",
            "globalObstacleCategory": "railway_electrified",
            "topElevation": 510.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [60.0, -100.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [60.0, -100.0],
            },
        }
    )

    assert result.is_compliant is False
    assert result.message == "在C区范围内"
    assert result.metrics == {
        "enteredProtectionZone": True,
        "topElevationMeters": 510.0,
        "actualDistanceMeters": pytest.approx(116.61903789690601, rel=1e-9),
        "isRoadOrRail": True,
        "requiresClearanceEvaluation": False,
    }


def test_gp_region_c_non_electrified_rail_entering_region_is_non_compliant() -> None:
    region_c_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_c"
    )

    bound_rule = region_c_module.GpSiteProtectionMhRegionCRule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="MH"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 23,
            "name": "Non-Electrified Rail In Region C",
            "rawObstacleType": "非电气化铁路",
            "globalObstacleCategory": "railway_non_electrified",
            "topElevation": 510.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [60.0, -100.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [60.0, -100.0],
            },
        }
    )

    assert result.is_compliant is False
    assert result.message == "在C区范围内"
    assert result.metrics == {
        "enteredProtectionZone": True,
        "topElevationMeters": 510.0,
        "actualDistanceMeters": pytest.approx(116.61903789690601, rel=1e-9),
        "isRoadOrRail": True,
        "requiresClearanceEvaluation": False,
    }
    assert result.standards_rule_code == "gp_site_protection_mh_region_c"


def test_gp_region_c_non_road_or_rail_with_unavailable_clearance_is_non_compliant() -> None:
    region_c_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_c"
    )

    bound_rule = region_c_module.GpSiteProtectionMhRegionCRule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="MH"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 24,
            "name": "Building In Region C",
            "rawObstacleType": "建筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 510.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [60.0, -100.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [60.0, -100.0],
            },
        }
    )

    assert result.is_compliant is True
    assert result.message == "gp clearance evaluation pending"
    assert result.metrics == {
        "enteredProtectionZone": True,
        "topElevationMeters": 510.0,
        "actualDistanceMeters": pytest.approx(116.61903789690601, rel=1e-9),
        "isRoadOrRail": False,
        "requiresClearanceEvaluation": True,
    }
    assert result.standards_rule_code == "gp_site_protection_mh_region_c"


def test_gp_region_c_non_road_or_rail_with_available_clearance_can_be_compliant(
    monkeypatch,
) -> None:
    region_c_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_c"
    )

    monkeypatch.setattr(
        region_c_module,
        "calculate_gp_clearance_limit_height_meters",
        lambda **_: 520.0,
    )

    bound_rule = region_c_module.GpSiteProtectionMhRegionCRule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="MH"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 25,
            "name": "Building In Region C Below Limit",
            "rawObstacleType": "建筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 510.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [60.0, -100.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [60.0, -100.0],
            },
        }
    )

    assert result.is_compliant is True
    assert result.metrics == {
        "enteredProtectionZone": True,
        "topElevationMeters": 510.0,
        "actualDistanceMeters": pytest.approx(116.61903789690601, rel=1e-9),
        "isRoadOrRail": False,
        "requiresClearanceEvaluation": True,
        "clearanceLimitHeightMeters": 520.0,
        "allowedHeightMeters": 520.0,
        "overHeightMeters": -10.0,
    }


def test_gp_region_c_non_road_or_rail_with_available_clearance_can_be_non_compliant(
    monkeypatch,
) -> None:
    region_c_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_c"
    )

    monkeypatch.setattr(
        region_c_module,
        "calculate_gp_clearance_limit_height_meters",
        lambda **_: 520.0,
    )

    bound_rule = region_c_module.GpSiteProtectionMhRegionCRule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="MH"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 26,
            "name": "Building In Region C Above Limit",
            "rawObstacleType": "建筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 530.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [60.0, -100.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [60.0, -100.0],
            },
        }
    )

    assert result.is_compliant is False
    assert result.metrics == {
        "enteredProtectionZone": True,
        "topElevationMeters": 530.0,
        "actualDistanceMeters": pytest.approx(116.61903789690601, rel=1e-9),
        "isRoadOrRail": False,
        "requiresClearanceEvaluation": True,
        "clearanceLimitHeightMeters": 520.0,
        "allowedHeightMeters": 520.0,
        "overHeightMeters": 10.0,
    }


def test_gp_region_a_cable_below_station_altitude_is_compliant() -> None:
    region_a_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_a"
    )

    bound_rule = region_a_module.GpSiteProtectionGbRegionARule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="GB"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 5,
            "name": "Cable Below Station",
            "rawObstacleType": "通信线",
            "globalObstacleCategory": "power_or_communication_cable",
            "topElevation": 499.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [0.0, -200.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [0.0, -200.0],
            },
        }
    )

    assert result.is_compliant is True
    assert result.metrics == {
        "enteredProtectionZone": True,
        "isCable": True,
        "baseHeightMeters": 500.0,
        "allowedHeightMeters": 500.0,
        "topElevationMeters": 499.0,
        "actualDistanceMeters": 200.0,
        "overHeightMeters": 0.0,
    }
    assert result.standards_rule_code == "gp_site_protection_gb_region_a_cable"


def test_gp_region_a_cable_at_or_above_station_altitude_is_non_compliant() -> None:
    region_a_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_a"
    )

    bound_rule = region_a_module.GpSiteProtectionGbRegionARule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="GB"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 6,
            "name": "Cable Above Station",
            "rawObstacleType": "通信线",
            "globalObstacleCategory": "power_or_communication_cable",
            "topElevation": 500.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [0.0, -200.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [0.0, -200.0],
            },
        }
    )

    assert result.is_compliant is False
    assert result.metrics == {
        "enteredProtectionZone": True,
        "isCable": True,
        "baseHeightMeters": 500.0,
        "allowedHeightMeters": 500.0,
        "topElevationMeters": 500.0,
        "actualDistanceMeters": 200.0,
        "overHeightMeters": 0.0,
    }
    assert result.standards_rule_code == "gp_site_protection_gb_region_a_cable"


def test_gp_region_a_non_cable_entering_region_is_non_compliant() -> None:
    region_a_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_a"
    )

    bound_rule = region_a_module.GpSiteProtectionGbRegionARule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="GB"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 7,
            "name": "Building In Region A",
            "rawObstacleType": "建筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 510.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [0.0, -200.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [0.0, -200.0],
            },
        }
    )

    assert result.is_compliant is False
    assert result.metrics == {
        "enteredProtectionZone": True,
        "isCable": False,
        "baseHeightMeters": 500.0,
        "topElevationMeters": 510.0,
        "actualDistanceMeters": 200.0,
        "overHeightMeters": 10.0,
    }
    assert result.standards_rule_code == "gp_site_protection_gb_region_a"


def test_gp_region_a_non_cable_outside_region_is_compliant() -> None:
    region_a_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_a"
    )

    bound_rule = region_a_module.GpSiteProtectionMhRegionARule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="MH"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 8,
            "name": "Building Outside Region A",
            "rawObstacleType": "建筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 510.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [50.0, 200.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [50.0, 200.0],
            },
        }
    )

    assert result.is_compliant is True
    assert result.metrics == {
        "enteredProtectionZone": False,
        "isCable": False,
        "baseHeightMeters": 500.0,
        "topElevationMeters": 510.0,
        "actualDistanceMeters": pytest.approx(206.15528128088303, rel=1e-9),
        "overHeightMeters": 10.0,
    }
    assert result.standards_rule_code == "gp_site_protection_mh_region_a"


def test_gp_region_b_does_not_inherit_region_a_cable_exception() -> None:
    region_b_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_b"
    )

    bound_rule = region_b_module.GpSiteProtectionGbRegionBRule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="GB"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 15,
            "name": "Cable In Region B",
            "rawObstacleType": "电力线缆和通信线缆",
            "globalObstacleCategory": "power_or_communication_cable",
            "topElevation": 490.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [60.0, -500.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [60.0, -500.0],
            },
        }
    )

    assert result.is_compliant is False
    assert result.standards_rule_code == "gp_site_protection_gb_region_b"


def test_gp_bound_rule_returns_compliant_when_obstacle_stays_outside_zone() -> None:
    region_a_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_a"
    )

    bound_rule = region_a_module.GpSiteProtectionMhRegionARule().bind(
        station=_make_gp_station(station_sub_type="III"),
        shared_context=_make_gp_shared_context(standard_version="MH"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 2,
            "name": "Outside Obstacle",
            "rawObstacleType": "建筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 510.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [50.0, 200.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [50.0, 200.0],
            },
        }
    )

    assert result.is_applicable is True
    assert result.is_compliant is True
    assert result.message == "不在A区范围内"
    assert result.metrics["enteredProtectionZone"] is False
    assert result.standards_rule_code == "gp_site_protection_mh_region_a"


def test_gp_region_b_rule_returns_mh_subtype_specific_standards_rule_code() -> None:
    region_b_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_b"
    )
    station = _make_gp_station(station_sub_type="II")
    helpers = importlib.import_module("app.analysis.rules.gp.site_protection.helpers")
    shared_context = helpers.build_gp_site_protection_shared_context(
        station=station,
        station_point=(0.0, 0.0),
        runway_context={
            "runNumber": "18",
            "directionDegrees": 0.0,
            "widthMeters": 40.0,
            "lengthMeters": 600.0,
            "localCenterPoint": (0.0, -600.0),
        },
        standard_version="MH",
    )
    bound_rule = region_b_module.GpSiteProtectionMhRegionBRule().bind(
        station=station,
        shared_context=shared_context,
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 4,
            "name": "Outside B Obstacle",
            "rawObstacleType": "建筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 510.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [200.0, 200.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [200.0, 200.0],
            },
        }
    )

    assert result.standards_rule_code == "gp_site_protection_mh_region_b_ii"


def test_gp_region_b_gb_entered_within_600m_is_non_compliant() -> None:
    region_b_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_b"
    )

    bound_rule = region_b_module.GpSiteProtectionGbRegionBRule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="GB"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 16,
            "name": "Building Within 600m",
            "rawObstacleType": "建筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 510.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [60.0, -500.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [60.0, -500.0],
            },
        }
    )

    assert result.is_compliant is False
    assert result.message == "在B区范围600米内"
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["forwardDistanceMeters"] == 500.0
    assert result.metrics["requiresClearanceEvaluation"] is False


def test_gp_region_b_mh_i_entered_is_non_compliant() -> None:
    region_b_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_b"
    )

    bound_rule = region_b_module.GpSiteProtectionMhRegionBRule().bind(
        station=_make_gp_station(station_sub_type="I"),
        shared_context=_make_gp_shared_context(standard_version="MH"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 17,
            "name": "MH I Building",
            "rawObstacleType": "建筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 510.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [60.0, -500.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [60.0, -500.0],
            },
        }
    )

    assert result.is_compliant is False
    assert result.message == "在B区范围内"
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["stationSubType"] == "I"


def test_gp_region_b_mh_ii_ring_road_within_600m_is_non_compliant() -> None:
    region_b_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_b"
    )

    bound_rule = region_b_module.GpSiteProtectionMhRegionBRule().bind(
        station=_make_gp_station(station_sub_type="II"),
        shared_context=_make_gp_shared_context(standard_version="MH"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 18,
            "name": "MH II Ring Road Within 600m",
            "rawObstacleType": "机场环场路",
            "globalObstacleCategory": "airport_ring_road",
            "topElevation": 510.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [60.0, -500.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [60.0, -500.0],
            },
        }
    )

    assert result.is_compliant is False
    assert result.message == "在B区范围600米内"
    assert result.metrics["isAirportRingRoad"] is True
    assert result.metrics["forwardDistanceMeters"] == 500.0


def test_gp_region_b_mh_ii_ring_road_outside_600m_is_compliant() -> None:
    region_b_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_b"
    )

    bound_rule = region_b_module.GpSiteProtectionMhRegionBRule().bind(
        station=_make_gp_station(station_sub_type="II"),
        shared_context=_make_gp_shared_context(standard_version="MH"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 19,
            "name": "MH II Ring Road Outside 600m",
            "rawObstacleType": "机场环场路",
            "globalObstacleCategory": "airport_ring_road",
            "topElevation": 510.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [60.0, -700.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [60.0, -700.0],
            },
        }
    )

    assert result.is_compliant is True
    assert result.message == "不在B区范围内"
    assert result.metrics["isAirportRingRoad"] is True
    assert result.metrics["forwardDistanceMeters"] is None


def test_gp_region_b_mh_iii_non_ring_road_entered_is_non_compliant() -> None:
    region_b_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_b"
    )

    bound_rule = region_b_module.GpSiteProtectionMhRegionBRule().bind(
        station=_make_gp_station(station_sub_type="III"),
        shared_context=_make_gp_shared_context(standard_version="MH"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 20,
            "name": "MH III Building",
            "rawObstacleType": "建筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 510.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [60.0, -500.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [60.0, -500.0],
            },
        }
    )

    assert result.is_compliant is False
    assert result.message == "在B区范围内"
    assert result.metrics["isAirportRingRoad"] is False
    assert result.metrics["stationSubType"] == "III"


def test_gp_region_b_gb_entered_outside_600m_with_unavailable_clearance_is_non_compliant() -> None:
    region_b_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_b"
    )

    bound_rule = region_b_module.GpSiteProtectionGbRegionBRule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="GB"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 21,
            "name": "GB Building Outside 600m",
            "rawObstacleType": "建筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 510.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [60.0, -700.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [60.0, -700.0],
            },
        }
    )

    assert result.is_compliant is True
    assert result.message == "gp clearance evaluation pending"
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["forwardDistanceMeters"] == 700.0
    assert result.metrics["requiresClearanceEvaluation"] is True


def test_gp_region_b_gb_entered_outside_600m_with_available_clearance_can_be_compliant(
    monkeypatch,
) -> None:
    region_b_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_b"
    )

    monkeypatch.setattr(
        region_b_module,
        "calculate_gp_clearance_limit_height_meters",
        lambda **_: 520.0,
    )

    bound_rule = region_b_module.GpSiteProtectionGbRegionBRule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="GB"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 22,
            "name": "GB Building Outside 600m Below Limit",
            "rawObstacleType": "建筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 510.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [60.0, -700.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [60.0, -700.0],
            },
        }
    )

    assert result.is_compliant is True
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["forwardDistanceMeters"] == 700.0
    assert result.metrics["requiresClearanceEvaluation"] is True
    assert result.metrics["clearanceLimitHeightMeters"] == 520.0
    assert result.metrics["overHeightMeters"] == -10.0


def test_gp_region_b_gb_entered_outside_600m_with_available_clearance_can_be_non_compliant(
    monkeypatch,
) -> None:
    region_b_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_b"
    )

    monkeypatch.setattr(
        region_b_module,
        "calculate_gp_clearance_limit_height_meters",
        lambda **_: 520.0,
    )

    bound_rule = region_b_module.GpSiteProtectionGbRegionBRule().bind(
        station=_make_gp_station(),
        shared_context=_make_gp_shared_context(standard_version="GB"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 23,
            "name": "GB Building Outside 600m Above Limit",
            "rawObstacleType": "建筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 530.0,
            "localGeometry": {
                "type": "Point",
                "coordinates": [60.0, -700.0],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [60.0, -700.0],
            },
        }
    )

    assert result.is_compliant is False
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["forwardDistanceMeters"] == 700.0
    assert result.metrics["requiresClearanceEvaluation"] is True
    assert result.metrics["clearanceLimitHeightMeters"] == 520.0
    assert result.metrics["overHeightMeters"] == 10.0


def test_gp_run_area_region_a_returns_is_mid_when_type_not_supported() -> None:
    region_a_module = importlib.import_module(
        "app.analysis.rules.gp.run_area_protection.region_a"
    )
    helpers = importlib.import_module(
        "app.analysis.rules.gp.run_area_protection.helpers"
    )

    station = type(
        "Station", (),
        {
            "id": 301,
            "station_type": "GP",
            "altitude": 500.0,
            "runway_no": "18",
            "station_sub_type": "I",
            "distance_v_to_runway": 180.0,
        },
    )()
    runway_context = {
        "runNumber": "18",
        "directionDegrees": 0.0,
        "widthMeters": 45.0,
        "lengthMeters": 600.0,
        "localCenterPoint": (0.0, -600.0),
        "maximumAirworthiness": 0,
    }
    shared_context = helpers.build_gp_run_area_shared_context(
        station=station, station_point=(0.0, 0.0), runway_context=runway_context,
    )
    assert shared_context is not None

    bound_rule = region_a_module.GpRunAreaProtectionRegionARule().bind(
        station=station, shared_context=shared_context,
    )
    zone_geom = bound_rule.protection_zone.local_geometry
    point = zone_geom.representative_point()
    inside_obstacle = {
        "obstacleId": 777,
        "name": "Building Inside Run Area A",
        "rawObstacleType": "建筑物",
        "globalObstacleCategory": "building_general",
        "topElevation": 510.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [[[[float(point.x - 2), float(point.y - 2)],
                               [float(point.x + 2), float(point.y - 2)],
                               [float(point.x + 2), float(point.y + 2)],
                               [float(point.x - 2), float(point.y + 2)],
                               [float(point.x - 2), float(point.y - 2)]]]],
        },
    }
    result = bound_rule.analyze(inside_obstacle)
    assert result.is_mid is True
    assert result.is_applicable is False
    assert result.metrics["enteredProtectionZone"] is True


def test_gp_run_area_region_b_returns_is_mid_when_type_not_supported() -> None:
    region_b_module = importlib.import_module(
        "app.analysis.rules.gp.run_area_protection.region_b"
    )
    helpers = importlib.import_module(
        "app.analysis.rules.gp.run_area_protection.helpers"
    )

    station = type(
        "Station", (),
        {
            "id": 302,
            "station_type": "GP",
            "altitude": 500.0,
            "runway_no": "18",
            "station_sub_type": "I",
            "distance_v_to_runway": 180.0,
        },
    )()
    runway_context = {
        "runNumber": "18",
        "directionDegrees": 0.0,
        "widthMeters": 45.0,
        "lengthMeters": 600.0,
        "localCenterPoint": (0.0, -600.0),
        "maximumAirworthiness": 0,
    }
    shared_context = helpers.build_gp_run_area_shared_context(
        station=station, station_point=(0.0, 0.0), runway_context=runway_context,
    )
    assert shared_context is not None

    bound_rule = region_b_module.GpRunAreaProtectionRegionBRule().bind(
        station=station, shared_context=shared_context,
    )
    zone_geom = bound_rule.protection_zone.local_geometry
    point = zone_geom.representative_point()
    inside_obstacle = {
        "obstacleId": 778,
        "name": "Building Inside Run Area B",
        "rawObstacleType": "建筑物",
        "globalObstacleCategory": "building_general",
        "topElevation": 510.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [[[[float(point.x - 2), float(point.y - 2)],
                               [float(point.x + 2), float(point.y - 2)],
                               [float(point.x + 2), float(point.y + 2)],
                               [float(point.x - 2), float(point.y + 2)],
                               [float(point.x - 2), float(point.y - 2)]]]],
        },
    }
    result = bound_rule.analyze(inside_obstacle)
    assert result.is_mid is True
    assert result.is_applicable is False
    assert result.metrics["enteredProtectionZone"] is True


def _make_gp_shared_context(*, standard_version: str):
    helpers = importlib.import_module("app.analysis.rules.gp.site_protection.helpers")
    return helpers.build_gp_site_protection_shared_context(
        station=_make_gp_station(),
        station_point=(0.0, 0.0),
        runway_context={
            "runNumber": "18",
            "directionDegrees": 0.0,
            "widthMeters": 40.0,
            "lengthMeters": 600.0,
            "localCenterPoint": (0.0, -600.0),
        },
        standard_version=standard_version,
    )
