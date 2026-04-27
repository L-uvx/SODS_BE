import importlib
from dataclasses import replace

import pytest


def _make_station(**overrides: object) -> object:
    values = {
        "station_sub_type": "I",
        "unit_number": "11",
    }
    values.update(overrides)
    return type("Station", (), values)()


def _make_runway_context(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "maximumAirworthiness": 1,
    }
    values.update(overrides)
    return values


def _make_shared_context(**overrides: object) -> object:
    helpers = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.helpers"
    )

    shared_context = helpers.build_loc_run_area_shared_context(
        station=_make_station(),
        station_point=(0.0, 0.0),
        runway_context=_make_runway_context(),
    )

    assert shared_context is not None
    if not overrides:
        return shared_context
    return replace(shared_context, **overrides)


def _get_builder(module: object, name: str):
    builder = getattr(module, name, None)
    assert builder is not None, f"missing helper builder: {name}"
    return builder


def _get_ring_points(geometry: object) -> list[tuple[float, float]]:
    return list(geometry.local_geometry.geoms[0].exterior.coords)[:-1]


def test_loc_run_area_region_c_geometry_builds_main_rectangle() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.helpers"
    )
    geometry = _get_builder(helpers, "build_loc_run_area_region_c_geometry")(
        _make_shared_context()
    )

    ring = _get_ring_points(geometry)

    assert len(ring) == 4
    assert ring[0] == pytest.approx((-110.0, 35.0))
    assert ring[1] == pytest.approx((-110.0, -360.0))
    assert ring[2] == pytest.approx((110.0, -360.0))
    assert ring[3] == pytest.approx((110.0, 35.0))


def test_loc_run_area_region_b_geometry_builds_backward_rectangle() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.helpers"
    )
    table_item = replace(
        _make_shared_context().table_item,
        zc_meters=35.0,
        yc_meters=110.0,
        zs1_meters=55.0,
    )
    geometry = _get_builder(helpers, "build_loc_run_area_region_b_geometry")(
        _make_shared_context(table_item=table_item)
    )

    ring = _get_ring_points(geometry)

    assert len(ring) == 4
    assert ring[0] == pytest.approx((-110.0, 55.0))
    assert ring[1] == pytest.approx((-110.0, 35.0))
    assert ring[2] == pytest.approx((110.0, 35.0))
    assert ring[3] == pytest.approx((110.0, 55.0))


def test_loc_run_area_region_a_geometry_uses_fixed_120m_width() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.helpers"
    )
    table_item = replace(
        _make_shared_context().table_item,
        zs1_meters=55.0,
        zs2_meters=80.0,
    )
    geometry = _get_builder(helpers, "build_loc_run_area_region_a_geometry")(
        _make_shared_context(table_item=table_item)
    )

    ring = _get_ring_points(geometry)
    xs = [point[0] for point in ring]
    ys = [point[1] for point in ring]

    assert len(ring) == 4
    assert min(xs) == pytest.approx(-60.0)
    assert max(xs) == pytest.approx(60.0)
    assert min(ys) == pytest.approx(55.0)
    assert max(ys) == pytest.approx(80.0)
    assert ring[0] == pytest.approx((-60.0, 80.0))
    assert ring[1] == pytest.approx((-60.0, 55.0))
    assert ring[2] == pytest.approx((60.0, 55.0))
    assert ring[3] == pytest.approx((60.0, 80.0))


def test_loc_run_area_region_d_geometry_builds_short_case_when_xs_within_1500m() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.helpers"
    )
    geometry = _get_builder(helpers, "build_loc_run_area_region_d_geometry")(
        _make_shared_context()
    )

    ring = _get_ring_points(geometry)

    assert len(ring) == 4
    assert ring[0] == pytest.approx((-110.0, 35.0))
    assert ring[1] == pytest.approx((-90.0, -500.0))
    assert ring[2] == pytest.approx((90.0, -500.0))
    assert ring[3] == pytest.approx((110.0, 35.0))


def test_loc_run_area_region_d_geometry_builds_middle_case_when_xs_within_1800m() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.helpers"
    )
    table_item = replace(
        _make_shared_context().table_item,
        xs_meters=1700.0,
        y1_meters=120.0,
        y2_meters=180.0,
    )
    geometry = _get_builder(helpers, "build_loc_run_area_region_d_geometry")(
        _make_shared_context(table_item=table_item)
    )

    ring = _get_ring_points(geometry)

    assert len(ring) == 6
    assert ring[0] == pytest.approx((-110.0, 35.0))
    assert ring[1] == pytest.approx((-120.0, -1500.0))
    assert ring[2] == pytest.approx((-180.0, -1700.0))
    assert ring[3] == pytest.approx((180.0, -1700.0))
    assert ring[4] == pytest.approx((120.0, -1500.0))
    assert ring[5] == pytest.approx((110.0, 35.0))


def test_loc_run_area_region_d_geometry_builds_long_case_with_300m_platform() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.helpers"
    )
    table_item = replace(
        _make_shared_context().table_item,
        xs_meters=2200.0,
        y1_meters=120.0,
        y2_meters=180.0,
    )
    geometry = _get_builder(helpers, "build_loc_run_area_region_d_geometry")(
        _make_shared_context(table_item=table_item)
    )

    ring = _get_ring_points(geometry)

    assert len(ring) == 8
    assert ring[0] == pytest.approx((-110.0, 35.0))
    assert ring[1] == pytest.approx((-120.0, -1500.0))
    assert ring[2] == pytest.approx((-180.0, -1900.0))
    assert ring[3] == pytest.approx((-180.0, -2200.0))
    assert ring[4] == pytest.approx((180.0, -2200.0))
    assert ring[5] == pytest.approx((180.0, -1900.0))
    assert ring[6] == pytest.approx((120.0, -1500.0))
    assert ring[7] == pytest.approx((110.0, 35.0))
