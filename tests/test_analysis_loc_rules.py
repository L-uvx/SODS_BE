import importlib
import math
from decimal import Decimal

import pytest
from shapely.geometry import LineString, MultiPolygon, Polygon

from app.analysis.config import PROTECTION_ZONE_BUILDER_DISCRETIZATION
from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule
from app.analysis.rules.protection_zone_helpers import build_geometry_definition
from app.analysis.rules.loc.profile import LocRuleProfile
from app.analysis.rules.loc import (
    LOC_BUILDING_RESTRICTION_ZONE,
    LOC_FORWARD_SECTOR_3000M_15M,
    LOC_SITE_PROTECTION,
    LocBuildingRestrictionZoneRegion1Rule,
    LocBuildingRestrictionZoneRegion2Rule,
    LocBuildingRestrictionZoneRegion3Rule,
    LocBuildingRestrictionZoneRegion4Rule,
    LocForwardSector3000m15mRule,
    LocRunAreaProtectionRegionARule,
    LocRunAreaProtectionRegionCRule,
    LocSiteProtectionRule,
)
from app.analysis.rules.loc.building_restriction.helpers import (
    build_loc_building_restriction_zone_region_1_geometry,
    build_loc_building_restriction_zone_region_2_geometry,
    build_loc_building_restriction_zone_region_3_geometry,
    build_loc_building_restriction_zone_region_4_geometry,
    build_loc_building_restriction_zone_shared_context,
    calculate_region_3_worst_allowed_height_meters,
)
from app.analysis.rules.loc.run_area_protection.helpers import (
    build_loc_run_area_shared_context,
)
import app.analysis.rules.loc.building_restriction.region_3 as loc_region_3_module
import app.analysis.rules.loc.building_restriction.region_1 as loc_region_1_module
import app.analysis.rules.loc.building_restriction.region_2 as loc_region_2_module
import app.analysis.rules.loc.building_restriction.region_4 as loc_region_4_module
import app.analysis.rules.loc.building_restriction as loc_building_restriction_module
import app.analysis.rules.loc.profile as loc_profile_module
import app.analysis.rules.loc.run_area_protection as loc_run_area_protection_module
from app.analysis.rules.geometry_evaluation import evaluate_geometry_metric
from app.application.polygon_obstacle_import import PolygonObstacleImportService


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


def test_loc_placeholder_building_restriction_regions_keep_standards_neutral() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
            "station_sub_type": "II",
            "unit_number": "16",
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

    results = [
        LocBuildingRestrictionZoneRegion1Rule().bind(
            station=station,
            station_point=(0.0, 0.0),
            runway_context=runway,
        ).analyze(obstacle),
        LocBuildingRestrictionZoneRegion2Rule().bind(
            station=station,
            station_point=(0.0, 0.0),
            runway_context=runway,
        ).analyze(obstacle),
        LocBuildingRestrictionZoneRegion4Rule().bind(
            station=station,
            station_point=(0.0, 0.0),
            runway_context=runway,
        ).analyze(obstacle),
    ]

    assert [result.rule_code for result in results] == [
        "loc_building_restriction_zone_region_1",
        "loc_building_restriction_zone_region_2",
        "loc_building_restriction_zone_region_4",
    ]
    assert all(result.standards_rule_code is None for result in results)


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


def _make_loc_run_area_station() -> object:
    return type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
            "station_sub_type": "I",
            "unit_number": "11",
        },
    )()


def _make_loc_run_area_shared_context() -> tuple[object, object]:
    station = _make_loc_run_area_station()
    shared_context = build_loc_run_area_shared_context(
        station=station,
        station_point=(0.0, 0.0),
        runway_context={
            "localCenterPoint": (0.0, -600.0),
            "directionDegrees": 0.0,
            "lengthMeters": 600.0,
            "maximumAirworthiness": 1,
        },
    )

    assert shared_context is not None
    return station, shared_context


def _make_local_geometry_obstacle(
    *,
    obstacle_id: int,
    name: str,
    geometry: MultiPolygon,
    top_elevation: float = 520.0,
    raw_obstacle_type: str = "建筑物/构建物",
    global_obstacle_category: str = "building_general",
) -> dict[str, object]:
    polygon = max(geometry.geoms, key=lambda item: item.area)
    coordinates = [
        [[float(x), float(y)] for x, y in polygon.exterior.coords]
    ]
    return {
        "obstacleId": obstacle_id,
        "name": name,
        "rawObstacleType": raw_obstacle_type,
        "globalObstacleCategory": global_obstacle_category,
        "topElevation": top_elevation,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [coordinates],
        },
    }


def _build_inside_obstacle_for_zone(
    *,
    zone_geometry: MultiPolygon,
    obstacle_id: int,
    name: str,
) -> dict[str, object]:
    point = zone_geometry.representative_point()
    x = float(point.x)
    y = float(point.y)
    polygon = Polygon(
        [
            (x - 2.0, y - 2.0),
            (x + 2.0, y - 2.0),
            (x + 2.0, y + 2.0),
            (x - 2.0, y + 2.0),
            (x - 2.0, y - 2.0),
        ]
    )
    return _make_local_geometry_obstacle(
        obstacle_id=obstacle_id,
        name=name,
        geometry=MultiPolygon([polygon]),
        raw_obstacle_type="车辆/航空器/机械",
        global_obstacle_category="vehicle_or_aircraft_or_machine",
    )


def _build_outside_obstacle_for_zone(
    *,
    zone_geometry: MultiPolygon,
    obstacle_id: int,
    name: str,
) -> dict[str, object]:
    _, _, max_x, max_y = zone_geometry.bounds
    polygon = Polygon(
        [
            (max_x + 100.0, max_y + 100.0),
            (max_x + 120.0, max_y + 100.0),
            (max_x + 120.0, max_y + 120.0),
            (max_x + 100.0, max_y + 120.0),
            (max_x + 100.0, max_y + 100.0),
        ]
    )
    return _make_local_geometry_obstacle(
        obstacle_id=obstacle_id,
        name=name,
        geometry=MultiPolygon([polygon]),
    )


def test_loc_run_area_region_a_rule_bind_builds_sensitive_zone_spec() -> None:
    module = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.region_a"
    )
    station, shared_context = _make_loc_run_area_shared_context()

    bound_rule = module.LocRunAreaProtectionRegionARule().bind(
        station=station,
        shared_context=shared_context,
    )

    assert bound_rule.protection_zone.rule_code == "loc_run_area_protection_region_a"
    assert bound_rule.protection_zone.zone_code == "loc_run_area_protection"
    assert bound_rule.protection_zone.region_code == "A"
    assert (
        bound_rule.protection_zone.geometry_definition["shapeType"] == "multipolygon"
    )


def test_loc_run_area_region_c_rule_rejects_obstacle_entering_critical_zone() -> None:
    station, shared_context = _make_loc_run_area_shared_context()
    bound_rule = LocRunAreaProtectionRegionCRule().bind(
        station=station,
        shared_context=shared_context,
    )
    obstacle = _build_inside_obstacle_for_zone(
        zone_geometry=bound_rule.protection_zone.local_geometry,
        obstacle_id=201,
        name="Critical Obstacle",
    )

    result = bound_rule.analyze(obstacle)

    assert result.is_applicable is True
    assert result.is_compliant is False
    assert result.standards_rule_code == "loc_run_area_protection_critical"
    assert result.metrics["enteredProtectionZone"] is True


def test_loc_run_area_region_c_rule_allows_obstacle_outside_critical_zone() -> None:
    station, shared_context = _make_loc_run_area_shared_context()
    bound_rule = LocRunAreaProtectionRegionCRule().bind(
        station=station,
        shared_context=shared_context,
    )
    obstacle = _build_outside_obstacle_for_zone(
        zone_geometry=bound_rule.protection_zone.local_geometry,
        obstacle_id=202,
        name="Outside Critical Obstacle",
    )
    obstacle["rawObstacleType"] = "车辆/航空器/机械"
    obstacle["globalObstacleCategory"] = "vehicle_or_aircraft_or_machine"

    result = bound_rule.analyze(obstacle)

    assert result.is_applicable is True
    assert result.is_compliant is True
    assert result.standards_rule_code == "loc_run_area_protection_critical"
    assert result.metrics["enteredProtectionZone"] is False


def test_loc_run_area_region_b_rule_bind_builds_sensitive_zone_spec() -> None:
    module = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.region_b"
    )
    station, shared_context = _make_loc_run_area_shared_context()

    bound_rule = module.LocRunAreaProtectionRegionBRule().bind(
        station=station,
        shared_context=shared_context,
    )

    assert bound_rule.protection_zone.rule_code == "loc_run_area_protection_region_b"
    assert bound_rule.protection_zone.zone_code == "loc_run_area_protection"
    assert bound_rule.protection_zone.region_code == "B"
    assert (
        bound_rule.protection_zone.geometry_definition["shapeType"] == "multipolygon"
    )


