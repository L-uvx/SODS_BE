import importlib
import math


def _make_station(**overrides: object) -> object:
    values = {
        "station_sub_type": "II",
        "unit_number": "16",
    }
    values.update(overrides)
    return type("Station", (), values)()


def _make_runway_context(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "localCenterPoint": (100.0, 200.0),
        "directionDegrees": 90.0,
        "lengthMeters": 400.0,
        "maximumAirworthiness": 2,
    }
    values.update(overrides)
    return values


def test_loc_run_area_table_exposes_public_types_and_maps_aircraft() -> None:
    module = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.loc_run_area_table"
    )

    aircraft = module.Aircraft
    table = module.LocRunAreaTable(l_meters=6600.0)

    assert aircraft.H6.value == "H6"
    assert aircraft.H14.value == "H14"
    assert aircraft.H20.value == "H20"
    assert aircraft.H25.value == "H25"
    assert table.resolve_aircraft(maximum_airworthiness=0) is aircraft.H6
    assert table.resolve_aircraft(maximum_airworthiness=1) is aircraft.H14
    assert table.resolve_aircraft(maximum_airworthiness=2) is aircraft.H20
    assert table.resolve_aircraft(maximum_airworthiness=3) is aircraft.H25


def test_loc_run_area_table_resolves_unit_group_and_builds_key() -> None:
    module = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.loc_run_area_table"
    )

    aircraft = module.Aircraft
    table = module.LocRunAreaTable(l_meters=6600.0)

    assert table.resolve_unit_group(unit_number=11) == 1
    assert table.resolve_unit_group(unit_number=12) == 2
    assert table.resolve_unit_group(unit_number=15) == 2
    assert table.resolve_unit_group(unit_number=16) == 3
    assert (
        table.build_key(
            station_sub_type="II",
            aircraft=aircraft.H20,
            unit_number=16,
        )
        == "II_H20_3"
    )


def test_loc_run_area_table_returns_expected_static_and_dynamic_rows() -> None:
    module = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.loc_run_area_table"
    )

    aircraft = module.Aircraft
    table = module.LocRunAreaTable(l_meters=6600.0)

    static_item = table.get_item(
        station_sub_type="I",
        aircraft=aircraft.H14,
        unit_number=11,
    )
    dynamic_item = table.get_item(
        station_sub_type="II",
        aircraft=aircraft.H20,
        unit_number=16,
    )

    assert static_item == module.LocRunAreaTableItem(
        xc_meters=360.0,
        yc_meters=110.0,
        zc_meters=35.0,
        zs1_meters=35.0,
        zs2_meters=35.0,
        y1_meters=90.0,
        y2_meters=90.0,
        xs_meters=500.0,
    )
    assert dynamic_item == module.LocRunAreaTableItem(
        xc_meters=475.0,
        yc_meters=30.0,
        zc_meters=50.0,
        zs1_meters=60.0,
        zs2_meters=160.0,
        y1_meters=60.0 * math.sqrt(2.0),
        y2_meters=60.0 * math.sqrt(2.0),
        xs_meters=1400.0,
    )


def test_loc_run_area_shared_context_computes_l_meters_from_runway_positive_end() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.helpers"
    )
    table_module = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.loc_run_area_table"
    )

    shared_context = helpers.build_loc_run_area_shared_context(
        station=_make_station(station_sub_type="II", unit_number="16"),
        station_point=(50.0, 200.0),
        runway_context=_make_runway_context(),
    )

    assert shared_context is not None
    assert shared_context.runway_end_point == (300.0, 200.0)
    assert shared_context.station_sub_type == "II"
    assert shared_context.aircraft is table_module.Aircraft.H20
    assert shared_context.unit_number == 16
    assert shared_context.l_meters == 650.0


def test_loc_run_area_shared_context_returns_none_for_invalid_airworthiness() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.helpers"
    )

    shared_context = helpers.build_loc_run_area_shared_context(
        station=_make_station(),
        station_point=(50.0, 200.0),
        runway_context=_make_runway_context(maximumAirworthiness=9),
    )

    assert shared_context is None


def test_loc_run_area_shared_context_returns_none_for_non_numeric_airworthiness() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.helpers"
    )

    shared_context = helpers.build_loc_run_area_shared_context(
        station=_make_station(),
        station_point=(50.0, 200.0),
        runway_context=_make_runway_context(maximumAirworthiness="H20"),
    )

    assert shared_context is None


def test_loc_run_area_shared_context_returns_none_for_non_integral_airworthiness() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.helpers"
    )

    shared_context = helpers.build_loc_run_area_shared_context(
        station=_make_station(),
        station_point=(50.0, 200.0),
        runway_context=_make_runway_context(maximumAirworthiness=2.5),
    )

    assert shared_context is None


def test_loc_run_area_shared_context_returns_none_for_non_numeric_unit_number() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.helpers"
    )

    shared_context = helpers.build_loc_run_area_shared_context(
        station=_make_station(unit_number="16A"),
        station_point=(50.0, 200.0),
        runway_context=_make_runway_context(),
    )

    assert shared_context is None
