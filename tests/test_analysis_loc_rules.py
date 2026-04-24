import pytest

from app.analysis.config import PROTECTION_ZONE_BUILDER_DISCRETIZATION
from app.analysis.rules.loc.profile import LocRuleProfile
from app.analysis.rules.loc import (
    LOC_FORWARD_SECTOR_3000M_15M,
    LOC_SITE_PROTECTION,
    LocForwardSector3000m15mRule,
    LocSiteProtectionRule,
)


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

    result = LocSiteProtectionRule().analyze(
        station=station,
        obstacle=obstacle,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

    assert result.rule_name == "loc_site_protection"
    assert result.zone_definition["shape"] == "multipolygon"
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

    result = LocSiteProtectionRule().analyze(
        station=station,
        obstacle=obstacle,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

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

    result = LocSiteProtectionRule().analyze(
        station=station,
        obstacle=obstacle,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

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

    result = LocSiteProtectionRule().analyze(
        station=station,
        obstacle=obstacle,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

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

    result = LocSiteProtectionRule().analyze(
        station=station,
        obstacle=obstacle,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

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

    result = LocSiteProtectionRule().analyze(
        station=station,
        obstacle=obstacle,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

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

    result = LocSiteProtectionRule().analyze(
        station=station,
        obstacle=obstacle,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

    assert LOC_SITE_PROTECTION["circle_radius_m"] == 75.0
    assert LOC_SITE_PROTECTION["rectangle_width_m"] == 120.0
    assert LOC_SITE_PROTECTION["minimum_rectangle_length_m"] == 300.0
    assert "circle_step_degrees" not in LOC_SITE_PROTECTION
    assert (
        result.zone_definition["circle_radius_m"]
        == LOC_SITE_PROTECTION["circle_radius_m"]
    )
    assert (
        result.zone_definition["rectangle_width_m"]
        == LOC_SITE_PROTECTION["rectangle_width_m"]
    )
    assert (
        result.metrics["rectangleLengthMeters"]
        >= LOC_SITE_PROTECTION["minimum_rectangle_length_m"]
    )
    assert (
        result.zone_definition["circle_step_degrees"]
        == PROTECTION_ZONE_BUILDER_DISCRETIZATION["circle_step_degrees"]
    )


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

    result = LocSiteProtectionRule(circle_step_degrees=5.0).analyze(
        station=station,
        obstacle=obstacle,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

    assert result.zone_definition["circle_step_degrees"] == 5.0


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

    result = LocForwardSector3000m15mRule().analyze(
        station=station,
        obstacle=obstacle,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

    assert result.rule_name == "loc_forward_sector_3000m_15m"
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

    result = LocForwardSector3000m15mRule().analyze(
        station=station,
        obstacle=obstacle,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

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

    results = LocRuleProfile().analyze(
        station=station,
        station_point=(0.0, 0.0),
        obstacles=[obstacle],
        runways=[runway],
    )

    assert [result.rule_name for result in results] == ["loc_site_protection"]


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

    result = LocForwardSector3000m15mRule().analyze(
        station=station,
        obstacle=obstacle,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

    assert LOC_FORWARD_SECTOR_3000M_15M["radius_m"] == 3000.0
    assert LOC_FORWARD_SECTOR_3000M_15M["half_angle_degrees"] == 10.0
    assert LOC_FORWARD_SECTOR_3000M_15M["height_limit_offset_m"] == 15.0
    assert result.zone_definition["shape"] == "sector"
    assert result.zone_definition["min_radius_m"] == 0.0
    assert result.zone_definition["max_radius_m"] == 3000.0
    assert result.zone_definition["start_azimuth_deg"] == 170.0
    assert result.zone_definition["end_azimuth_deg"] == 190.0
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

    inside_result = LocForwardSector3000m15mRule().analyze(
        station=station,
        obstacle=inside_obstacle,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )
    outside_result = LocForwardSector3000m15mRule().analyze(
        station=station,
        obstacle=outside_obstacle,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

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

    result = LocForwardSector3000m15mRule().analyze(
        station=station,
        obstacle=obstacle,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

    assert result.zone_definition["start_azimuth_deg"] == 350.0
    assert result.zone_definition["end_azimuth_deg"] == 10.0
    assert result.metrics["enteredProtectionZone"] is True
    assert result.is_compliant is False
