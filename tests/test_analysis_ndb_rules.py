from app.analysis.rules.ndb import (
    NDB_CONICAL_CLEARANCE,
    NDB_MINIMUM_SEPARATION_METERS,
    NdbConicalClearance3DegRule,
    NdbMinimumDistance150mRule,
    NdbMinimumDistance300mRule,
    NdbMinimumDistance500mRule,
    NdbMinimumDistance50mRule,
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
    assert NDB_CONICAL_CLEARANCE["outer_radius_m"] == 37040.0


def test_ndb_rule_classes_expose_name_and_zone_definition() -> None:
    minimum_rule = NdbMinimumDistance50mRule()
    conical_rule = NdbConicalClearance3DegRule()

    assert minimum_rule.rule_name == "ndb_minimum_distance_50m"
    assert minimum_rule.zone_definition["shape"] == "circle"
    assert minimum_rule.zone_definition["radius_m"] == 50.0
    assert conical_rule.rule_name == "ndb_conical_clearance_3deg"
    assert conical_rule.zone_definition["shape"] == "radial_band"
    assert conical_rule.zone_definition["min_radius_m"] == 50.0
    assert conical_rule.zone_definition["max_radius_m"] == 37040.0


def test_ndb_minimum_distance_rules_return_uniform_results() -> None:
    station = type("Station", (), {"id": 1, "station_type": "NDB"})()
    obstacle = {
        "obstacleId": 2,
        "name": "Obstacle A",
        "rawObstacleType": "山丘",
        "globalObstacleCategory": "hill",
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [200.0, 0.0],
                        [210.0, 0.0],
                        [210.0, 10.0],
                        [200.0, 10.0],
                        [200.0, 0.0],
                    ]
                ]
            ],
        },
    }

    result_150 = NdbMinimumDistance150mRule().analyze(
        station=station,
        obstacle={**obstacle, "globalObstacleCategory": "railway_electrified"},
        station_point=(0.0, 0.0),
    )
    result_300 = NdbMinimumDistance300mRule().analyze(
        station=station,
        obstacle=obstacle,
        station_point=(0.0, 0.0),
    )
    result_500 = NdbMinimumDistance500mRule().analyze(
        station=station,
        obstacle={
            **obstacle,
            "rawObstacleType": "高压架空输电线路",
            "globalObstacleCategory": "power_line_high_voltage_overhead",
        },
        station_point=(0.0, 0.0),
    )

    assert result_150.rule_name == "ndb_minimum_distance_150m"
    assert result_150.metrics["requiredDistanceMeters"] == 150.0
    assert result_300.rule_name == "ndb_minimum_distance_300m"
    assert result_300.metrics["requiredDistanceMeters"] == 300.0
    assert result_500.rule_name == "ndb_minimum_distance_500m"
    assert result_500.metrics["requiredDistanceMeters"] == 500.0
