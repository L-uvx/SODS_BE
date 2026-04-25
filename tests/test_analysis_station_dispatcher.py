from app.analysis.station_dispatcher import StationAnalysisDispatcher


def test_station_rule_dispatcher_dispatches_loc_and_ndb_by_station_type() -> None:
    dispatcher = StationAnalysisDispatcher()

    loc_station = type(
        "Station",
        (),
        {
            "id": 101,
            "name": "LOC Station",
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    ndb_station = type(
        "Station",
        (),
        {
            "id": 102,
            "name": "NDB Station",
            "station_type": "NDB",
            "altitude": 500.0,
        },
    )()
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
    runway_context = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, 150.0),
        "directionDegrees": 180.0,
        "lengthMeters": 400.0,
        "widthMeters": 45.0,
    }

    loc_payload = dispatcher.analyze_station(
        station=loc_station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
        runways=[runway_context],
    )
    ndb_payload = dispatcher.analyze_station(
        station=ndb_station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
        runways=[],
    )

    assert [result.rule_name for result in loc_payload.rule_results] == [
        "loc_site_protection",
        "loc_forward_sector_3000m_15m",
    ]
    assert len(loc_payload.protection_zones) == 2
    assert {zone.rule_code for zone in loc_payload.protection_zones} == {
        "loc_site_protection",
        "loc_forward_sector_3000m_15m",
    }
    assert {result.rule_name for result in ndb_payload.rule_results} == {
        "ndb_minimum_distance_50m",
        "ndb_conical_clearance_3deg",
    }
    assert {zone.rule_code for zone in ndb_payload.protection_zones} == {
        "ndb_minimum_distance_50m",
        "ndb_minimum_distance_150m",
        "ndb_minimum_distance_300m",
        "ndb_minimum_distance_500m",
        "ndb_conical_clearance_3deg",
    }


def test_station_rule_dispatcher_skips_unsupported_station_type() -> None:
    dispatcher = StationAnalysisDispatcher()
    station = type(
        "Station",
        (),
        {
            "id": 999,
            "name": "Unknown Station",
            "station_type": "nav",
            "altitude": 500.0,
        },
    )()

    payload = dispatcher.analyze_station(
        station=station,
        obstacles=[],
        station_point=(0.0, 0.0),
        runways=[],
    )

    assert payload.rule_results == []
    assert payload.protection_zones == []
