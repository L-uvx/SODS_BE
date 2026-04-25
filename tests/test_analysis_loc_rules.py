import pytest
from shapely.geometry import MultiPolygon, Polygon

from app.analysis.config import PROTECTION_ZONE_BUILDER_DISCRETIZATION
from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule
from app.analysis.rules.protection_zone_helpers import build_geometry_definition
from app.analysis.rules.loc.profile import LocRuleProfile
from app.analysis.rules.loc import (
    LOC_FORWARD_SECTOR_3000M_15M,
    LOC_SITE_PROTECTION,
    LocForwardSector3000m15mRule,
    LocSiteProtectionRule,
)


def test_loc_bound_rule_keeps_protection_zone_and_returns_uniform_result() -> None:
    polygon = Polygon(
        [(0.0, 0.0), (8.0, 0.0), (8.0, 8.0), (0.0, 8.0), (0.0, 0.0)]
    )
    spec = ProtectionZoneSpec(
        station_id=101,
        station_type="LOC",
        rule_code="loc_site_protection",
        rule_name="loc_site_protection",
        zone_code="loc_site_protection",
        zone_name="LOC site protection",
        region_code="default",
        region_name="default",
        local_geometry=MultiPolygon([polygon]),
        geometry_definition={"shapeType": "multipolygon", "coordinates": []},
        vertical_definition={
            "mode": "flat",
            "baseReference": "station",
            "baseHeightMeters": 500.0,
        },
    )

    class _BoundRule(BoundObstacleRule):
        def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
            return AnalysisRuleResult(
                station_id=self.protection_zone.station_id,
                station_type=self.protection_zone.station_type,
                obstacle_id=int(obstacle["obstacleId"]),
                obstacle_name=str(obstacle["name"]),
                raw_obstacle_type=str(obstacle["rawObstacleType"]),
                global_obstacle_category=str(obstacle["globalObstacleCategory"]),
                rule_code=self.protection_zone.rule_code,
                rule_name=self.protection_zone.rule_name,
                zone_code=self.protection_zone.zone_code,
                zone_name=self.protection_zone.zone_name,
                region_code=self.protection_zone.region_code,
                region_name=self.protection_zone.region_name,
                is_applicable=True,
                is_compliant=False,
                message="entered protection zone",
                metrics={"enteredProtectionZone": True},
            )

    rule = _BoundRule(protection_zone=spec)
    result = rule.analyze(
        {
            "obstacleId": 1,
            "name": "Obstacle A",
            "rawObstacleType": "建筑物/构建物",
            "globalObstacleCategory": "building_general",
        }
    )

    assert rule.protection_zone.zone_code == "loc_site_protection"
    assert result.zone_code == "loc_site_protection"
    assert not hasattr(result, "zone_definition")


def test_build_geometry_definition_returns_multipolygon_coordinates() -> None:
    geometry = MultiPolygon(
        [
            Polygon(
                [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
            )
        ]
    )

    geometry_definition = build_geometry_definition(geometry)

    assert geometry_definition["shapeType"] == "multipolygon"
    assert geometry_definition["coordinates"][0][0][0] == [0.0, 0.0]


def test_loc_site_protection_rule_rejects_general_obstacle_entering_zone() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, 400.0),
        "directionDegrees": 0.0,
        "lengthMeters": 400.0,
        "widthMeters": 45.0,
    }
    obstacle = {
        "obstacleId": 1,
        "name": "Obstacle A",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 520.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [10.0, -10.0],
                        [20.0, -10.0],
                        [20.0, 10.0],
                        [10.0, 10.0],
                        [10.0, -10.0],
                    ]
                ]
            ],
        },
    }

    bound_rule = LocSiteProtectionRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )
    result = bound_rule.analyze(obstacle)

    assert result.rule_name == "loc_site_protection"
    assert result.rule_code == "loc_site_protection"
    assert bound_rule.protection_zone.geometry_definition["shapeType"] == "multipolygon"
    assert result.metrics["rectangleLengthMeters"] == 300.0
    assert result.metrics["enteredProtectionZone"] is True
    assert result.is_compliant is False