def test_loc_run_area_region_a_rule_rejects_obstacle_entering_sensitive_zone() -> None:
    station, shared_context = _make_loc_run_area_shared_context()
    bound_rule = LocRunAreaProtectionRegionARule().bind(
        station=station,
        shared_context=shared_context,
    )
    obstacle = _build_inside_obstacle_for_zone(
        zone_geometry=bound_rule.protection_zone.local_geometry,
        obstacle_id=203,
        name="Sensitive Obstacle",
    )

    result = bound_rule.analyze(obstacle)

    assert result.is_applicable is True
    assert result.is_compliant is False
    assert result.standards_rule_code == "loc_run_area_protection_sensitive"
    assert result.metrics["enteredProtectionZone"] is True


def test_loc_run_area_region_a_rule_skips_non_mobile_obstacle_type() -> None:
    station, shared_context = _make_loc_run_area_shared_context()
    bound_rule = LocRunAreaProtectionRegionARule().bind(
        station=station,
        shared_context=shared_context,
    )
    obstacle = _make_local_geometry_obstacle(
        obstacle_id=2031,
        name="Static Building In Sensitive Zone",
        geometry=bound_rule.protection_zone.local_geometry,
        raw_obstacle_type="建筑物/构建物",
        global_obstacle_category="building_general",
    )

    result = bound_rule.analyze(obstacle)

    assert result.is_applicable is False
    assert result.is_compliant is True
    assert result.standards_rule_code == "loc_run_area_protection_sensitive"
    assert result.metrics["enteredProtectionZone"] is True


def test_loc_run_area_region_c_rule_bind_builds_critical_zone_spec() -> None:
    module = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.region_c"
    )
    station, shared_context = _make_loc_run_area_shared_context()

    bound_rule = module.LocRunAreaProtectionRegionCRule().bind(
        station=station,
        shared_context=shared_context,
    )

    assert bound_rule.protection_zone.rule_code == "loc_run_area_protection_region_c"
    assert bound_rule.protection_zone.zone_code == "loc_run_area_protection"
    assert bound_rule.protection_zone.region_code == "C"
    assert (
        bound_rule.protection_zone.geometry_definition["shapeType"] == "multipolygon"
    )


def test_loc_run_area_region_d_rule_bind_builds_sensitive_zone_spec() -> None:
    module = importlib.import_module(
        "app.analysis.rules.loc.run_area_protection.region_d"
    )
    station, shared_context = _make_loc_run_area_shared_context()

    bound_rule = module.LocRunAreaProtectionRegionDRule().bind(
        station=station,
        shared_context=shared_context,
    )

    assert bound_rule.protection_zone.rule_code == "loc_run_area_protection_region_d"
    assert bound_rule.protection_zone.zone_code == "loc_run_area_protection"
    assert bound_rule.protection_zone.region_code == "D"
    assert (
        bound_rule.protection_zone.geometry_definition["shapeType"] == "multipolygon"
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
            "station_sub_type": "II",
            "unit_number": "16",
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
            "station_sub_type": "II",
            "unit_number": "16",
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
            "station_sub_type": "II",
            "unit_number": "16",
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
        "maximumAirworthiness": 2,
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
            "station_sub_type": "II",
            "unit_number": "16",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
        "maximumAirworthiness": 2,
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
            "station_sub_type": "II",
            "unit_number": "16",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
        "maximumAirworthiness": 2,
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

    assert [result.rule_name for result in payload.rule_results] == [
        "loc_site_protection",
    ]
    assert {zone.rule_code for zone in payload.protection_zones} == {
        "loc_site_protection",
    }


def _make_loc_profile_station() -> object:
    return type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
            "station_sub_type": "II",
            "unit_number": "16",
        },
    )()


def _make_loc_profile_runway(*, maximum_airworthiness: float = 2.0) -> dict[str, object]:
    return {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
        "maximumAirworthiness": maximum_airworthiness,
    }


class _FakeBoundRule(BoundObstacleRule):
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
            is_compliant=True,
            message="fake result",
            metrics={},
        )


def _make_fake_bound_rule(*, rule_code: str, zone_code: str, region_code: str) -> _FakeBoundRule:
    return _FakeBoundRule(
        protection_zone=ProtectionZoneSpec(
            station_id=101,
            station_type="LOC",
            rule_code=rule_code,
            rule_name=rule_code,
            zone_code=zone_code,
            zone_name=zone_code,
            region_code=region_code,
            region_name=region_code,
            local_geometry=MultiPolygon(
                [
                    Polygon(
                        [
                            (0.0, 0.0),
                            (1.0, 0.0),
                            (1.0, 1.0),
                            (0.0, 1.0),
                            (0.0, 0.0),
                        ]
                    )
                ]
            ),
            geometry_definition={"shapeType": "multipolygon", "coordinates": []},
            vertical_definition={
                "mode": "flat",
                "baseReference": "station",
                "baseHeightMeters": 500.0,
            },
        )
    )


def test_loc_rule_profile_skips_run_area_and_building_restriction_prebind_for_hill_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    station = _make_loc_profile_station()
    runway = _make_loc_profile_runway()
    obstacle = {
        "obstacleId": 701,
        "name": "Hill Only Obstacle",
        "rawObstacleType": "山丘",
        "globalObstacleCategory": "hill",
        "topElevation": 999.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [[[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]],
        },
    }
    calls = {
        "run_area_builder": 0,
        "building_builder": 0,
    }

    def _fake_site_bind(self, *, station: object, station_point: tuple[float, float], runway_context: dict[str, object]) -> BoundObstacleRule:
        return _make_fake_bound_rule(
            rule_code="loc_site_protection",
            zone_code="loc_site_protection",
            region_code="default",
        )

    def _record_run_area_builder(*, station: object, station_point: tuple[float, float], runway_context: dict[str, object]) -> object:
        calls["run_area_builder"] += 1
        return object()

    def _record_building_builder(*, station_point: tuple[float, float], runway_context: dict[str, object]) -> object:
        calls["building_builder"] += 1
        return object()

    monkeypatch.setattr(loc_profile_module.LocSiteProtectionRule, "bind", _fake_site_bind)
    monkeypatch.setattr(
        loc_profile_module,
        "build_loc_run_area_shared_context",
        _record_run_area_builder,
    )
    monkeypatch.setattr(
        loc_profile_module,
        "build_loc_building_restriction_zone_shared_context",
        _record_building_builder,
    )

    LocRuleProfile().analyze(
        station=station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
        runways=[runway],
    )

    assert calls["run_area_builder"] == 0
    assert calls["building_builder"] == 0


def test_loc_rule_profile_only_prebinds_run_area_for_mobile_obstacle_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    station = _make_loc_profile_station()
    runway = _make_loc_profile_runway(maximum_airworthiness=1.0)
    obstacle = {
        "obstacleId": 702,
        "name": "Mobile Obstacle",
        "rawObstacleType": "车辆/航空器/机械",
        "globalObstacleCategory": "vehicle_or_aircraft_or_machine",
        "topElevation": 505.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [[[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]],
        },
    }
    calls = {
        "run_area_builder": 0,
        "building_builder": 0,
        "forward_sector_bind": 0,
    }

    def _fake_site_bind(self, *, station: object, station_point: tuple[float, float], runway_context: dict[str, object]) -> BoundObstacleRule:
        return _make_fake_bound_rule(
            rule_code="loc_site_protection",
            zone_code="loc_site_protection",
            region_code="default",
        )

    def _record_forward_sector_bind(self, *, station: object, station_point: tuple[float, float], runway_context: dict[str, object]) -> BoundObstacleRule:
        calls["forward_sector_bind"] += 1
        return _make_fake_bound_rule(
            rule_code="loc_forward_sector_3000m_15m",
            zone_code="loc_forward_sector_3000m_15m",
            region_code="default",
        )

    def _record_run_area_builder(*, station: object, station_point: tuple[float, float], runway_context: dict[str, object]) -> object:
        calls["run_area_builder"] += 1
        return object()

    def _record_building_builder(*, station_point: tuple[float, float], runway_context: dict[str, object]) -> object:
        calls["building_builder"] += 1
        return object()

    def _fake_run_area_bind(self, *, station: object, shared_context: object) -> BoundObstacleRule:
        return _make_fake_bound_rule(
            rule_code=str(self.rule_code),
            zone_code="loc_run_area_protection",
            region_code=str(getattr(self, "region_code", "default")),
        )

    monkeypatch.setattr(loc_profile_module.LocSiteProtectionRule, "bind", _fake_site_bind)
    monkeypatch.setattr(
        loc_profile_module.LocForwardSector3000m15mRule,
        "bind",
        _record_forward_sector_bind,
    )
    monkeypatch.setattr(
        loc_profile_module,
        "build_loc_run_area_shared_context",
        _record_run_area_builder,
    )
    monkeypatch.setattr(
        loc_profile_module,
        "build_loc_building_restriction_zone_shared_context",
        _record_building_builder,
    )
    monkeypatch.setattr(
        loc_profile_module.LocRunAreaProtectionRegionARule,
        "bind",
        _fake_run_area_bind,
    )
    monkeypatch.setattr(
        loc_profile_module.LocRunAreaProtectionRegionBRule,
        "bind",
        _fake_run_area_bind,
    )
    monkeypatch.setattr(
        loc_profile_module.LocRunAreaProtectionRegionCRule,
        "bind",
        _fake_run_area_bind,
    )
    monkeypatch.setattr(
        loc_profile_module.LocRunAreaProtectionRegionDRule,
        "bind",
        _fake_run_area_bind,
    )

    LocRuleProfile().analyze(
        station=station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
        runways=[runway],
    )

    assert calls["run_area_builder"] == 1
    assert calls["building_builder"] == 0
    assert calls["forward_sector_bind"] == 0


