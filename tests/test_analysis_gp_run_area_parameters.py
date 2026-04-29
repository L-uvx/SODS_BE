import importlib


def _make_gp_station(**overrides: object) -> object:
    values = {
        "station_sub_type": "I",
    }
    values.update(overrides)
    return type("Station", (), values)()


def test_gp_run_area_table_defaults_missing_antenna_type_to_m() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.gp.run_area_protection.helpers"
    )

    assert helpers.resolve_gp_run_area_antenna_type(_make_gp_station()) == "M"


def test_gp_run_area_table_returns_o_branch_when_explicit_antenna_type_present() -> None:
    table_module = importlib.import_module(
        "app.analysis.rules.gp.run_area_protection.gp_run_area_table"
    )
    table = table_module.GpRunAreaTable()

    assert table.get_item(
        station_sub_type="I",
        aircraft=table_module.Aircraft.H14,
        antenna_type="O",
    ) == table_module.GpRunAreaTableItem(
        pc_x_meters=829.0,
        pc_y_meters=39.0,
        ps_x_meters=537.0,
        ps_y_meters=39.0,
    )


def test_gp_run_area_shared_context_returns_none_for_invalid_airworthiness() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.gp.run_area_protection.helpers"
    )

    shared_context = helpers.build_gp_run_area_shared_context(
        station=_make_gp_station(),
        station_point=(0.0, 0.0),
        runway_context={
            "runNumber": "18",
            "directionDegrees": 0.0,
            "widthMeters": 40.0,
            "lengthMeters": 600.0,
            "localCenterPoint": (0.0, -600.0),
            "maximumAirworthiness": 9,
        },
    )

    assert shared_context is None


def test_gp_run_area_shared_context_returns_none_for_non_integral_airworthiness() -> None:
    helpers = importlib.import_module(
        "app.analysis.rules.gp.run_area_protection.helpers"
    )

    shared_context = helpers.build_gp_run_area_shared_context(
        station=_make_gp_station(),
        station_point=(0.0, 0.0),
        runway_context={
            "runNumber": "18",
            "directionDegrees": 0.0,
            "widthMeters": 40.0,
            "lengthMeters": 600.0,
            "localCenterPoint": (0.0, -600.0),
            "maximumAirworthiness": 1.5,
        },
    )

    assert shared_context is None
