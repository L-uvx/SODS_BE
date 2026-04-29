import importlib

import pytest


def _make_gp_station(**overrides: object) -> object:
    values = {
        "station_sub_type": "I",
        "distance_v_to_runway": 180.0,
    }
    values.update(overrides)
    return type("Station", (), values)()


def test_gp_run_area_region_a_geometry_matches_csharp_template() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.gp.run_area_protection.helpers"
    )
    shared_context = helpers.build_gp_run_area_shared_context(
        station=_make_gp_station(
            station_sub_type="I",
            distance_v_to_runway=180.0,
        ),
        station_point=(0.0, 0.0),
        runway_context={
            "runNumber": "18",
            "directionDegrees": 0.0,
            "widthMeters": 40.0,
            "lengthMeters": 600.0,
            "localCenterPoint": (0.0, -600.0),
            "maximumAirworthiness": 1,
        },
    )

    assert shared_context is not None
    geometry = helpers.build_gp_run_area_region_a_geometry(shared_context)
    ring = list(geometry.local_geometry.geoms[0].exterior.coords)[:-1]

    assert ring == [
        pytest.approx((39.0, 0.0)),
        pytest.approx((39.0, -329.0)),
        pytest.approx((-160.0, -329.0)),
        pytest.approx((-160.0, 0.0)),
    ]


def test_gp_run_area_region_b_geometry_matches_csharp_template() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.gp.run_area_protection.helpers"
    )
    shared_context = helpers.build_gp_run_area_shared_context(
        station=_make_gp_station(
            station_sub_type="I",
            distance_v_to_runway=180.0,
        ),
        station_point=(0.0, 0.0),
        runway_context={
            "runNumber": "18",
            "directionDegrees": 0.0,
            "widthMeters": 40.0,
            "lengthMeters": 600.0,
            "localCenterPoint": (0.0, -600.0),
            "maximumAirworthiness": 1,
        },
    )

    assert shared_context is not None
    geometry = helpers.build_gp_run_area_region_b_geometry(shared_context)
    ring = list(geometry.local_geometry.geoms[0].exterior.coords)[:-1]

    assert ring == [
        pytest.approx((39.0, 0.0)),
        pytest.approx((39.0, -297.0)),
        pytest.approx((-200.0, -297.0)),
        pytest.approx((-200.0, 0.0)),
    ]


def test_gp_run_area_geometry_mirrors_side_for_negative_distance_v_to_runway() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.gp.run_area_protection.helpers"
    )
    positive_context = helpers.build_gp_run_area_shared_context(
        station=_make_gp_station(distance_v_to_runway=180.0),
        station_point=(0.0, 0.0),
        runway_context={
            "runNumber": "18",
            "directionDegrees": 0.0,
            "widthMeters": 40.0,
            "lengthMeters": 600.0,
            "localCenterPoint": (0.0, -600.0),
            "maximumAirworthiness": 1,
        },
    )
    negative_context = helpers.build_gp_run_area_shared_context(
        station=_make_gp_station(distance_v_to_runway=-180.0),
        station_point=(0.0, 0.0),
        runway_context={
            "runNumber": "18",
            "directionDegrees": 0.0,
            "widthMeters": 40.0,
            "lengthMeters": 600.0,
            "localCenterPoint": (0.0, -600.0),
            "maximumAirworthiness": 1,
        },
    )

    assert positive_context is not None
    assert negative_context is not None

    positive_bounds = helpers.build_gp_run_area_region_a_geometry(
        positive_context
    ).local_geometry.bounds
    negative_bounds = helpers.build_gp_run_area_region_a_geometry(
        negative_context
    ).local_geometry.bounds

    assert positive_bounds == (-160.0, -329.0, 39.0, 0.0)
    assert negative_bounds == (-39.0, -329.0, 160.0, 0.0)