def test_loc_rule_profile_only_prebinds_building_groups_for_building_obstacle_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    station = _make_loc_profile_station()
    runway = _make_loc_profile_runway()
    obstacle = {
        "obstacleId": 703,
        "name": "Building Obstacle",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 520.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [[[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]],
        },
    }
    calls = {
        "run_area_builder": 0,
        "building_builder": 0,
        "forward_sector_bind": 0,
    }

    def _fake_site_bind(self, *, station: object, station_point: tuple[float, float], runway_context: dict[str, object]) -> BoundObstacleRule:
        return _make_fake_bound_rule(
            rule_code="loc_site_protection",
            zone_code="loc_site_protection",
            region_code="default",
        )

    def _record_forward_sector_bind(self, *, station: object, station_point: tuple[float, float], runway_context: dict[str, object]) -> BoundObstacleRule:
        calls["forward_sector_bind"] += 1
        return _make_fake_bound_rule(
            rule_code="loc_forward_sector_3000m_15m",
            zone_code="loc_forward_sector_3000m_15m",
            region_code="default",
        )

    def _record_run_area_builder(*, station: object, station_point: tuple[float, float], runway_context: dict[str, object]) -> object:
        calls["run_area_builder"] += 1
        return object()

    def _record_building_builder(*, station_point: tuple[float, float], runway_context: dict[str, object]) -> object:
        calls["building_builder"] += 1
        return object()

    def _fake_building_bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
        runway_context: dict[str, object],
        shared_context: object,
    ) -> BoundObstacleRule:
        return _make_fake_bound_rule(
            rule_code=str(self.rule_code),
            zone_code="loc_building_restriction_zone",
            region_code=str(getattr(self, "region_code", "default")),
        )

    monkeypatch.setattr(loc_profile_module.LocSiteProtectionRule, "bind", _fake_site_bind)
    monkeypatch.setattr(
        loc_profile_module.LocForwardSector3000m15mRule,
        "bind",
        _record_forward_sector_bind,
    )
    monkeypatch.setattr(
        loc_profile_module,
        "build_loc_run_area_shared_context",
        _record_run_area_builder,
    )
    monkeypatch.setattr(
        loc_profile_module,
        "build_loc_building_restriction_zone_shared_context",
        _record_building_builder,
    )
    monkeypatch.setattr(
        loc_profile_module.LocBuildingRestrictionZoneRegion1Rule,
        "bind",
        _fake_building_bind,
    )
    monkeypatch.setattr(
        loc_profile_module.LocBuildingRestrictionZoneRegion2Rule,
        "bind",
        _fake_building_bind,
    )
    monkeypatch.setattr(
        loc_profile_module.LocBuildingRestrictionZoneRegion3Rule,
        "bind",
        _fake_building_bind,
    )
    monkeypatch.setattr(
        loc_profile_module.LocBuildingRestrictionZoneRegion4Rule,
        "bind",
        _fake_building_bind,
    )

    LocRuleProfile().analyze(
        station=station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
        runways=[runway],
    )

    assert calls["building_builder"] == 1
    assert calls["forward_sector_bind"] == 1
    assert calls["run_area_builder"] == 0


def test_loc_rule_profile_returns_rule_results_and_protection_zone_specs() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
            "station_sub_type": "II",
            "unit_number": "16",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
        "maximumAirworthiness": 2,
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

    assert len(payload.rule_results) == 6
    assert len(payload.protection_zones) == 6
    assert all(
        zone.geometry_definition["shapeType"] == "multipolygon"
        for zone in payload.protection_zones
    )
    assert {result.rule_code for result in payload.rule_results} == {
        "loc_site_protection",
        "loc_forward_sector_3000m_15m",
        "loc_building_restriction_zone_region_1",
        "loc_building_restriction_zone_region_2",
        "loc_building_restriction_zone_region_3",
        "loc_building_restriction_zone_region_4",
    }
    assert {zone.rule_code for zone in payload.protection_zones} == {
        "loc_site_protection",
        "loc_forward_sector_3000m_15m",
        "loc_building_restriction_zone_region_1",
        "loc_building_restriction_zone_region_2",
        "loc_building_restriction_zone_region_3",
        "loc_building_restriction_zone_region_4",
    }


def test_loc_rule_profile_returns_run_area_abcd_protection_zones_when_context_valid() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
            "station_sub_type": "I",
            "unit_number": "11",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
        "maximumAirworthiness": 1,
    }

    payload = LocRuleProfile().analyze(
        station=station,
        obstacles=[],
        station_point=(0.0, 0.0),
        runways=[runway],
    )

    run_area_zone_codes = {
        zone.rule_code
        for zone in payload.protection_zones
        if zone.zone_code == "loc_run_area_protection"
    }

    assert run_area_zone_codes == {
        "loc_run_area_protection_region_a",
        "loc_run_area_protection_region_b",
        "loc_run_area_protection_region_c",
        "loc_run_area_protection_region_d",
    }


def test_loc_rule_profile_does_not_raise_when_run_area_table_row_lacks_optional_region_parameters() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
            "station_sub_type": "I",
            "unit_number": "12",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
        "maximumAirworthiness": 1,
    }
    obstacle = {
        "obstacleId": 205,
        "name": "Run Area Optional Region Obstacle",
        "rawObstacleType": "车辆/航空器/机械",
        "globalObstacleCategory": "vehicle_or_aircraft_or_machine",
        "topElevation": 505.0,
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

    try:
        LocRuleProfile().analyze(
            station=station,
            obstacles=[obstacle],
            station_point=(0.0, 0.0),
            runways=[runway],
        )
    except ValueError as exc:
        pytest.fail(f"LocRuleProfile.analyze should skip unavailable run-area regions: {exc}")


def test_loc_rule_profile_keeps_region_c_and_skips_unavailable_run_area_regions() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
            "station_sub_type": "I",
            "unit_number": "12",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
        "maximumAirworthiness": 1,
    }
    obstacle = {
        "obstacleId": 206,
        "name": "Run Area Critical Obstacle",
        "rawObstacleType": "车辆/航空器/机械",
        "globalObstacleCategory": "vehicle_or_aircraft_or_machine",
        "topElevation": 505.0,
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

    run_area_zone_codes = {
        zone.rule_code
        for zone in payload.protection_zones
        if zone.zone_code == "loc_run_area_protection"
    }

    assert run_area_zone_codes == {"loc_run_area_protection_region_c"}


def test_loc_rule_profile_emits_run_area_rule_results_for_intersecting_zone() -> None:
    station, shared_context = _make_loc_run_area_shared_context()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
        "maximumAirworthiness": 1,
    }
    run_area_rule = LocRunAreaProtectionRegionCRule().bind(
        station=station,
        shared_context=shared_context,
    )
    obstacle = _build_inside_obstacle_for_zone(
        zone_geometry=run_area_rule.protection_zone.local_geometry,
        obstacle_id=204,
        name="Profile Critical Obstacle",
    )

    payload = LocRuleProfile().analyze(
        station=station,
        obstacles=[obstacle],
        station_point=(0.0, 0.0),
        runways=[runway],
    )

    region_c_results = [
        result
        for result in payload.rule_results
        if result.rule_code == "loc_run_area_protection_region_c"
    ]

    assert len(region_c_results) == 1
    assert region_c_results[0].is_applicable is True
    assert region_c_results[0].is_compliant is False
    assert (
        region_c_results[0].standards_rule_code
        == "loc_run_area_protection_critical"
    )
    assert region_c_results[0].metrics["enteredProtectionZone"] is True


