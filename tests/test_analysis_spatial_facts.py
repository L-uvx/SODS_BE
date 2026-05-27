import math
from types import SimpleNamespace

from app.analysis.obstacle_projection import (
    create_station_projector,
    project_geometry_to_projector,
    project_obstacle_for_station,
)
from app.analysis.spatial_facts import build_airport_spatial_facts


def test_build_airport_spatial_facts_returns_station_local_coordinates() -> None:
    airport = SimpleNamespace(id=1, name="Airport A", longitude=104.0, latitude=30.0)
    station = SimpleNamespace(
        id=101,
        name="Station A",
        longitude=104.001,
        latitude=30.0,
        altitude=498.2,
    )
    obstacle = SimpleNamespace(
        id=201,
        name="Obstacle A",
        raw_payload={
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [104.0, 30.0],
                            [104.0005, 30.0],
                            [104.0005, 30.0005],
                            [104.0, 30.0005],
                            [104.0, 30.0],
                        ]
                    ]
                ],
            }
        },
    )
    context = SimpleNamespace(
        airport=airport,
        runways=[],
        stations=[station],
        obstacles=[obstacle],
    )

    facts = build_airport_spatial_facts(context)

    assert facts["airportId"] == 1
    assert facts["stationCount"] == 1
    assert facts["stations"][0]["stationId"] == 101
    assert facts["stations"][0]["localX"] > 0


def test_build_airport_spatial_facts_skips_station_without_coordinates() -> None:
    airport = SimpleNamespace(id=1, name="Airport A", longitude=104.0, latitude=30.0)
    station = SimpleNamespace(
        id=102,
        name="Station B",
        longitude=None,
        latitude=None,
        altitude=500.0,
    )
    obstacle = SimpleNamespace(
        id=201,
        name="Obstacle A",
        raw_payload={
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [104.0, 30.0],
                            [104.0005, 30.0],
                            [104.0005, 30.0005],
                            [104.0, 30.0005],
                            [104.0, 30.0],
                        ]
                    ]
                ],
            }
        },
    )
    context = SimpleNamespace(
        airport=airport,
        runways=[],
        stations=[station],
        obstacles=[obstacle],
    )

    facts = build_airport_spatial_facts(context)

    assert facts["stationCount"] == 1
    assert facts["stations"] == []


def test_build_airport_spatial_facts_includes_global_obstacle_category() -> None:
    airport = SimpleNamespace(id=1, name="Airport A", longitude=104.0, latitude=30.0)
    obstacle = SimpleNamespace(
        id=201,
        name="Obstacle A",
        obstacle_type="建筑物/构建物",
        raw_payload={
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [104.0, 30.0],
                            [104.0005, 30.0],
                            [104.0005, 30.0005],
                            [104.0, 30.0005],
                            [104.0, 30.0],
                        ]
                    ]
                ],
            }
        },
    )
    context = SimpleNamespace(
        airport=airport,
        runways=[],
        stations=[],
        obstacles=[obstacle],
    )

    facts = build_airport_spatial_facts(context)

    assert facts["obstacles"][0]["globalObstacleCategory"] == "building_general"


def test_build_airport_spatial_facts_keeps_geometry_empty_when_only_local_geometry_exists() -> None:
    airport = SimpleNamespace(id=1, name="Airport A", longitude=104.0, latitude=30.0)
    local_geometry = {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [
                    [10.0, 20.0],
                    [20.0, 20.0],
                    [20.0, 30.0],
                    [10.0, 30.0],
                    [10.0, 20.0],
                ]
            ]
        ],
    }
    obstacle = SimpleNamespace(
        id=201,
        name="Obstacle A",
        obstacle_type="建筑物/构建物",
        top_elevation=520.0,
        raw_payload={"localGeometry": local_geometry},
    )
    context = SimpleNamespace(
        airport=airport,
        runways=[],
        stations=[],
        obstacles=[obstacle],
    )

    facts = build_airport_spatial_facts(context)

    assert facts["obstacles"][0]["geometry"] is None
    assert facts["obstacles"][0]["localGeometry"] == local_geometry
    assert facts["obstacles"][0]["topElevation"] == 520.0


