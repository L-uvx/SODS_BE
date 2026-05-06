import math

from shapely.geometry import MultiPolygon, Polygon

from app.analysis.config import PROTECTION_ZONE_BUILDER_DISCRETIZATION
from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule
import pytest

from app.analysis.rules.ndb import (
    NDB_CONICAL_CLEARANCE,
    NDB_MINIMUM_SEPARATION_METERS,
    NdbConicalClearance3DegRule,
    NdbMinimumDistance150mRule,
    NdbMinimumDistance300mRule,
    NdbMinimumDistance500mRule,
    NdbMinimumDistance50mRule,
    NdbRuleProfile,
    is_ndb_supported_category,
)


class _CountingMinimumRule:
    rule_code = "ndb_minimum_distance_50m"
    rule_name = "ndb_minimum_distance_50m"

    def __init__(self) -> None:
        self.bind_calls = 0

    def bind(self, *, station: object, station_point: tuple[float, float]):
        del station, station_point
        self.bind_calls += 1
        return NdbMinimumDistance50mRule().bind(
            station=type("Station", (), {"id": 1, "station_type": "NDB"})(),
            station_point=(0.0, 0.0),
        )


class _CountingConicalRule:
    rule_code = "ndb_conical_clearance_3deg"
    rule_name = "ndb_conical_clearance_3deg"

    def __init__(self) -> None:
        self.bind_calls = 0

    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
        station_altitude: float | None,
    ):
        del station, station_point, station_altitude
        self.bind_calls += 1
        return NdbConicalClearance3DegRule().bind(
            station=type(
                "Station",
                (),
                {"id": 1, "station_type": "NDB", "altitude": 500.0},
            )(),
            station_point=(0.0, 0.0),
            station_altitude=500.0,
        )


def test_ndb_supported_categories_include_expected_global_categories() -> None:
    assert is_ndb_supported_category("building_general") is True
    assert is_ndb_supported_category("weather_radar_station") is False