def test_loc_rule_profile_accepts_integral_float_airworthiness_from_service_context() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
            "station_sub_type": "I",
            "unit_number": "11",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
        "maximumAirworthiness": 1.0,
    }

    payload = LocRuleProfile().analyze(
        station=station,
        obstacles=[],
        station_point=(0.0, 0.0),
        runways=[runway],
    )

    assert {
        zone.rule_code
        for zone in payload.protection_zones
        if zone.zone_code == "loc_run_area_protection"
    } == {
        "loc_run_area_protection_region_a",
        "loc_run_area_protection_region_b",
        "loc_run_area_protection_region_c",
        "loc_run_area_protection_region_d",
    }


def test_loc_rule_profile_returns_no_run_area_abcd_protection_zones_when_context_invalid() -> None:
    station = type(
        "Station",
        (),
        {
            "id": 101,
            "station_type": "LOC",
            "altitude": 500.0,
            "runway_no": "18",
            "station_sub_type": "I",
            "unit_number": "11",
        },
    )()
    runway = {
        "runwayId": 201,
        "runNumber": "18",
        "localCenterPoint": (0.0, -600.0),
        "directionDegrees": 0.0,
        "lengthMeters": 600.0,
        "widthMeters": 45.0,
        "maximumAirworthiness": 99,
    }

    payload = LocRuleProfile().analyze(
        station=station,
        obstacles=[],
        station_point=(0.0, 0.0),
        runways=[runway],
    )

    assert {zone.rule_code for zone in payload.protection_zones} == {
        "loc_site_protection",
        "loc_forward_sector_3000m_15m",
        "loc_building_restriction_zone_region_1",
        "loc_building_restriction_zone_region_2",
        "loc_building_restriction_zone_region_3",
        "loc_building_restriction_zone_region_4",
    }
    assert all(
        zone.zone_code != "loc_run_area_protection"
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


def test_build_runway_contexts_preserves_non_integral_airworthiness_for_validation() -> None:
    service = PolygonObstacleImportService.__new__(PolygonObstacleImportService)

    class _Projector:
        def project_point(self, longitude: float, latitude: float) -> tuple[float, float]:
            return (longitude, latitude)

    runway = type(
        "Runway",
        (),
        {
            "id": 201,
            "run_number": "18",
            "longitude": Decimal("120.100000"),
            "latitude": Decimal("30.100000"),
            "direction": Decimal("90.00"),
            "length": Decimal("600.00"),
            "width": Decimal("45.00"),
            "maximum_airworthiness": Decimal("2.50"),
        },
    )()

    runway_contexts = service._build_runway_contexts(
        projector=_Projector(),
        runways=[runway],
    )

    assert runway_contexts[0]["maximumAirworthiness"] == 2.5


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


def test_loc_building_restriction_zone_shared_context_resolves_apex_root_and_arc_geometry() -> None:
    assert LOC_BUILDING_RESTRICTION_ZONE["zone_code"] == "loc_building_restriction_zone"
    assert LOC_BUILDING_RESTRICTION_ZONE["zone_name"] == "LOC 建筑物限制区"
    assert "region_1_2_inner_offset_m" not in LOC_BUILDING_RESTRICTION_ZONE
    assert LOC_BUILDING_RESTRICTION_ZONE["region_1_2_forward_length_m"] == 500.0
    assert LOC_BUILDING_RESTRICTION_ZONE["region_1_2_outer_offset_m"] == 1500.0
    assert LOC_BUILDING_RESTRICTION_ZONE["region_1_2_side_angle_degrees"] == 20.0
    assert LOC_BUILDING_RESTRICTION_ZONE["region_1_2_height_offset_m"] == 20.0

    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(0.0, 0.0),
        runway_context={
            "localCenterPoint": (0.0, 600.0),
            "directionDegrees": 180.0,
            "lengthMeters": 600.0,
            "widthMeters": 45.0,
        },
    )

    region_3_geometry = build_loc_building_restriction_zone_region_3_geometry(shared_context)

    assert shared_context.apex_point == pytest.approx((0.0, 900.0))
    assert shared_context.root_left_point == pytest.approx((-500.0, 900.0))
    assert shared_context.root_right_point == pytest.approx((500.0, 900.0))
    assert shared_context.station_to_apex_distance_meters == pytest.approx(900.0)
    assert shared_context.arc_radius_meters == pytest.approx(6900.0)
    assert shared_context.arc_height_offset_meters == 70.0
    assert shared_context.alpha_degrees > 0.0
    assert region_3_geometry.arc_points


def test_loc_building_restriction_zone_shared_context_resolves_only_shared_base_data() -> None:
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(0.0, 0.0),
        runway_context={
            "localCenterPoint": (0.0, 600.0),
            "directionDegrees": 180.0,
            "lengthMeters": 600.0,
            "widthMeters": 45.0,
        },
    )

    assert shared_context.station_point == pytest.approx((0.0, 0.0))
    assert shared_context.apex_point == pytest.approx((0.0, 900.0))
    assert shared_context.root_left_point == pytest.approx((-500.0, 900.0))
    assert shared_context.root_right_point == pytest.approx((500.0, 900.0))
    assert shared_context.station_to_apex_distance_meters == pytest.approx(900.0)
    assert shared_context.arc_radius_meters == pytest.approx(6900.0)
    assert shared_context.arc_height_offset_meters == 70.0
    assert shared_context.alpha_degrees > 0.0


def test_loc_building_restriction_zone_region_builders_share_same_context_outputs() -> None:
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(100.0, 0.0),
        runway_context={
            "localCenterPoint": (0.0, 600.0),
            "directionDegrees": 180.0,
            "lengthMeters": 600.0,
            "widthMeters": 45.0,
        },
    )

    region_1_geometry = build_loc_building_restriction_zone_region_1_geometry(
        shared_context
    )
    region_2_geometry = build_loc_building_restriction_zone_region_2_geometry(
        shared_context
    )
    region_3_geometry = build_loc_building_restriction_zone_region_3_geometry(
        shared_context
    )
    region_4_geometry = build_loc_building_restriction_zone_region_4_geometry(
        shared_context
    )
    region_1_points = list(region_1_geometry.local_geometry.geoms[0].exterior.coords)[:-1]
    region_2_points = list(region_2_geometry.local_geometry.geoms[0].exterior.coords)[:-1]

    assert len(region_1_points) == 4
    assert len(region_2_points) == 4
    assert region_1_points[0] == pytest.approx(shared_context.root_left_point)
    assert region_2_points[0] == pytest.approx(shared_context.root_right_point)
    assert region_3_geometry.local_geometry.bounds[1] == pytest.approx(
        shared_context.root_left_point[1]
    )
    assert region_3_geometry.local_geometry.bounds[3] == pytest.approx(
        max(point[1] for point in region_3_geometry.arc_points)
    )
    assert region_3_geometry.arc_points
    assert region_4_geometry.front_left_point == pytest.approx((-500.0, 900.0))
    assert region_4_geometry.back_right_point == pytest.approx((500.0, -500.0))


def test_loc_building_restriction_zone_region_3_root_edge_aligns_with_region_4_front_edge() -> None:
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(100.0, 0.0),
        runway_context={
            "localCenterPoint": (0.0, 600.0),
            "directionDegrees": 180.0,
            "lengthMeters": 600.0,
            "widthMeters": 45.0,
        },
    )

    region_3_geometry = build_loc_building_restriction_zone_region_3_geometry(
        shared_context
    )
    region_4_geometry = build_loc_building_restriction_zone_region_4_geometry(
        shared_context
    )
    region_3_points = list(region_3_geometry.local_geometry.geoms[0].exterior.coords)[:-1]

    assert region_3_points[0] == pytest.approx(region_4_geometry.front_left_point)
    assert region_3_points[-1] == pytest.approx(region_4_geometry.front_right_point)


def test_loc_building_restriction_zone_region_4_back_edge_uses_apex_based_full_length() -> None:
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(100.0, 0.0),
        runway_context={
            "localCenterPoint": (0.0, 600.0),
            "directionDegrees": 180.0,
            "lengthMeters": 600.0,
            "widthMeters": 45.0,
        },
    )

    geometry = build_loc_building_restriction_zone_region_4_geometry(shared_context)

    assert geometry.back_left_point == pytest.approx((-500.0, -500.0))
    assert geometry.back_right_point == pytest.approx((500.0, -500.0))