def test_loc_site_protection_rule_allows_cable_below_station_altitude() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (-250.0, 0.0),
        "directionDegrees": 90.0,
        "lengthMeters": 200.0,
        "widthMeters": 45.0,
    }
    obstacle = {
        "obstacleId": 2,
        "name": "Cable A",
        "rawObstacleType": "电力线缆和通信线缆",
        "globalObstacleCategory": "power_or_communication_cable",
        "topElevation": 499.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-260.0, -5.0],
                        [-250.0, -5.0],
                        [-250.0, 5.0],
                        [-260.0, 5.0],
                        [-260.0, -5.0],
                    ]
                ]
            ],
        },
    }

    result = LocSiteProtectionRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert result.metrics["rectangleLengthMeters"] == 300.0
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["baseHeightMeters"] == 500.0
    assert result.metrics["topElevationMeters"] == 499.0
    assert result.is_compliant is True


def test_loc_site_protection_uses_runway_direction_end_for_rectangle_length() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (-600.0, 0.0),
        "directionDegrees": 90.0,
        "lengthMeters": 400.0,
        "widthMeters": 45.0,
    }
    obstacle = {
        "obstacleId": 3,
        "name": "Obstacle B",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 520.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-390.0, -10.0],
                        [-380.0, -10.0],
                        [-380.0, 10.0],
                        [-390.0, 10.0],
                        [-390.0, -10.0],
                    ]
                ]
            ],
        },
    }

    result = LocSiteProtectionRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert result.metrics["rectangleLengthMeters"] == 400.0
    assert result.metrics["enteredProtectionZone"] is True
    assert result.is_compliant is False


def test_loc_site_protection_uses_runway_end_in_direction_for_rectangle_length() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (-600.0, 0.0),
        "directionDegrees": 90.0,
        "lengthMeters": 400.0,
        "widthMeters": 45.0,
    }
    obstacle = {
        "obstacleId": 31,
        "name": "Obstacle Runway End",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 520.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-390.0, -10.0],
                        [-380.0, -10.0],
                        [-380.0, 10.0],
                        [-390.0, 10.0],
                        [-390.0, -10.0],
                    ]
                ]
            ],
        },
    }

    result = LocSiteProtectionRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert result.metrics["rectangleLengthMeters"] == 400.0
    assert result.metrics["enteredProtectionZone"] is True
    assert result.is_compliant is False


def test_loc_site_protection_uses_reverse_runway_direction_for_rectangle_axis() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 400.0,
        "widthMeters": 45.0,
    }
    obstacle = {
        "obstacleId": 32,
        "name": "Obstacle Reverse Axis",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 520.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-10.0, -390.0],
                        [10.0, -390.0],
                        [10.0, -380.0],
                        [-10.0, -380.0],
                        [-10.0, -390.0],
                    ]
                ]
            ],
        },
    }

    result = LocSiteProtectionRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert result.metrics["rectangleLengthMeters"] == 400.0
    assert result.metrics["enteredProtectionZone"] is True
    assert result.is_compliant is False


def test_loc_site_protection_uses_runway_direction_end_distance_after_reversing_axis() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (-600.0, 0.0),
        "directionDegrees": 90.0,
        "lengthMeters": 400.0,
        "widthMeters": 45.0,
    }
    obstacle = {
        "obstacleId": 33,
        "name": "Obstacle Direction End Distance",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 520.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-790.0, -10.0],
                        [-780.0, -10.0],
                        [-780.0, 10.0],
                        [-790.0, 10.0],
                        [-790.0, -10.0],
                    ]
                ]
            ],
        },
    }

    result = LocSiteProtectionRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert result.metrics["rectangleLengthMeters"] == 400.0
    assert result.metrics["enteredProtectionZone"] is False
    assert result.is_compliant is True


def test_loc_site_protection_uses_config_defined_defaults() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, 400.0),
        "directionDegrees": 180.0,
        "lengthMeters": 400.0,
        "widthMeters": 45.0,
    }
    obstacle = {
        "obstacleId": 1,
        "name": "Obstacle A",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 520.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [10.0, -10.0],
                        [20.0, -10.0],
                        [20.0, 10.0],
                        [10.0, 10.0],
                        [10.0, -10.0],
                    ]
                ]
            ],
        },
    }

    result = LocSiteProtectionRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert LOC_SITE_PROTECTION["circle_radius_m"] == 75.0
    assert LOC_SITE_PROTECTION["rectangle_width_m"] == 120.0
    assert LOC_SITE_PROTECTION["minimum_rectangle_length_m"] == 300.0
    assert "circle_step_degrees" not in LOC_SITE_PROTECTION
    assert (
        result.metrics["rectangleLengthMeters"]
        >= LOC_SITE_PROTECTION["minimum_rectangle_length_m"]
    )
    assert PROTECTION_ZONE_BUILDER_DISCRETIZATION["circle_step_degrees"] > 0.0