def test_build_airport_spatial_facts_projects_point_geometry() -> None:
    context = SimpleNamespace(
        airport=SimpleNamespace(id=1, longitude=103.0, latitude=30.0),
        runways=[],
        stations=[],
        obstacles=[
            SimpleNamespace(
                id=1,
                name="点障碍物1",
                obstacle_type="point_tree",
                top_elevation=20.0,
                raw_payload={
                    "geometry": {
                        "type": "Point",
                        "coordinates": [103.001, 30.001],
                    }
                },
            )
        ],
    )

    facts = build_airport_spatial_facts(context)

    assert facts["obstacles"][0]["geometry"]["type"] == "Point"
    assert facts["obstacles"][0]["localGeometry"]["type"] == "Point"
    assert len(facts["obstacles"][0]["localGeometry"]["coordinates"]) == 2


def test_create_station_projector_centered_on_station() -> None:
    station = SimpleNamespace(longitude=104.0, latitude=30.0)

    projector = create_station_projector(station)

    origin_x, origin_y = projector.project_point(104.0, 30.0)
    local_x, local_y = projector.project_point(104.0, 30.0)
    assert math.isclose(local_x - origin_x, 0.0, abs_tol=1.0)
    assert math.isclose(local_y - origin_y, 0.0, abs_tol=1.0)


def test_project_obstacle_for_station_point() -> None:
    projector = create_station_projector(
        SimpleNamespace(longitude=104.0, latitude=30.0)
    )
    obstacle = {
        "id": 1,
        "name": "点障碍物",
        "obstacle_type": "tree_or_forest",
        "top_elevation": 520.0,
        "geometry": {
            "type": "Point",
            "coordinates": [104.001, 30.0],
        },
    }

    result = project_obstacle_for_station(projector, obstacle)

    assert result["id"] == 1
    assert result["name"] == "点障碍物"
    assert result["geometry"]["type"] == "Point"
    assert result["geometry"]["coordinates"] == [104.001, 30.0]
    assert result["localGeometry"]["type"] == "Point"
    local_coords = result["localGeometry"]["coordinates"]
    assert len(local_coords) == 2
    origin_x, origin_y = projector.project_point(104.0, 30.0)
    rel_x = local_coords[0] - origin_x
    rel_y = local_coords[1] - origin_y
    assert rel_x > 0
    assert math.isclose(rel_y, 0.0, abs_tol=10.0)


def test_project_obstacle_for_station_polygon() -> None:
    projector = create_station_projector(
        SimpleNamespace(longitude=104.0, latitude=30.0)
    )
    obstacle = {
        "id": 2,
        "name": "多边形障碍物",
        "obstacle_type": "building_general",
        "top_elevation": 550.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [104.0, 30.0],
                        [104.0005, 30.0],
                        [104.0005, 30.0005],
                        [104.0, 30.0005],
                        [104.0, 30.0],
                    ]
                ]
            ],
        },
    }

    result = project_obstacle_for_station(projector, obstacle)

    assert result["id"] == 2
    assert result["name"] == "多边形障碍物"
    assert result["obstacle_type"] == "building_general"
    assert result["top_elevation"] == 550.0
    assert result["geometry"]["type"] == "MultiPolygon"
    assert result["localGeometry"]["type"] == "MultiPolygon"
    local_coords = result["localGeometry"]["coordinates"]
    assert len(local_coords) == 1


def test_project_obstacle_for_station_overwrites_existing_local_geometry() -> None:
    projector = create_station_projector(
        SimpleNamespace(longitude=104.0, latitude=30.0)
    )
    obstacle = {
        "id": 3,
        "name": "测试障碍物",
        "geometry": {
            "type": "Point",
            "coordinates": [104.001, 30.001],
        },
        "localGeometry": {
            "type": "Point",
            "coordinates": [999.0, 888.0],
        },
    }

    result = project_obstacle_for_station(projector, obstacle)

    origin_x, origin_y = projector.project_point(104.0, 30.0)
    local_coords = result["localGeometry"]["coordinates"]
    rel_x = local_coords[0] - origin_x
    rel_y = local_coords[1] - origin_y
    assert math.isclose(rel_x, 0.0, abs_tol=200.0)
    assert math.isclose(rel_y, 0.0, abs_tol=200.0)
    assert local_coords[0] != 999.0