def test_loc_building_restriction_zone_region_1_2_build_mirrored_trapezoids() -> None:
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(0.0, 0.0),
        runway_context={
            "localCenterPoint": (0.0, 600.0),
            "directionDegrees": 180.0,
            "lengthMeters": 600.0,
            "widthMeters": 45.0,
        },
    )

    region_1_geometry = build_loc_building_restriction_zone_region_1_geometry(
        shared_context
    )
    region_2_geometry = build_loc_building_restriction_zone_region_2_geometry(
        shared_context
    )

    region_1_points = list(region_1_geometry.local_geometry.geoms[0].exterior.coords)[:-1]
    region_2_points = list(region_2_geometry.local_geometry.geoms[0].exterior.coords)[:-1]
    expected_forward_length = LOC_BUILDING_RESTRICTION_ZONE[
        "region_1_2_forward_length_m"
    ]
    expected_outer_offset = LOC_BUILDING_RESTRICTION_ZONE["region_1_2_outer_offset_m"]
    expected_lateral_delta = (
        expected_outer_offset - LOC_BUILDING_RESTRICTION_ZONE["root_half_width_m"]
    )
    expected_reverse_delta = expected_lateral_delta / math.tan(
        math.radians(LOC_BUILDING_RESTRICTION_ZONE["region_1_2_side_angle_degrees"])
    )

    assert len(region_1_points) == 4
    assert len(region_2_points) == 4
    assert region_1_points[0] == pytest.approx(shared_context.root_left_point)
    assert region_2_points[0] == pytest.approx(shared_context.root_right_point)
    assert region_1_points[1] == pytest.approx((-500.0, -500.0))
    assert region_1_points[2] == pytest.approx((-1500.0, -500.0))
    assert region_1_points[3] == pytest.approx((-1500.0, 900.0 + expected_reverse_delta))
    assert region_2_points[1] == pytest.approx((500.0, -500.0))
    assert region_2_points[2] == pytest.approx((1500.0, -500.0))
    assert region_2_points[3] == pytest.approx((1500.0, 900.0 + expected_reverse_delta))
    assert region_1_points[1][1] == pytest.approx(region_2_points[1][1])
    assert region_1_points[2][1] == pytest.approx(region_2_points[2][1])
    assert region_1_points[3][1] == pytest.approx(region_2_points[3][1])
    assert abs(region_1_points[1][1] - shared_context.station_point[1]) == pytest.approx(
        expected_forward_length
    )
    assert abs(region_1_points[2][0] - region_1_points[1][0]) == pytest.approx(
        expected_lateral_delta
    )


def test_loc_building_restriction_zone_region_1_2_bind_uses_height_offset_config() -> None:
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

    region_1_rule = LocBuildingRestrictionZoneRegion1Rule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )
    region_2_rule = LocBuildingRestrictionZoneRegion2Rule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

    assert region_1_rule.protection_zone.vertical_definition == {
        "mode": "flat",
        "baseReference": "station",
        "baseHeightMeters": 520.0,
    }
    assert region_2_rule.protection_zone.vertical_definition == {
        "mode": "flat",
        "baseReference": "station",
        "baseHeightMeters": 520.0,
    }


def test_loc_building_restriction_zone_region_1_rule_allows_obstacle_within_zone_below_allowed_height() -> None:
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
        "obstacleId": 14,
        "name": "Obstacle Region 1 Below Limit",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 519.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-520.0, 500.0],
                        [-480.0, 500.0],
                        [-480.0, 540.0],
                        [-520.0, 540.0],
                        [-520.0, 500.0],
                    ]
                ]
            ],
        },
    }

    result = LocBuildingRestrictionZoneRegion1Rule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert result.region_code == "1"
    assert result.metrics == {
        "enteredProtectionZone": True,
        "baseHeightMeters": 500.0,
        "allowedHeightMeters": 520.0,
        "topElevationMeters": 519.0,
    }
    assert result.message == "obstacle within region 1 and below allowed height"
    assert result.is_compliant is True


def test_loc_building_restriction_zone_region_1_rule_rejects_obstacle_within_zone_above_allowed_height() -> None:
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
        "obstacleId": 15,
        "name": "Obstacle Region 1 Above Limit",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 521.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-520.0, 500.0],
                        [-480.0, 500.0],
                        [-480.0, 540.0],
                        [-520.0, 540.0],
                        [-520.0, 500.0],
                    ]
                ]
            ],
        },
    }

    result = LocBuildingRestrictionZoneRegion1Rule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert result.region_code == "1"
    assert result.metrics == {
        "enteredProtectionZone": True,
        "baseHeightMeters": 500.0,
        "allowedHeightMeters": 520.0,
        "topElevationMeters": 521.0,
    }
    assert result.message == "obstacle within region 1 above allowed height"
    assert result.is_compliant is False


def test_loc_building_restriction_zone_region_2_rule_allows_obstacle_within_zone_below_allowed_height() -> None:
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
        "obstacleId": 16,
        "name": "Obstacle Region 2 Below Limit",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 519.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [480.0, 500.0],
                        [520.0, 500.0],
                        [520.0, 540.0],
                        [480.0, 540.0],
                        [480.0, 500.0],
                    ]
                ]
            ],
        },
    }

    result = LocBuildingRestrictionZoneRegion2Rule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert result.region_code == "2"
    assert result.metrics == {
        "enteredProtectionZone": True,
        "baseHeightMeters": 500.0,
        "allowedHeightMeters": 520.0,
        "topElevationMeters": 519.0,
    }
    assert result.message == "obstacle within region 2 and below allowed height"
    assert result.is_compliant is True


def test_loc_building_restriction_zone_region_2_rule_rejects_obstacle_within_zone_above_allowed_height() -> None:
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
        "obstacleId": 17,
        "name": "Obstacle Region 2 Above Limit",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 521.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [480.0, 500.0],
                        [520.0, 500.0],
                        [520.0, 540.0],
                        [480.0, 540.0],
                        [480.0, 500.0],
                    ]
                ]
            ],
        },
    }

    result = LocBuildingRestrictionZoneRegion2Rule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert result.region_code == "2"
    assert result.metrics == {
        "enteredProtectionZone": True,
        "baseHeightMeters": 500.0,
        "allowedHeightMeters": 520.0,
        "topElevationMeters": 521.0,
    }
    assert result.message == "obstacle within region 2 above allowed height"
    assert result.is_compliant is False


def test_loc_building_restriction_zone_region_1_2_keeps_root_anchor_points() -> None:
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(0.0, 0.0),
        runway_context={
            "localCenterPoint": (0.0, 600.0),
            "directionDegrees": 180.0,
            "lengthMeters": 600.0,
            "widthMeters": 45.0,
        },
    )

    region_1_geometry = build_loc_building_restriction_zone_region_1_geometry(
        shared_context
    )
    region_2_geometry = build_loc_building_restriction_zone_region_2_geometry(
        shared_context
    )

    region_1_points = list(region_1_geometry.local_geometry.geoms[0].exterior.coords)[:-1]
    region_2_points = list(region_2_geometry.local_geometry.geoms[0].exterior.coords)[:-1]

    assert shared_context.root_left_point == pytest.approx((-500.0, 900.0))
    assert shared_context.root_right_point == pytest.approx((500.0, 900.0))
    assert region_1_points[0] == pytest.approx(shared_context.root_left_point)
    assert region_2_points[0] == pytest.approx(shared_context.root_right_point)


def test_loc_building_restriction_zone_helper_builds_region_4_rectangle() -> None:
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(0.0, 0.0),
        runway_context={
            "localCenterPoint": (0.0, 600.0),
            "directionDegrees": 180.0,
            "lengthMeters": 600.0,
            "widthMeters": 45.0,
        },
    )

    geometry = build_loc_building_restriction_zone_region_4_geometry(shared_context)

    min_x, min_y, max_x, max_y = geometry.local_geometry.bounds

    assert min_x == pytest.approx(-500.0)
    assert max_x == pytest.approx(500.0)
    assert min_y == pytest.approx(-500.0)
    assert max_y == pytest.approx(900.0)


def test_loc_building_restriction_zone_helper_builds_region_4_front_edge_from_front_center() -> None:
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(100.0, 0.0),
        runway_context={
            "localCenterPoint": (0.0, 600.0),
            "directionDegrees": 180.0,
            "lengthMeters": 600.0,
            "widthMeters": 45.0,
        },
    )

    geometry = build_loc_building_restriction_zone_region_4_geometry(shared_context)

    assert geometry.front_left_point == pytest.approx((-500.0, 900.0))
    assert geometry.front_right_point == pytest.approx((500.0, 900.0))


