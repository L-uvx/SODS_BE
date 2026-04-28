import importlib

from shapely.geometry import MultiPolygon

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


def test_gp_rule_profile_returns_dual_standard_protection_zones() -> None:
    profile_module = importlib.import_module("app.analysis.rules.gp.profile")

    payload = profile_module.GpRuleProfile().analyze(
        station=_make_gp_station(),
        obstacles=[],
        station_point=(0.0, 0.0),
        runways=[
            {
                "runNumber": "18",
                "directionDegrees": 0.0,
                "widthMeters": 40.0,
                "lengthMeters": 600.0,
                "localCenterPoint": (0.0, -600.0),
            }
        ],
    )

    assert len(payload.protection_zones) == 6
    assert {zone.zone_code for zone in payload.protection_zones} == {
        "gp_site_protection_gb",
        "gp_site_protection_mh",
    }
    assert {zone.region_code for zone in payload.protection_zones} == {"A", "B", "C"}


def test_gp_bound_rule_returns_non_compliant_when_obstacle_enters_zone() -> None:
    region_a_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_a"
    )

    bound_rule = region_a_module.GpSiteProtectionGbRegionARule().bind(
        station=_make_gp_station(station_sub_type="II"),
        shared_context=_make_gp_shared_context(standard_version="GB"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 1,
            "name": "Inside Obstacle",
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

    assert result.is_applicable is True
    assert result.is_compliant is False
    assert result.message == "obstacle enters GP site protection region"
    assert result.metrics["enteredProtectionZone"] is True
    assert result.standards_rule_code == "gp_site_protection_gb_region_a"


def test_gp_bound_rule_returns_cable_specific_standards_rule_code_in_region_a() -> None:
    region_a_module = importlib.import_module(
        "app.analysis.rules.gp.site_protection.region_a"
    )

    bound_rule = region_a_module.GpSiteProtectionGbRegionARule().bind(
        station=_make_gp_station(station_sub_type="II"),
        shared_context=_make_gp_shared_context(standard_version="GB"),
    )

    result = bound_rule.analyze(
        {
            "obstacleId": 3,
            "name": "Cable Obstacle",
            "rawObstacleType": "高压输电线",
            "globalObstacleCategory": "power_line_high_voltage_overhead",
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

    assert result.standards_rule_code == "gp_site_protection_gb_region_a_cable"


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
    assert result.message == "obstacle outside GP site protection region"
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