def test_loc_site_protection_rule_allows_explicit_circle_step_override() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -400.0),
        "directionDegrees": 0.0,
        "lengthMeters": 400.0,
        "widthMeters": 45.0,
    }
    obstacle = {
        "obstacleId": 4,
        "name": "Obstacle C",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 520.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [10.0, -10.0],
                        [20.0, -10.0],
                        [20.0, 10.0],
                        [10.0, 10.0],
                        [10.0, -10.0],
                    ]
                ]
            ],
        },
    }

    result = LocSiteProtectionRule(circle_step_degrees=5.0).bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert result.metrics["enteredProtectionZone"] is True


def test_loc_site_protection_rule_rejects_zero_circle_step_override() -> None:
    with pytest.raises(ValueError, match="circle_step_degrees"):
        LocSiteProtectionRule(circle_step_degrees=0)


def test_loc_site_protection_rule_rejects_negative_circle_step_override() -> None:
    with pytest.raises(ValueError, match="circle_step_degrees"):
        LocSiteProtectionRule(circle_step_degrees=-1.0)


def test_loc_site_protection_rule_rejects_maximum_circle_step_override() -> None:
    with pytest.raises(ValueError, match="circle_step_degrees"):
        LocSiteProtectionRule(circle_step_degrees=180.0)


def test_loc_forward_sector_rule_rejects_applicable_obstacle_above_height_limit() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
    }
    obstacle = {
        "obstacleId": 5,
        "name": "Obstacle D",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 516.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-20.0, -1040.0],
                        [20.0, -1040.0],
                        [20.0, -1000.0],
                        [-20.0, -1000.0],
                        [-20.0, -1040.0],
                    ]
                ]
            ],
        },
    }

    bound_rule = LocForwardSector3000m15mRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )
    result = bound_rule.analyze(obstacle)

    assert result.rule_name == "loc_forward_sector_3000m_15m"
    assert result.rule_code == "loc_forward_sector_3000m_15m"
    assert bound_rule.protection_zone.geometry_definition["shapeType"] == "multipolygon"
    assert result.region_code == "default"
    assert result.is_applicable is True
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["heightLimitMeters"] == 515.0
    assert result.is_compliant is False


def test_loc_forward_sector_rule_allows_applicable_obstacle_at_height_limit() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
    }
    obstacle = {
        "obstacleId": 6,
        "name": "Obstacle E",
        "rawObstacleType": "航站楼",
        "globalObstacleCategory": "building_terminal",
        "topElevation": 515.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-40.0, -1540.0],
                        [40.0, -1540.0],
                        [40.0, -1500.0],
                        [-40.0, -1500.0],
                        [-40.0, -1540.0],
                    ]
                ]
            ],
        },
    }

    result = LocForwardSector3000m15mRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert result.is_applicable is True
    assert result.metrics["enteredProtectionZone"] is True
    assert result.is_compliant is True


def test_loc_profile_skips_forward_sector_rule_for_non_applicable_obstacle() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
    }
    obstacle = {
        "obstacleId": 7,
        "name": "Obstacle F",
        "rawObstacleType": "山丘",
        "globalObstacleCategory": "hill",
        "topElevation": 999.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-10.0, 800.0],
                        [10.0, 800.0],
                        [10.0, 820.0],
                        [-10.0, 820.0],
                        [-10.0, 800.0],
                    ]
                ]
            ],
        },
    }

    payload = LocRuleProfile().analyze(
        station=station,
        station_point=(0.0, 0.0),
        obstacles=[obstacle],
        runways=[runway],
    )

    assert [result.rule_name for result in payload.rule_results] == ["loc_site_protection"]
    assert {zone.rule_code for zone in payload.protection_zones} == {
        "loc_site_protection",
        "loc_forward_sector_3000m_15m",
    }