def test_loc_building_restriction_zone_region_3_rule_uses_worst_point_height_check() -> None:
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
        "obstacleId": 12,
        "name": "Obstacle Region 3",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 571.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-20.0, 3000.0],
                        [20.0, 3000.0],
                        [20.0, 3040.0],
                        [-20.0, 3040.0],
                        [-20.0, 3000.0],
                    ]
                ]
            ],
        },
    }

    result = LocBuildingRestrictionZoneRegion3Rule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert result.rule_code == "loc_building_restriction_zone_region_3"
    assert result.zone_code == LOC_BUILDING_RESTRICTION_ZONE["zone_code"]
    assert result.region_code == "3"
    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["worstAllowedHeightMeters"] < 571.0
    assert result.is_compliant is False


def test_loc_building_restriction_zone_region_3_rule_checks_non_vertex_worst_point() -> None:
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
        "obstacleId": 13,
        "name": "Obstacle Region 3 Edge Critical Point",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 501.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-550.0, 920.0],
                        [550.0, 920.0],
                        [550.0, 960.0],
                        [-550.0, 960.0],
                        [-550.0, 920.0],
                    ]
                ]
            ],
        },
    }

    result = LocBuildingRestrictionZoneRegion3Rule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert result.metrics["enteredProtectionZone"] is True
    assert result.metrics["worstAllowedHeightMeters"] is not None
    assert result.metrics["worstAllowedHeightMeters"] < 501.0
    assert result.is_compliant is False


def test_loc_building_restriction_zone_region_3_bind_uses_shared_context_and_region_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    captured: dict[str, object] = {}

    original_build_shared_context = (
        loc_region_3_module.build_loc_building_restriction_zone_shared_context
    )
    original_build_region_3_geometry = (
        loc_region_3_module.build_loc_building_restriction_zone_region_3_geometry
    )

    def _record_shared_context(*, station_point: tuple[float, float], runway_context: dict[str, object]):
        captured["station_point"] = station_point
        captured["runway_context"] = runway_context
        return original_build_shared_context(
            station_point=station_point,
            runway_context=runway_context,
        )

    def _record_region_3_geometry(shared_context: object):
        captured["shared_context"] = shared_context
        return original_build_region_3_geometry(shared_context)

    monkeypatch.setattr(
        loc_region_3_module,
        "build_loc_building_restriction_zone_shared_context",
        _record_shared_context,
    )
    monkeypatch.setattr(
        loc_region_3_module,
        "build_loc_building_restriction_zone_region_3_geometry",
        _record_region_3_geometry,
    )

    bound_rule = LocBuildingRestrictionZoneRegion3Rule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

    assert captured["station_point"] == (0.0, 0.0)
    assert captured["runway_context"] is runway
    assert bound_rule.zone_geometry.apex_point == pytest.approx(
        captured["shared_context"].apex_point
    )
    assert bound_rule.protection_zone.local_geometry.equals(
        bound_rule.zone_geometry.local_geometry
    )


def test_loc_building_restriction_zone_region_3_bind_accepts_prebuilt_shared_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

    def _fail_build_shared_context(*args: object, **kwargs: object) -> object:
        raise AssertionError("shared context builder should not be used")

    monkeypatch.setattr(
        loc_region_3_module,
        "build_loc_building_restriction_zone_shared_context",
        _fail_build_shared_context,
    )

    bound_rule = LocBuildingRestrictionZoneRegion3Rule().bind(
        station=station,
        station_point=(999.0, 999.0),
        runway_context=runway,
        shared_context=shared_context,
    )

    assert bound_rule.zone_geometry.apex_point == pytest.approx(shared_context.apex_point)
    assert bound_rule.protection_zone.local_geometry.equals(
        build_loc_building_restriction_zone_region_3_geometry(
            shared_context
        ).local_geometry
    )


def test_loc_building_restriction_zone_region_3_helper_uses_intersection_edge_point_only() -> None:
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(0.0, 0.0),
        runway_context={
            "localCenterPoint": (0.0, 600.0),
            "directionDegrees": 180.0,
            "lengthMeters": 600.0,
            "widthMeters": 45.0,
        },
    )
    geometry = loc_region_3_module._build_region_3_analysis_geometry(
        shared_context=shared_context,
        region_3_geometry=build_loc_building_restriction_zone_region_3_geometry(
            shared_context
        ),
    )
    obstacle_geometry = MultiPolygon(
        [
            Polygon(
                [
                    (-550.0, 920.0),
                    (550.0, 920.0),
                    (550.0, 960.0),
                    (-550.0, 960.0),
                    (-550.0, 920.0),
                ]
            )
        ]
    )

    worst_allowed_height_meters = calculate_region_3_worst_allowed_height_meters(
        zone_geometry=geometry,
        obstacle_geometry=obstacle_geometry,
        station_altitude_meters=500.0,
    )

    assert worst_allowed_height_meters == pytest.approx(500.2, abs=0.05)


def test_loc_building_restriction_zone_region_3_helper_handles_boundary_only_intersection() -> None:
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(0.0, 0.0),
        runway_context={
            "localCenterPoint": (0.0, 600.0),
            "directionDegrees": 180.0,
            "lengthMeters": 600.0,
            "widthMeters": 45.0,
        },
    )
    geometry = loc_region_3_module._build_region_3_analysis_geometry(
        shared_context=shared_context,
        region_3_geometry=build_loc_building_restriction_zone_region_3_geometry(
            shared_context
        ),
    )
    obstacle_geometry = MultiPolygon(
        [
            Polygon(
                [
                    (-550.0, 900.0),
                    (550.0, 900.0),
                    (550.0, 880.0),
                    (-550.0, 880.0),
                    (-550.0, 900.0),
                ]
            )
        ]
    )

    intersection = obstacle_geometry.intersection(geometry.local_geometry)

    assert intersection.is_empty is False
    assert intersection.bounds[3] == pytest.approx(900.0)
    worst_allowed_height_meters = calculate_region_3_worst_allowed_height_meters(
        zone_geometry=geometry,
        obstacle_geometry=obstacle_geometry,
        station_altitude_meters=500.0,
    )

    assert worst_allowed_height_meters == pytest.approx(500.0)


def test_loc_building_restriction_zone_region_3_helper_keeps_root_edge_height_near_station_altitude() -> None:
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(0.0, 0.0),
        runway_context={
            "localCenterPoint": (0.0, 600.0),
            "directionDegrees": 180.0,
            "lengthMeters": 600.0,
            "widthMeters": 45.0,
        },
    )
    geometry = loc_region_3_module._build_region_3_analysis_geometry(
        shared_context=shared_context,
        region_3_geometry=build_loc_building_restriction_zone_region_3_geometry(
            shared_context
        ),
    )
    obstacle_geometry = MultiPolygon(
        [
            Polygon(
                [
                    (-520.0, 890.0),
                    (520.0, 890.0),
                    (520.0, 910.0),
                    (-520.0, 910.0),
                    (-520.0, 890.0),
                ]
            )
        ]
    )

    worst_allowed_height_meters = calculate_region_3_worst_allowed_height_meters(
        zone_geometry=geometry,
        obstacle_geometry=obstacle_geometry,
        station_altitude_meters=500.0,
    )

    assert worst_allowed_height_meters == pytest.approx(500.0, abs=0.05)


def test_loc_building_restriction_zone_region_3_helper_lifts_outer_arc_height_near_station_plus_70m() -> None:
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(0.0, 0.0),
        runway_context={
            "localCenterPoint": (0.0, 600.0),
            "directionDegrees": 180.0,
            "lengthMeters": 600.0,
            "widthMeters": 45.0,
        },
    )
    geometry = loc_region_3_module._build_region_3_analysis_geometry(
        shared_context=shared_context,
        region_3_geometry=build_loc_building_restriction_zone_region_3_geometry(
            shared_context
        ),
    )
    obstacle_geometry = MultiPolygon(
        [
            Polygon(
                [
                    (-80.0, 6880.0),
                    (80.0, 6880.0),
                    (80.0, 6905.0),
                    (-80.0, 6905.0),
                    (-80.0, 6880.0),
                ]
            )
        ]
    )

    worst_allowed_height_meters = calculate_region_3_worst_allowed_height_meters(
        zone_geometry=geometry,
        obstacle_geometry=obstacle_geometry,
        station_altitude_meters=500.0,
    )

    assert worst_allowed_height_meters == pytest.approx(570.0, abs=0.5)