def test_protection_zone_spec_keeps_local_geometry_and_discretized_geometry_definition() -> None:
    polygon = Polygon(
        [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
    )
    spec = ProtectionZoneSpec(
        station_id=1,
        station_type="NDB",
        rule_code="ndb_minimum_distance_50m",
        rule_name="ndb_minimum_distance_50m",
        zone_code="ndb_minimum_distance_50m",
        zone_name="NDB 50m minimum distance zone",
        region_code="default",
        region_name="default",
        local_geometry=MultiPolygon([polygon]),
        geometry_definition={
            "shapeType": "multipolygon",
            "coordinates": [
                [
                    [
                        [0.0, 0.0],
                        [10.0, 0.0],
                        [10.0, 10.0],
                        [0.0, 10.0],
                        [0.0, 0.0],
                    ]
                ]
            ],
        },
        vertical_definition={
            "mode": "flat",
            "baseReference": "station",
            "baseHeightMeters": 0.0,
        },
        render_geometry=None,
    )

    assert spec.local_geometry.geom_type == "MultiPolygon"
    assert spec.geometry_definition["shapeType"] == "multipolygon"


def test_bound_rule_keeps_protection_zone_and_returns_result_without_zone_definition() -> None:
    polygon = Polygon(
        [(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0), (0.0, 0.0)]
    )
    spec = ProtectionZoneSpec(
        station_id=1,
        station_type="NDB",
        rule_code="ndb_minimum_distance_50m",
        rule_name="ndb_minimum_distance_50m",
        zone_code="ndb_minimum_distance_50m",
        zone_name="NDB 50m minimum distance zone",
        region_code="default",
        region_name="default",
        local_geometry=MultiPolygon([polygon]),
        geometry_definition={"shapeType": "multipolygon", "coordinates": []},
        vertical_definition={"mode": "flat"},
    )

    class _BoundRule(BoundObstacleRule):
        def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
            return AnalysisRuleResult(
                station_id=self.protection_zone.station_id,
                station_type=self.protection_zone.station_type,
                obstacle_id=int(obstacle["obstacleId"]),
                obstacle_name=str(obstacle["name"]),
                raw_obstacle_type=None,
                global_obstacle_category="building_general",
                rule_code=self.protection_zone.rule_code,
                rule_name=self.protection_zone.rule_name,
                zone_code=self.protection_zone.zone_code,
                zone_name=self.protection_zone.zone_name,
                region_code=self.protection_zone.region_code,
                region_name=self.protection_zone.region_name,
                is_applicable=True,
                is_compliant=True,
                message="ok",
                metrics={"enteredProtectionZone": False},
            )

    rule = _BoundRule(protection_zone=spec)
    result = rule.analyze({"obstacleId": 2, "name": "Obstacle A"})

    assert rule.protection_zone is spec
    assert not hasattr(result, "zone_definition")


def test_ndb_minimum_separation_uses_expected_defaults() -> None:
    assert NDB_MINIMUM_SEPARATION_METERS["building_general"] == 50.0
    assert NDB_MINIMUM_SEPARATION_METERS["hill"] == 300.0
    assert NDB_MINIMUM_SEPARATION_METERS["power_line_high_voltage_110kv"] == 500.0


def test_ndb_conical_clearance_defaults_are_defined() -> None:
    assert NDB_CONICAL_CLEARANCE["inner_radius_m"] == 50.0
    assert NDB_CONICAL_CLEARANCE["vertical_angle_deg"] == 3.0
    assert NDB_CONICAL_CLEARANCE["outer_radius_m"] == 37040.0


def test_ndb_rule_classes_expose_name_and_zone_name() -> None:
    minimum_rule = NdbMinimumDistance50mRule()
    conical_rule = NdbConicalClearance3DegRule()

    assert minimum_rule.rule_name == "ndb_minimum_distance_50m"
    assert minimum_rule.zone_name == "NDB 50米最小间距"
    assert conical_rule.rule_name == "ndb_conical_clearance_3deg"
    assert conical_rule.zone_name == "NDB 50 米外 3°区域"


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

    result_150 = NdbMinimumDistance150mRule().bind(
        station=station,
        station_point=(0.0, 0.0),
    ).analyze({**obstacle, "globalObstacleCategory": "railway_electrified"})
    result_300 = NdbMinimumDistance300mRule().bind(
        station=station,
        station_point=(0.0, 0.0),
    ).analyze(obstacle)
    result_500 = NdbMinimumDistance500mRule().bind(
        station=station,
        station_point=(0.0, 0.0),
    ).analyze(
        {
            **obstacle,
            "rawObstacleType": "高压架空输电线路(110kV)",
            "globalObstacleCategory": "power_line_high_voltage_110kv",
        }
    )

    assert result_150.rule_name == "ndb_minimum_distance_150m"
    assert result_150.rule_code == "ndb_minimum_distance_150m"
    assert result_150.metrics["requiredDistanceMeters"] == 150.0
    assert result_300.rule_name == "ndb_minimum_distance_300m"
    assert result_300.rule_code == "ndb_minimum_distance_300m"
    assert result_300.metrics["requiredDistanceMeters"] == 300.0
    assert result_500.rule_name == "ndb_minimum_distance_500m"
    assert result_500.rule_code == "ndb_minimum_distance_500m"
    assert result_500.metrics["requiredDistanceMeters"] == 500.0


def test_ndb_conical_clearance_rule_returns_uniform_result() -> None:
    station = type("Station", (), {"id": 1, "station_type": "NDB"})()
    obstacle = {
        "obstacleId": 2,
        "name": "Obstacle A",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
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
        "topElevation": 520.0,
    }

    result = NdbConicalClearance3DegRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        station_altitude=500.0,
    ).analyze(obstacle)

    assert result.rule_name == "ndb_conical_clearance_3deg"
    assert result.rule_code == "ndb_conical_clearance_3deg"
    assert result.zone_code == "ndb_conical_clearance_3deg"
    assert result.region_code == "default"
    assert result.metrics["baseHeightMeters"] == 500.0
    assert result.metrics["elevationAngleDegrees"] == 3.0


def test_ndb_rule_profile_returns_minimum_distance_and_conical_results() -> None:
    station = type(
        "Station",
        (),
        {"id": 1, "station_type": "NDB", "altitude": 500.0},
    )()
    obstacle = {
        "obstacleId": 2,
        "name": "Obstacle A",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
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
        "topElevation": 520.0,
    }

    payload = NdbRuleProfile().analyze(
        station=station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
    )

    assert {result.rule_name for result in payload.rule_results} == {
        "ndb_minimum_distance_50m",
        "ndb_conical_clearance_3deg",
    }
    assert {zone.rule_name for zone in payload.protection_zones} == {
        "ndb_minimum_distance_50m",
        "ndb_conical_clearance_3deg",
    }
    assert all(
        zone.geometry_definition["shapeType"] == "multipolygon"
        for zone in payload.protection_zones
    )