def test_loc_rule_profile_returns_rule_results_and_protection_zone_specs() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
    }
    obstacle = {
        "obstacleId": 70,
        "name": "Obstacle Payload",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 516.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-20.0, -1040.0],
                        [20.0, -1040.0],
                        [20.0, -1000.0],
                        [-20.0, -1000.0],
                        [-20.0, -1040.0],
                    ]
                ]
            ],
        },
    }

    payload = LocRuleProfile().analyze(
        station=station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
        runways=[runway],
    )

    assert len(payload.rule_results) == 2
    assert len(payload.protection_zones) == 2
    assert all(
        zone.geometry_definition["shapeType"] == "multipolygon"
        for zone in payload.protection_zones
    )


def test_loc_rule_profile_payload_is_not_iterable() -> None:
    payload = LocRuleProfile().analyze(
        station=type(
            "Station",
            (),
            {
                "id": 101,
                "station_type": "LOC",
                "altitude": 500.0,
                "runway_no": "18",
            },
        )(),
        obstacles=[],
        station_point=(0.0, 0.0),
        runways=[
            {
                "runwayId": 201,
                "runNumber": "18",
                "localCenterPoint": (0.0, -600.0),
                "directionDegrees": 0.0,
                "lengthMeters": 600.0,
                "widthMeters": 45.0,
            }
        ],
    )

    with pytest.raises(TypeError):
        iter(payload)


def test_loc_forward_sector_rule_uses_config_defined_defaults() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
    }
    obstacle = {
        "obstacleId": 8,
        "name": "Obstacle G",
        "rawObstacleType": "机库",
        "globalObstacleCategory": "building_hangar",
        "topElevation": 514.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-10.0, 1200.0],
                        [10.0, 1200.0],
                        [10.0, 1220.0],
                        [-10.0, 1220.0],
                        [-10.0, 1200.0],
                    ]
                ]
            ],
        },
    }

    result = LocForwardSector3000m15mRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert LOC_FORWARD_SECTOR_3000M_15M["radius_m"] == 3000.0
    assert LOC_FORWARD_SECTOR_3000M_15M["half_angle_degrees"] == 10.0
    assert LOC_FORWARD_SECTOR_3000M_15M["height_limit_offset_m"] == 15.0
    assert result.metrics["heightLimitMeters"] == 515.0
    assert result.metrics["elevationAngleDegrees"] == 0.0


def test_loc_forward_sector_rule_respects_sector_angle_boundary() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
    }
    inside_obstacle = {
        "obstacleId": 9,
        "name": "Obstacle H",
        "rawObstacleType": "高压架空输电线路",
        "globalObstacleCategory": "power_line_high_voltage_overhead",
        "topElevation": 520.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [172.0, -1002.0],
                        [192.0, -1002.0],
                        [192.0, -982.0],
                        [172.0, -982.0],
                        [172.0, -1002.0],
                    ]
                ]
            ],
        },
    }
    outside_obstacle = {
        "obstacleId": 10,
        "name": "Obstacle I",
        "rawObstacleType": "高压架空输电线路",
        "globalObstacleCategory": "power_line_high_voltage_overhead",
        "topElevation": 520.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [184.0, -982.0],
                        [204.0, -982.0],
                        [204.0, -962.0],
                        [184.0, -962.0],
                        [184.0, -982.0],
                    ]
                ]
            ],
        },
    }

    bound_rule = LocForwardSector3000m15mRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )
    inside_result = bound_rule.analyze(inside_obstacle)
    outside_result = bound_rule.analyze(outside_obstacle)

    assert inside_result.metrics["enteredProtectionZone"] is True
    assert inside_result.is_compliant is False
    assert outside_result.metrics["enteredProtectionZone"] is False
    assert outside_result.is_compliant is True


def test_loc_forward_sector_rule_uses_reverse_runway_direction() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, 600.0),
        "directionDegrees": 180.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
    }
    obstacle = {
        "obstacleId": 11,
        "name": "Obstacle J",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 520.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-20.0, 1000.0],
                        [20.0, 1000.0],
                        [20.0, 1040.0],
                        [-20.0, 1040.0],
                        [-20.0, 1000.0],
                    ]
                ]
            ],
        },
    }

    result = LocForwardSector3000m15mRule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert result.metrics["enteredProtectionZone"] is True
    assert result.is_compliant is False
