from app.analysis.ndb_rules import (
    NDB_CONICAL_CLEARANCE,
    NDB_MINIMUM_SEPARATION_METERS,
    is_ndb_supported_category,
)


def test_ndb_supported_categories_include_expected_global_categories() -> None:
    assert is_ndb_supported_category("building_general") is True
    assert is_ndb_supported_category("weather_radar_station") is False


def test_ndb_minimum_separation_uses_expected_defaults() -> None:
    assert NDB_MINIMUM_SEPARATION_METERS["building_general"] == 50.0
    assert NDB_MINIMUM_SEPARATION_METERS["hill"] == 300.0
    assert NDB_MINIMUM_SEPARATION_METERS["power_line_high_voltage_overhead"] == 500.0


def test_ndb_conical_clearance_defaults_are_defined() -> None:
    assert NDB_CONICAL_CLEARANCE["inner_radius_m"] == 50.0
    assert NDB_CONICAL_CLEARANCE["vertical_angle_deg"] == 3.0