def test_ndb_rule_profile_returns_only_matching_minimum_distance_zone_for_hill() -> None:
    station = type(
        "Station",
        (),
        {"id": 1, "station_type": "NDB", "altitude": 500.0},
    )()
    obstacle = {
        "obstacleId": 2,
        "name": "Obstacle Hill",
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
        "topElevation": 520.0,
    }

    payload = NdbRuleProfile().analyze(
        station=station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
    )

    assert {result.rule_name for result in payload.rule_results} == {
        "ndb_minimum_distance_300m",
        "ndb_conical_clearance_3deg",
    }
    assert {zone.rule_name for zone in payload.protection_zones} == {
        "ndb_minimum_distance_300m",
        "ndb_conical_clearance_3deg",
    }


def test_ndb_rule_profile_binds_rules_once_per_station() -> None:
    station = type(
        "Station",
        (),
        {"id": 1, "station_type": "NDB", "altitude": 500.0},
    )()
    obstacles = [
        {
            "obstacleId": 1,
            "name": "Obstacle A",
            "rawObstacleType": "建筑物/构建物",
            "globalObstacleCategory": "building_general",
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [[[[200.0, 0.0], [210.0, 0.0], [210.0, 10.0], [200.0, 10.0], [200.0, 0.0]]]],
            },
            "topElevation": 520.0,
        },
        {
            "obstacleId": 2,
            "name": "Obstacle B",
            "rawObstacleType": "建筑物/构建物",
            "globalObstacleCategory": "building_general",
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [[[[300.0, 0.0], [310.0, 0.0], [310.0, 10.0], [300.0, 10.0], [300.0, 0.0]]]],
            },
            "topElevation": 520.0,
        },
    ]
    profile = NdbRuleProfile()
    counting_minimum_rule = _CountingMinimumRule()
    counting_conical_rule = _CountingConicalRule()
    profile._rules["building_general"] = counting_minimum_rule
    profile._conical_rule = counting_conical_rule

    payload = profile.analyze(
        station=station,
        obstacles=obstacles,
        station_point=(0.0, 0.0),
    )

    assert len(payload.rule_results) == 4
    assert counting_minimum_rule.bind_calls == 1
    assert counting_conical_rule.bind_calls == 1


def test_ndb_rule_profile_payload_is_not_iterable() -> None:
    payload = NdbRuleProfile().analyze(
        station=type(
            "Station",
            (),
            {"id": 1, "station_type": "NDB", "altitude": 500.0},
        )(),
        obstacles=[],
        station_point=(0.0, 0.0),
    )

    with pytest.raises(TypeError):
        iter(payload)


def test_ndb_circle_protection_zone_uses_shared_circle_step_discretization() -> None:
    bound_rule = NdbMinimumDistance50mRule().bind(
        station=type("Station", (), {"id": 1, "station_type": "NDB"})(),
        station_point=(0.0, 0.0),
    )

    expected_segment_count = int(
        math.ceil(
            360.0 / PROTECTION_ZONE_BUILDER_DISCRETIZATION["circle_step_degrees"]
        )
    )
    exterior_ring = bound_rule.protection_zone.geometry_definition["coordinates"][0][0]

    assert len(exterior_ring) == expected_segment_count + 1


def test_ndb_conical_protection_zone_uses_shared_circle_step_discretization() -> None:
    bound_rule = NdbConicalClearance3DegRule().bind(
        station=type(
            "Station",
            (),
            {
                "id": 1,
                "station_type": "NDB",
                "altitude": 500.0,
                "longitude": 104.123456,
                "latitude": 30.123456,
            },
        )(),
        station_point=(0.0, 0.0),
        station_altitude=500.0,
    )

    expected_segment_count = int(
        math.ceil(
            360.0 / PROTECTION_ZONE_BUILDER_DISCRETIZATION["circle_step_degrees"]
        )
    )
    outer_ring = bound_rule.protection_zone.geometry_definition["coordinates"][0][0]
    inner_ring = bound_rule.protection_zone.geometry_definition["coordinates"][0][1]

    assert len(outer_ring) == expected_segment_count + 1
    assert len(inner_ring) == expected_segment_count + 1


