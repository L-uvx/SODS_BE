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
            "station_sub_type": "II",
            "unit_number": "16",
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
        "rawObstacleType": "车辆/航空器/机械",
        "globalObstacleCategory": "vehicle_or_aircraft_or_machine",
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
        "maximumAirworthiness": 2,
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
        "loc_run_area_protection_region_a",
        "loc_run_area_protection_region_b",
        "loc_run_area_protection_region_c",
        "loc_run_area_protection_region_d",
    ]
    assert len(loc_payload.protection_zones) == 5
    assert {zone.rule_code for zone in loc_payload.protection_zones} == {
        "loc_site_protection",
        "loc_run_area_protection_region_a",
        "loc_run_area_protection_region_b",
        "loc_run_area_protection_region_c",
        "loc_run_area_protection_region_d",
    }
    assert {result.rule_name for result in ndb_payload.rule_results} == {
        "ndb_conical_clearance_3deg",
    }
    assert {zone.rule_code for zone in ndb_payload.protection_zones} == {
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


def test_station_rule_dispatcher_dispatches_gp_by_station_type() -> None:
    dispatcher = StationAnalysisDispatcher()
    gp_station = type(
        "Station",
        (),
        {
            "id": 103,
            "name": "GP Station",
            "station_type": "GP",
            "altitude": 500.0,
            "runway_no": "18",
            "station_sub_type": "II",
            "distance_v_to_runway": 180.0,
        },
    )()
    obstacle = {
        "obstacleId": 1,
        "name": "Obstacle A",
        "rawObstacleType": "车辆/航空器/机械",
        "globalObstacleCategory": "vehicle_or_aircraft_or_machine",
        "topElevation": 520.0,
        "localGeometry": {
            "type": "Point",
            "coordinates": [0.0, -200.0],
        },
        "geometry": {
            "type": "Point",
            "coordinates": [0.0, -200.0],
        },
    }
    runway_context = {
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 40.0,
        "maximumAirworthiness": 1,
    }

    payload = dispatcher.analyze_station(
        station=gp_station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
        runways=[runway_context],
    )

    assert len(payload.protection_zones) == 9
    assert {zone.zone_code for zone in payload.protection_zones} == {
        "gp_elevation_restriction_1deg",
        "gp_site_protection_gb",
        "gp_site_protection_mh",
        "gp_run_area_protection",
    }
    assert {result.rule_name for result in payload.rule_results} == {
        "gp_elevation_restriction_1deg",
        "gp_site_protection_gb_region_a",
        "gp_site_protection_gb_region_b",
        "gp_site_protection_gb_region_c",
        "gp_site_protection_mh_region_a",
        "gp_site_protection_mh_region_b",
        "gp_site_protection_mh_region_c",
        "gp_run_area_protection_region_a",
        "gp_run_area_protection_region_b",
    }


def test_station_rule_dispatcher_dispatches_mb_by_station_type() -> None:
    dispatcher = StationAnalysisDispatcher()
    mb_station = type(
        "Station",
        (),
        {
            "id": 104,
            "name": "MB Station",
            "station_type": "MB",
            "longitude": 120.0,
            "latitude": 30.0,
            "altitude": 500.0,
            "runway_no": "18",
        },
    )()
    runway_context = {
        "runNumber": "18",
        "directionDegrees": 180.0,
    }

    payload = dispatcher.analyze_station(
        station=mb_station,
        obstacles=[],
        station_point=(0.0, 0.0),
        runways=[runway_context],
    )

    assert payload.rule_results == []
    assert len(payload.protection_zones) == 4
    assert [zone.region_code for zone in payload.protection_zones] == [
        "I",
        "II",
        "III",
        "IV",
    ]
    assert {zone.zone_code for zone in payload.protection_zones} == {
        "mb_site_protection",
    }


def test_dispatcher_handles_vor_station() -> None:
    """dispatcher 按 station_type="VOR" 分发，无障碍物时返回空 rule_results 与绑定保护区。"""
    dispatcher = StationAnalysisDispatcher()
    station = type(
        "Station",
        (),
        {
            "id": 201,
            "name": "TEST_VOR",
            "station_type": "VOR",
            "longitude": 120.0,
            "latitude": 30.0,
            "altitude": 10.0,
            "b_to_center_distance": 3.0,
            "reflection_diameter": 30.0,
            "b_antenna_h": 2.0,
            "reflection_net_hag": 5.0,
            "coverage_radius": 1800.0,
        },
    )()

    payload = dispatcher.analyze_station(
        station=station,
        obstacles=[],
        station_point=(0.0, 0.0),
        runways=[],
    )
    assert payload.rule_results == []
    assert len(payload.protection_zones) == 2
    assert {zone.rule_code for zone in payload.protection_zones} == {
        "vor_reflector_mask_area",
        "vor_300_outside_2_5_deg",
    }


def test_dispatcher_vor_with_obstacle() -> None:
    """dispatcher 按 station_type="VOR" 分发，有障碍物时返回分析结果与保护区。"""
    dispatcher = StationAnalysisDispatcher()
    station = type(
        "Station",
        (),
        {
            "id": 201,
            "name": "TEST_VOR",
            "station_type": "VOR",
            "longitude": 120.0,
            "latitude": 30.0,
            "altitude": 10.0,
            "b_to_center_distance": 3.0,
            "reflection_diameter": 30.0,
            "b_antenna_h": 2.0,
            "reflection_net_hag": 5.0,
            "coverage_radius": 1800.0,
        },
    )()

    obstacle = {
        "obstacleId": 1,
        "name": "test_obs",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "geometry": {"type": "Point", "coordinates": [120.0, 30.0]},
        "localGeometry": {"type": "Point", "coordinates": [100.0, 200.0]},
        "topElevation": 0.0,
    }

    payload = dispatcher.analyze_station(
        station=station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
        runways=[],
    )
    assert len(payload.rule_results) == 5
    assert len(payload.protection_zones) == 5
    assert {result.rule_code for result in payload.rule_results} == {
        "vor_reflector_mask_area",
        "vor_100m_datum_plane",
        "vor_200m_datum_plane",
        "vor_200_300_1_5_deg",
        "vor_300_outside_2_5_deg",
    }
    assert {zone.rule_code for zone in payload.protection_zones} == {
        "vor_reflector_mask_area",
        "vor_100m_datum_plane",
        "vor_200m_datum_plane",
        "vor_200_300_1_5_deg",
        "vor_300_outside_2_5_deg",
    }


def test_station_rule_dispatcher_dispatches_vhf_by_station_type() -> None:
    dispatcher = StationAnalysisDispatcher()
    vhf_station = type(
        "Station",
        (),
        {
            "id": 105,
            "name": "VHF Station",
            "station_type": "VHF",
            "longitude": 120.0,
            "latitude": 30.0,
            "altitude": 500.0,
        },
    )()
    obstacle = {
        "obstacleId": 1,
        "name": "Obstacle A",
        "rawObstacleType": "调频广播1kW（含）以下",
        "globalObstacleCategory": "fm_broadcast_1kw_below",
        "topElevation": 520.0,
        "localGeometry": {
            "type": "Point",
            "coordinates": [900.0, 0.0],
        },
        "geometry": {
            "type": "Point",
            "coordinates": [900.0, 0.0],
        },
    }

    payload = dispatcher.analyze_station(
        station=vhf_station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
        runways=[],
    )

    assert len(payload.rule_results) == 1
    assert len(payload.protection_zones) == 1
    assert {result.rule_code for result in payload.rule_results} == {
        "vhf_minimum_distance_1km",
    }
    assert {zone.rule_code for zone in payload.protection_zones} == {
        "vhf_minimum_distance_1km",
    }


def test_station_rule_dispatcher_dispatches_hf_by_station_type() -> None:
    dispatcher = StationAnalysisDispatcher()
    hf_station = type(
        "Station",
        (),
        {
            "id": 106,
            "name": "HF Station",
            "station_type": "HF",
            "longitude": 120.0,
            "latitude": 30.0,
            "altitude": 500.0,
        },
    )()
    obstacle = {
        "obstacleId": 1,
        "name": "Obstacle A",
        "rawObstacleType": "工、科、医射频设备",
        "globalObstacleCategory": "industrial_scientific_medical_rf_equipment",
        "topElevation": 520.0,
        "localGeometry": {
            "type": "Point",
            "coordinates": [4900.0, 0.0],
        },
        "geometry": {
            "type": "Point",
            "coordinates": [4900.0, 0.0],
        },
    }

    payload = dispatcher.analyze_station(
        station=hf_station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
        runways=[],
    )

    assert len(payload.rule_results) == 1
    assert len(payload.protection_zones) == 1
    assert {result.rule_code for result in payload.rule_results} == {
        "hf_minimum_distance_5km",
    }
    assert {zone.rule_code for zone in payload.protection_zones} == {
        "hf_minimum_distance_5km",
    }


def test_station_rule_dispatcher_dispatches_ads_b_by_station_type() -> None:
    dispatcher = StationAnalysisDispatcher()
    ads_b_station = type(
        "Station",
        (),
        {
            "id": 301,
            "name": "ADS-B Station",
            "station_type": "ADS_B",
            "longitude": 120.0,
            "latitude": 30.0,
            "altitude": 500.0,
        },
    )()
    obstacle = {
        "obstacleId": 1,
        "name": "Obstacle A",
        "rawObstacleType": "道路/公路",
        "globalObstacleCategory": "road",
        "topElevation": 520.0,
        "localGeometry": {
            "type": "Point",
            "coordinates": [600.0, 0.0],
        },
        "geometry": {
            "type": "Point",
            "coordinates": [120.0, 30.0],
        },
    }

    payload = dispatcher.analyze_station(
        station=ads_b_station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
        runways=[],
    )

    assert [result.rule_code for result in payload.rule_results] == [
        "adsb_minimum_distance_0_7km",
    ]
    assert [result.standards_rule_code for result in payload.rule_results] == [
        "adsb_minimum_distance_0_7km_road",
    ]
    assert [zone.rule_code for zone in payload.protection_zones] == [
        "adsb_minimum_distance_0_7km",
    ]


def test_station_rule_dispatcher_dispatches_radar_by_station_type() -> None:
    dispatcher = StationAnalysisDispatcher()
    radar_station = type(
        "Station",
        (),
        {
            "id": 105,
            "name": "RADAR Station",
            "station_type": "RADAR",
            "longitude": 120.0,
            "latitude": 30.0,
            "altitude": 500.0,
            "station_sub_type": "PSR",
        },
    )()
    obstacles = [
        {
            "obstacleId": 1,
            "name": "Building A",
            "rawObstacleType": "建筑物/构筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 520.0,
            "localGeometry": {"type": "Point", "coordinates": [300.0, 0.0]},
            "geometry": {"type": "Point", "coordinates": [120.0, 30.0]},
        },
        {
            "obstacleId": 2,
            "name": "Reflector A",
            "rawObstacleType": "大型旋转反射体",
            "globalObstacleCategory": "large_rotating_reflector",
            "topElevation": 530.0,
            "localGeometry": {"type": "Point", "coordinates": [15000.0, 0.0]},
            "geometry": {"type": "Point", "coordinates": [120.1, 30.1]},
        },
    ]

    payload = dispatcher.analyze_station(
        station=radar_station,
        obstacles=obstacles,
        station_point=(0.0, 0.0),
        runways=[],
    )

    assert {result.rule_code for result in payload.rule_results} == {
        "radar_minimum_distance_460m",
        "radar_rotating_reflector_16km",
    }
    assert {result.zone_code for result in payload.rule_results} == {
        "radar_minimum_distance_zone_460m",
        "radar_rotating_reflector_zone_16km",
    }
    assert {result.standards_rule_code for result in payload.rule_results} == {
        "radar_minimum_distance_460m_standard",
        "radar_rotating_reflector_16km_standard",
    }
    assert {zone.zone_code for zone in payload.protection_zones} == {
        "radar_minimum_distance_zone_460m",
        "radar_rotating_reflector_zone_16km",
    }


def test_station_rule_dispatcher_dispatches_weather_radar_by_station_type() -> None:
    dispatcher = StationAnalysisDispatcher()
    station = type(
        "Station",
        (),
        {
            "id": 106,
            "name": "Weather Radar Station",
            "station_type": "WeatherRadar",
            "longitude": 120.0,
            "latitude": 30.0,
            "altitude": 10.0,
            "antenna_hag": 20.0,
            "coverage_radius": 1800.0,
        },
    )()
    obstacles = [
        {
            "obstacleId": 1,
            "name": "Building A",
            "rawObstacleType": "建筑物/构筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 60.0,
            "localGeometry": {"type": "Point", "coordinates": [1000.0, 0.0]},
            "geometry": {"type": "Point", "coordinates": [120.0, 30.0]},
        },
        {
            "obstacleId": 2,
            "name": "FM A",
            "rawObstacleType": "调频广播1kW（含）以下",
            "globalObstacleCategory": "fm_broadcast_1kw_below",
            "topElevation": 20.0,
            "localGeometry": {"type": "Point", "coordinates": [700.0, 0.0]},
            "geometry": {"type": "Point", "coordinates": [120.1, 30.1]},
        },
    ]

    payload = dispatcher.analyze_station(
        station=station,
        obstacles=obstacles,
        station_point=(0.0, 0.0),
        runways=[],
    )

    assert {result.rule_code for result in payload.rule_results} == {
        "weather_radar_minimum_distance_450m",
        "weather_radar_elevation_angle_1deg",
        "weather_radar_minimum_distance_800m",
    }
    assert {zone.zone_code for zone in payload.protection_zones} == {
        "weather_radar_minimum_distance_450m",
        "weather_radar_minimum_distance_800m",
        "weather_radar_elevation_angle_1deg",
    }


def test_station_rule_dispatcher_dispatches_wind_radar_by_station_type() -> None:
    dispatcher = StationAnalysisDispatcher()
    station = type(
        "Station",
        (),
        {
            "id": 107,
            "name": "Wind Radar Station",
            "station_type": "WindRadar",
            "longitude": 120.0,
            "latitude": 30.0,
            "altitude": 10.0,
            "antenna_hag": 20.0,
            "coverage_radius": 1800.0,
        },
    )()
    obstacles = [
        {
            "obstacleId": 1,
            "name": "Building A",
            "rawObstacleType": "建筑物/构筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 400.0,
            "localGeometry": {"type": "Point", "coordinates": [1000.0, 0.0]},
            "geometry": {"type": "Point", "coordinates": [120.0, 30.0]},
        }
    ]

    payload = dispatcher.analyze_station(
        station=station,
        obstacles=obstacles,
        station_point=(0.0, 0.0),
        runways=[],
    )

    assert {result.rule_code for result in payload.rule_results} == {
        "wind_radar_elevation_angle_15deg",
    }
    assert {zone.zone_code for zone in payload.protection_zones} == {
        "wind_radar_elevation_angle_15deg",
    }


def test_station_rule_dispatcher_dispatches_surface_detection_radar_by_station_type() -> None:
    dispatcher = StationAnalysisDispatcher()
    radar_station = type(
        "Station",
        (),
        {
            "id": 106,
            "name": "Surface Detection RADAR Station",
            "station_type": "Surface_Detection_Radar",
            "longitude": 120.0,
            "latitude": 30.0,
            "altitude": 500.0,
            "station_sub_type": "PSR",
            "runway_no": "18",
        },
    )()
    obstacles = [
        {
            "obstacleId": 1,
            "name": "Building A",
            "rawObstacleType": "建筑物/构筑物",
            "globalObstacleCategory": "building_general",
            "topElevation": 520.0,
            "localGeometry": {"type": "Point", "coordinates": [0.0, 150.0]},
            "geometry": {"type": "Point", "coordinates": [120.0, 30.0]},
        },
    ]
    runways = [
        {
            "runNumber": "18",
            "localCenterPoint": (0.0, 300.0),
            "directionDegrees": 180.0,
            "lengthMeters": 100.0,
            "widthMeters": 45.0,
        }
    ]

    payload = dispatcher.analyze_station(
        station=radar_station,
        obstacles=obstacles,
        station_point=(0.0, 0.0),
        runways=runways,
    )

    assert {result.rule_code for result in payload.rule_results} == {
        "surface_detection_radar_runway_triangle",
        "radar_minimum_distance_460m",
    }