def test_loc_building_restriction_zone_region_3_helper_uses_csharp_runway_project_formula_for_non_vertex_point() -> None:
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(0.0, 0.0),
        runway_context={
            "localCenterPoint": (0.0, 600.0),
            "directionDegrees": 180.0,
            "lengthMeters": 600.0,
            "widthMeters": 45.0,
        },
    )
    geometry = loc_region_3_module._build_region_3_analysis_geometry(
        shared_context=shared_context,
        region_3_geometry=build_loc_building_restriction_zone_region_3_geometry(
            shared_context
        ),
    )
    obstacle_geometry = MultiPolygon(
        [
            Polygon(
                [
                    (-1200.0, 4200.0),
                    (-800.0, 4200.0),
                    (-800.0, 4700.0),
                    (-1200.0, 4700.0),
                    (-1200.0, 4200.0),
                ]
            )
        ]
    )

    worst_allowed_height_meters = calculate_region_3_worst_allowed_height_meters(
        zone_geometry=geometry,
        obstacle_geometry=obstacle_geometry,
        station_altitude_meters=500.0,
    )

    assert worst_allowed_height_meters == pytest.approx(539.2, abs=0.5)


def test_loc_region_3_shared_geometry_helper_returns_expected_min_metric() -> None:
    result = evaluate_geometry_metric(
        geometry=Polygon(
            [
                (0.0, 0.0),
                (10.0, 10.0),
                (20.0, 0.0),
                (0.0, 0.0),
            ]
        ),
        point_metric=lambda point: point.y,
        collect_point_candidates=False,
    )

    assert result.min_metric == pytest.approx(0.0)


def test_loc_rule_profile_returns_active_region_1_to_region_4_zone_specs() -> None:
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

    payload = LocRuleProfile().analyze(
        station=station,
        obstacles=[],
        station_point=(0.0, 0.0),
        runways=[runway],
    )

    matching_zones = [
        zone
        for zone in payload.protection_zones
        if zone.zone_code == LOC_BUILDING_RESTRICTION_ZONE["zone_code"]
    ]
    assert {zone.region_code for zone in matching_zones} == {"1", "2", "3", "4"}


def test_loc_rule_profile_builds_building_restriction_shared_context_once_per_station(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    expected_shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(0.0, 0.0),
        runway_context=runway,
    )
    captured: dict[str, object] = {"bind_shared_contexts": []}

    def _record_shared_context(*, station_point: tuple[float, float], runway_context: dict[str, object]):
        captured["build_calls"] = int(captured.get("build_calls", 0)) + 1
        captured["station_point"] = station_point
        captured["runway_context"] = runway_context
        return expected_shared_context

    original_region_1_bind = LocBuildingRestrictionZoneRegion1Rule.bind
    original_region_2_bind = LocBuildingRestrictionZoneRegion2Rule.bind
    original_region_3_bind = LocBuildingRestrictionZoneRegion3Rule.bind
    original_region_4_bind = LocBuildingRestrictionZoneRegion4Rule.bind

    def _record_region_1_bind(self: object, **kwargs: object) -> object:
        captured["bind_shared_contexts"].append(kwargs.get("shared_context"))
        return original_region_1_bind(self, **kwargs)

    def _record_region_2_bind(self: object, **kwargs: object) -> object:
        captured["bind_shared_contexts"].append(kwargs.get("shared_context"))
        return original_region_2_bind(self, **kwargs)

    def _record_region_3_bind(self: object, **kwargs: object) -> object:
        captured["bind_shared_contexts"].append(kwargs.get("shared_context"))
        return original_region_3_bind(self, **kwargs)

    def _record_region_4_bind(self: object, **kwargs: object) -> object:
        captured["bind_shared_contexts"].append(kwargs.get("shared_context"))
        return original_region_4_bind(self, **kwargs)

    monkeypatch.setattr(
        loc_profile_module,
        "build_loc_building_restriction_zone_shared_context",
        _record_shared_context,
    )
    monkeypatch.setattr(
        LocBuildingRestrictionZoneRegion1Rule,
        "bind",
        _record_region_1_bind,
    )
    monkeypatch.setattr(
        LocBuildingRestrictionZoneRegion2Rule,
        "bind",
        _record_region_2_bind,
    )
    monkeypatch.setattr(
        LocBuildingRestrictionZoneRegion3Rule,
        "bind",
        _record_region_3_bind,
    )
    monkeypatch.setattr(
        LocBuildingRestrictionZoneRegion4Rule,
        "bind",
        _record_region_4_bind,
    )

    payload = LocRuleProfile().analyze(
        station=station,
        obstacles=[],
        station_point=(0.0, 0.0),
        runways=[runway],
    )

    assert captured["build_calls"] == 1
    assert captured["station_point"] == (0.0, 0.0)
    assert captured["runway_context"] is runway
    assert captured["bind_shared_contexts"] == [
        expected_shared_context,
        expected_shared_context,
        expected_shared_context,
        expected_shared_context,
    ]
    matching_zones = [
        zone
        for zone in payload.protection_zones
        if zone.zone_code == LOC_BUILDING_RESTRICTION_ZONE["zone_code"]
    ]
    assert {zone.region_code for zone in matching_zones} == {"1", "2", "3", "4"}


def test_loc_run_area_rule_group_exposes_shared_supported_categories_declaration() -> None:
    assert loc_run_area_protection_module.SUPPORTED_CATEGORIES == {
        "vehicle_or_aircraft_or_machine",
    }


def test_loc_building_restriction_rule_group_exposes_shared_supported_categories_declaration() -> None:
    assert loc_building_restriction_module.SUPPORTED_CATEGORIES == {
        "building_general",
        "building_hangar",
        "building_terminal",
    }


def test_loc_rule_profile_prebind_gating_follows_patched_rule_group_declarations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    station = _make_loc_profile_station()
    runway = _make_loc_profile_runway(maximum_airworthiness=1.0)
    obstacles = [
        {
            "obstacleId": 801,
            "name": "Patched Run Area Obstacle",
            "rawObstacleType": "山丘",
            "globalObstacleCategory": "hill",
            "topElevation": 505.0,
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [[[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0], [-1.0, -1.0]]]
                ],
            },
        },
        {
            "obstacleId": 802,
            "name": "Patched Building Obstacle",
            "rawObstacleType": "树木",
            "globalObstacleCategory": "tree",
            "topElevation": 506.0,
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [[[-2.0, -2.0], [2.0, -2.0], [2.0, 2.0], [-2.0, 2.0], [-2.0, -2.0]]]
                ],
            },
        },
    ]
    calls = {
        "run_area_builder": 0,
        "building_builder": 0,
    }

    monkeypatch.setattr(
        loc_run_area_protection_module,
        "SUPPORTED_CATEGORIES",
        {"hill"},
        raising=False,
    )
    monkeypatch.setattr(
        loc_building_restriction_module,
        "SUPPORTED_CATEGORIES",
        {"tree"},
        raising=False,
    )

    def _fake_site_bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
        runway_context: dict[str, object],
    ) -> BoundObstacleRule:
        return _make_fake_bound_rule(
            rule_code="loc_site_protection",
            zone_code="loc_site_protection",
            region_code="default",
        )

    def _record_run_area_builder(
        *,
        station: object,
        station_point: tuple[float, float],
        runway_context: dict[str, object],
    ) -> object:
        calls["run_area_builder"] += 1
        return object()

    def _record_building_builder(
        *, station_point: tuple[float, float], runway_context: dict[str, object]
    ) -> object:
        calls["building_builder"] += 1
        return object()

    def _fake_run_area_bind(self: object, **kwargs: object) -> BoundObstacleRule:
        return _make_fake_bound_rule(
            rule_code="loc_run_area_protection_region_a",
            zone_code="loc_run_area_protection",
            region_code="A",
        )

    def _fake_building_bind(self: object, **kwargs: object) -> BoundObstacleRule:
        return _make_fake_bound_rule(
            rule_code="loc_building_restriction_zone_region_1",
            zone_code="loc_building_restriction_zone",
            region_code="1",
        )

    monkeypatch.setattr(loc_profile_module.LocSiteProtectionRule, "bind", _fake_site_bind)
    monkeypatch.setattr(
        loc_profile_module,
        "build_loc_run_area_shared_context",
        _record_run_area_builder,
    )
    monkeypatch.setattr(
        loc_profile_module,
        "build_loc_building_restriction_zone_shared_context",
        _record_building_builder,
    )
    monkeypatch.setattr(LocRunAreaProtectionRegionARule, "bind", _fake_run_area_bind)
    monkeypatch.setattr(
        loc_profile_module.LocRunAreaProtectionRegionBRule,
        "bind",
        _fake_run_area_bind,
    )
    monkeypatch.setattr(LocRunAreaProtectionRegionCRule, "bind", _fake_run_area_bind)
    monkeypatch.setattr(
        loc_profile_module.LocRunAreaProtectionRegionDRule,
        "bind",
        _fake_run_area_bind,
    )
    monkeypatch.setattr(
        LocBuildingRestrictionZoneRegion1Rule,
        "bind",
        _fake_building_bind,
    )
    monkeypatch.setattr(
        LocBuildingRestrictionZoneRegion2Rule,
        "bind",
        _fake_building_bind,
    )
    monkeypatch.setattr(
        LocBuildingRestrictionZoneRegion3Rule,
        "bind",
        _fake_building_bind,
    )
    monkeypatch.setattr(
        LocBuildingRestrictionZoneRegion4Rule,
        "bind",
        _fake_building_bind,
    )

    LocRuleProfile().analyze(
        station=station,
        obstacles=obstacles,
        station_point=(0.0, 0.0),
        runways=[runway],
    )

    assert calls["run_area_builder"] == 1
    assert calls["building_builder"] == 1