def test_ndb_conical_clearance_rule_uses_shared_config_values() -> None:
    rule = NdbConicalClearance3DegRule()

    assert rule.inner_radius_meters == NDB_CONICAL_CLEARANCE["inner_radius_m"]
    assert rule.outer_radius_meters == NDB_CONICAL_CLEARANCE["outer_radius_m"]
    assert rule.elevation_angle_degrees == NDB_CONICAL_CLEARANCE["vertical_angle_deg"]


def test_ndb_minimum_distance_rule_prefers_local_geometry() -> None:
    station = type("Station", (), {"id": 1, "station_type": "NDB"})()
    obstacle = {
        "obstacleId": 2,
        "name": "Obstacle A",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [1000.0, 0.0],
                        [1010.0, 0.0],
                        [1010.0, 10.0],
                        [1000.0, 10.0],
                        [1000.0, 0.0],
                    ]
                ]
            ],
        },
        "localGeometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [20.0, 0.0],
                        [30.0, 0.0],
                        [30.0, 10.0],
                        [20.0, 10.0],
                        [20.0, 0.0],
                    ]
                ]
            ],
        },
    }

    result = NdbMinimumDistance50mRule().bind(
        station=station,
        station_point=(0.0, 0.0),
    ).analyze(obstacle)

    assert result.metrics["actualDistanceMeters"] == 20.0
    assert result.is_compliant is False


def test_ndb_minimum_distance_rule_uses_intersects_boundary_semantics() -> None:
    station = type("Station", (), {"id": 1, "station_type": "NDB"})()
    obstacle = {
        "obstacleId": 2,
        "name": "Obstacle A",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [50.0, 0.0],
                        [60.0, 0.0],
                        [60.0, 10.0],
                        [50.0, 10.0],
                        [50.0, 0.0],
                    ]
                ]
            ],
        },
    }

    result = NdbMinimumDistance50mRule().bind(
        station=station,
        station_point=(0.0, 0.0),
    ).analyze(obstacle)

    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["actualDistanceMeters"] == 50.0
    assert result.is_compliant is False


def test_ndb_conical_clearance_rule_prefers_local_geometry() -> None:
    station = type("Station", (), {"id": 1, "station_type": "NDB"})()
    obstacle = {
        "obstacleId": 2,
        "name": "Obstacle A",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [1000.0, 0.0],
                        [1010.0, 0.0],
                        [1010.0, 10.0],
                        [1000.0, 10.0],
                        [1000.0, 0.0],
                    ]
                ]
            ],
        },
        "localGeometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [20.0, 0.0],
                        [30.0, 0.0],
                        [30.0, 10.0],
                        [20.0, 10.0],
                        [20.0, 0.0],
                    ]
                ]
            ],
        },
        "topElevation": 501.0,
    }

    result = NdbConicalClearance3DegRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        station_altitude=500.0,
    ).analyze(obstacle)

    assert result.metrics["actualDistanceMeters"] == 20.0
    assert result.metrics["enteredProtectionZone"] is False
    assert result.metrics["allowedHeightMeters"] == 500.0
    assert result.is_compliant is True


def test_ndb_conical_clearance_rule_keeps_zero_top_elevation() -> None:
    station = type("Station", (), {"id": 1, "station_type": "NDB"})()
    obstacle = {
        "obstacleId": 2,
        "name": "Obstacle Zero Elevation",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [60.0, 0.0],
                        [70.0, 0.0],
                        [70.0, 10.0],
                        [60.0, 10.0],
                        [60.0, 0.0],
                    ]
                ]
            ],
        },
        "topElevation": 0.0,
    }

    result = NdbConicalClearance3DegRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        station_altitude=500.0,
    ).analyze(obstacle)

    assert result.metrics["topElevationMeters"] == 0.0
    assert result.is_compliant is True


def test_ndb_conical_rule_returns_bound_protection_zone_spec() -> None:
    station = type(
        "Station",
        (),
        {"id": 1, "station_type": "NDB", "altitude": 500.0},
    )()

    bound_rule = NdbConicalClearance3DegRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        station_altitude=500.0,
    )

    assert bound_rule.protection_zone.rule_code == "ndb_conical_clearance_3deg"
    assert bound_rule.protection_zone.geometry_definition["shapeType"] == "multipolygon"
    assert bound_rule.protection_zone.vertical_definition["mode"] == "analytic_surface"
