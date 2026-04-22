from app.analysis.rules.loc import LOC_SITE_PROTECTION, LocSiteProtectionRule


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
        "localCenterPoint": (0.0, 0.0),
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
        "localCenterPoint": (150.0, 0.0),
        "directionDegrees": 90.0,
        "lengthMeters": 400.0,
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
                        [250.0, -5.0],
                        [260.0, -5.0],
                        [260.0, 5.0],
                        [250.0, 5.0],
                        [250.0, -5.0],
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


def test_loc_site_protection_uses_nearest_runway_endpoint_for_rectangle_length() -> None:
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
        "localCenterPoint": (600.0, 0.0),
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
                        [430.0, -10.0],
                        [440.0, -10.0],
                        [440.0, 10.0],
                        [430.0, 10.0],
                        [430.0, -10.0],
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
        "localCenterPoint": (0.0, 150.0),
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