def test_loc_building_restriction_zone_region_4_rule_allows_obstacle_within_zone_at_station_height() -> None:
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
        "obstacleId": 14,
        "name": "Obstacle Region 4 Allowed",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 500.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-20.0, 100.0],
                        [20.0, 100.0],
                        [20.0, 140.0],
                        [-20.0, 140.0],
                        [-20.0, 100.0],
                    ]
                ]
            ],
        },
    }

    result = LocBuildingRestrictionZoneRegion4Rule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert result.metrics["enteredProtectionZone"] is True
    assert result.is_compliant is True
    assert result.message == "obstacle within region 4 and below allowed height"


def test_loc_building_restriction_zone_region_4_bind_uses_shared_context_and_region_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    captured: dict[str, object] = {}

    original_build_shared_context = (
        loc_region_4_module.build_loc_building_restriction_zone_shared_context
    )
    original_build_region_4_geometry = (
        loc_region_4_module.build_loc_building_restriction_zone_region_4_geometry
    )

    def _record_shared_context(*, station_point: tuple[float, float], runway_context: dict[str, object]):
        captured["station_point"] = station_point
        captured["runway_context"] = runway_context
        return original_build_shared_context(
            station_point=station_point,
            runway_context=runway_context,
        )

    def _record_region_4_geometry(shared_context: object):
        captured["shared_context"] = shared_context
        return original_build_region_4_geometry(shared_context)

    monkeypatch.setattr(
        loc_region_4_module,
        "build_loc_building_restriction_zone_shared_context",
        _record_shared_context,
    )
    monkeypatch.setattr(
        loc_region_4_module,
        "build_loc_building_restriction_zone_region_4_geometry",
        _record_region_4_geometry,
    )

    bound_rule = LocBuildingRestrictionZoneRegion4Rule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

    assert captured["station_point"] == (0.0, 0.0)
    assert captured["runway_context"] is runway
    assert bound_rule.protection_zone.local_geometry.bounds == pytest.approx(
        original_build_region_4_geometry(captured["shared_context"]).local_geometry.bounds
    )


def test_loc_building_restriction_zone_region_4_bind_accepts_prebuilt_shared_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

    def _fail_build_shared_context(*args: object, **kwargs: object) -> object:
        raise AssertionError("shared context builder should not be used")

    monkeypatch.setattr(
        loc_region_4_module,
        "build_loc_building_restriction_zone_shared_context",
        _fail_build_shared_context,
    )

    bound_rule = LocBuildingRestrictionZoneRegion4Rule().bind(
        station=station,
        station_point=(999.0, 999.0),
        runway_context=runway,
        shared_context=shared_context,
    )

    assert bound_rule.protection_zone.local_geometry.equals(
        build_loc_building_restriction_zone_region_4_geometry(
            shared_context
        ).local_geometry
    )


def test_loc_building_restriction_zone_region_1_bind_uses_shared_context_and_region_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    captured: dict[str, object] = {}

    original_build_shared_context = (
        loc_region_1_module.build_loc_building_restriction_zone_shared_context
    )
    original_build_region_1_geometry = (
        loc_region_1_module.build_loc_building_restriction_zone_region_1_geometry
    )

    def _record_shared_context(
        *, station_point: tuple[float, float], runway_context: dict[str, object]
    ):
        captured["station_point"] = station_point
        captured["runway_context"] = runway_context
        return original_build_shared_context(
            station_point=station_point,
            runway_context=runway_context,
        )

    def _record_region_1_geometry(shared_context: object):
        captured["shared_context"] = shared_context
        return original_build_region_1_geometry(shared_context)

    monkeypatch.setattr(
        loc_region_1_module,
        "build_loc_building_restriction_zone_shared_context",
        _record_shared_context,
    )
    monkeypatch.setattr(
        loc_region_1_module,
        "build_loc_building_restriction_zone_region_1_geometry",
        _record_region_1_geometry,
    )

    bound_rule = LocBuildingRestrictionZoneRegion1Rule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

    assert captured["station_point"] == (0.0, 0.0)
    assert captured["runway_context"] is runway
    assert bound_rule.protection_zone.local_geometry.equals(
        original_build_region_1_geometry(captured["shared_context"]).local_geometry
    )


def test_loc_building_restriction_zone_region_1_bind_accepts_prebuilt_shared_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

    def _fail_build_shared_context(*args: object, **kwargs: object) -> object:
        raise AssertionError("shared context builder should not be used")

    monkeypatch.setattr(
        loc_region_1_module,
        "build_loc_building_restriction_zone_shared_context",
        _fail_build_shared_context,
    )

    bound_rule = LocBuildingRestrictionZoneRegion1Rule().bind(
        station=station,
        station_point=(999.0, 999.0),
        runway_context=runway,
        shared_context=shared_context,
    )

    assert bound_rule.protection_zone.local_geometry.equals(
        build_loc_building_restriction_zone_region_1_geometry(
            shared_context
        ).local_geometry
    )


def test_loc_building_restriction_zone_region_2_bind_uses_shared_context_and_region_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    captured: dict[str, object] = {}

    original_build_shared_context = (
        loc_region_2_module.build_loc_building_restriction_zone_shared_context
    )
    original_build_region_2_geometry = (
        loc_region_2_module.build_loc_building_restriction_zone_region_2_geometry
    )

    def _record_shared_context(
        *, station_point: tuple[float, float], runway_context: dict[str, object]
    ):
        captured["station_point"] = station_point
        captured["runway_context"] = runway_context
        return original_build_shared_context(
            station_point=station_point,
            runway_context=runway_context,
        )

    def _record_region_2_geometry(shared_context: object):
        captured["shared_context"] = shared_context
        return original_build_region_2_geometry(shared_context)

    monkeypatch.setattr(
        loc_region_2_module,
        "build_loc_building_restriction_zone_shared_context",
        _record_shared_context,
    )
    monkeypatch.setattr(
        loc_region_2_module,
        "build_loc_building_restriction_zone_region_2_geometry",
        _record_region_2_geometry,
    )

    bound_rule = LocBuildingRestrictionZoneRegion2Rule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

    assert captured["station_point"] == (0.0, 0.0)
    assert captured["runway_context"] is runway
    assert bound_rule.protection_zone.local_geometry.equals(
        original_build_region_2_geometry(captured["shared_context"]).local_geometry
    )


def test_loc_building_restriction_zone_region_2_bind_accepts_prebuilt_shared_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    shared_context = build_loc_building_restriction_zone_shared_context(
        station_point=(0.0, 0.0),
        runway_context=runway,
    )

    def _fail_build_shared_context(*args: object, **kwargs: object) -> object:
        raise AssertionError("shared context builder should not be used")

    monkeypatch.setattr(
        loc_region_2_module,
        "build_loc_building_restriction_zone_shared_context",
        _fail_build_shared_context,
    )

    bound_rule = LocBuildingRestrictionZoneRegion2Rule().bind(
        station=station,
        station_point=(999.0, 999.0),
        runway_context=runway,
        shared_context=shared_context,
    )

    assert bound_rule.protection_zone.local_geometry.equals(
        build_loc_building_restriction_zone_region_2_geometry(
            shared_context
        ).local_geometry
    )


def test_loc_building_restriction_zone_region_4_rule_rejects_obstacle_within_zone_above_station_height() -> None:
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
        "obstacleId": 15,
        "name": "Obstacle Region 4 Rejected",
        "rawObstacleType": "建筑物/构建物",
        "globalObstacleCategory": "building_general",
        "topElevation": 501.0,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-20.0, 100.0],
                        [20.0, 100.0],
                        [20.0, 140.0],
                        [-20.0, 140.0],
                        [-20.0, 100.0],
                    ]
                ]
            ],
        },
    }

    result = LocBuildingRestrictionZoneRegion4Rule().bind(
        station=station,
        station_point=(0.0, 0.0),
        runway_context=runway,
    ).analyze(obstacle)

    assert result.metrics["enteredProtectionZone"] is True
    assert result.is_compliant is False
    assert result.message == "obstacle within region 4 above allowed height"
