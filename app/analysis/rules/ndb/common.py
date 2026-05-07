import math
from dataclasses import dataclass
from typing import Iterator

from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.base import BaseGeometry

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import build_circle_polygon, ensure_multipolygon, resolve_obstacle_shape
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


class NdbRule(ObstacleRule):
    # 绑定单个 NDB 台站上下文。
    def bind(self, *args, **kwargs) -> BoundObstacleRule:  # pragma: no cover
        raise NotImplementedError


@dataclass(slots=True)
class BoundNdbMinimumDistanceRule(BoundObstacleRule):
    station_point: tuple[float, float]
    required_distance_meters: float

    # 执行已绑定的 NDB 最小间距判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(
            self.protection_zone.local_geometry
        )
        actual_distance_meters = float(obstacle_shape.distance(Point(self.station_point)))
        is_compliant = not entered_protection_zone
        return AnalysisRuleResult(
            station_id=self.protection_zone.station_id,
            station_type=self.protection_zone.station_type,
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=obstacle["rawObstacleType"],
            global_obstacle_category=str(obstacle["globalObstacleCategory"]),
            rule_code=self.protection_zone.rule_code,
            rule_name=self.protection_zone.rule_name,
            zone_code=self.protection_zone.zone_code,
            zone_name=self.protection_zone.zone_name,
            region_code=self.protection_zone.region_code,
            region_name=self.protection_zone.region_name,
            is_applicable=True,
            is_compliant=is_compliant,
            message=(
                "distance meets minimum threshold"
                if is_compliant
                else "distance below required threshold"
            ),
            metrics={
                "enteredProtectionZone": entered_protection_zone,
                "actualDistanceMeters": actual_distance_meters,
                "requiredDistanceMeters": self.required_distance_meters,
            },
            standards_rule_code=self.protection_zone.rule_code,
        )


@dataclass(slots=True)
class BoundNdbConicalClearanceRule(BoundObstacleRule):
    station_point: tuple[float, float]
    station_altitude: float | None
    inner_radius_meters: float
    outer_radius_meters: float
    elevation_angle_degrees: float

    # 执行已绑定的 NDB 锥形净空判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_geometry = obstacle_shape.intersection(self.protection_zone.local_geometry)
        entered_protection_zone = (
            not entered_geometry.is_empty
            and _calculate_max_distance_to_station(
                geometry=obstacle_shape,
                station_point=self.station_point,
            )
            > self.inner_radius_meters
        )
        actual_distance_meters = float(obstacle_shape.distance(Point(self.station_point)))
        base_height_meters = float(self.station_altitude or 0.0)
        raw_top_elevation = obstacle.get("topElevation")
        top_elevation = float(
            base_height_meters if raw_top_elevation is None else raw_top_elevation
        )
        actual_elevation_angle_degrees = 90.0
        if actual_distance_meters > 0.0:
            actual_elevation_angle_degrees = math.degrees(
                math.atan(
                    (top_elevation - base_height_meters) / actual_distance_meters
                )
            )

        allowed_height_meters = base_height_meters
        is_compliant = True
        message = "top elevation outside conical clearance band"
        if entered_protection_zone:
            allowed_height_meters = base_height_meters + math.tan(
                math.radians(self.elevation_angle_degrees)
            ) * actual_distance_meters
            is_compliant = (
                actual_elevation_angle_degrees <= self.elevation_angle_degrees
            )
            message = (
                "top elevation within conical clearance"
                if is_compliant
                else "top elevation exceeds conical clearance"
            )

        return AnalysisRuleResult(
            station_id=self.protection_zone.station_id,
            station_type=self.protection_zone.station_type,
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=obstacle["rawObstacleType"],
            global_obstacle_category=str(obstacle["globalObstacleCategory"]),
            rule_code=self.protection_zone.rule_code,
            rule_name=self.protection_zone.rule_name,
            zone_code=self.protection_zone.zone_code,
            zone_name=self.protection_zone.zone_name,
            region_code=self.protection_zone.region_code,
            region_name=self.protection_zone.region_name,
            is_applicable=True,
            is_compliant=is_compliant,
            message=message,
            metrics={
                "enteredProtectionZone": entered_protection_zone,
                "actualDistanceMeters": actual_distance_meters,
                "actualElevationAngleDegrees": actual_elevation_angle_degrees,
                "baseHeightMeters": base_height_meters,
                "elevationAngleDegrees": self.elevation_angle_degrees,
                "allowedHeightMeters": allowed_height_meters,
                "topElevationMeters": top_elevation,
                "innerRadiusMeters": self.inner_radius_meters,
                "outerRadiusMeters": self.outer_radius_meters,
            },
            standards_rule_code=self.protection_zone.rule_code,
        )


# 构建 NDB 圆形保护区规格。
def build_ndb_circle_protection_zone(
    *,
    station: object,
    rule_code: str,
    rule_name: str,
    zone_code: str,
    zone_name: str,
    station_point: tuple[float, float],
    radius_meters: float,
) -> ProtectionZoneSpec:
    protection_zone = ensure_multipolygon(
        build_circle_polygon(
            center_point=station_point,
            radius_meters=radius_meters,
        )
    )
    return build_protection_zone_spec(
        station_id=int(station.id),
        station_type=str(station.station_type),
        rule_code=rule_code,
        rule_name=rule_name,
        zone_code=zone_code,
        zone_name=zone_name,
        region_code="default",
        region_name="default",
        local_geometry=protection_zone,
        vertical_definition={
            "mode": "flat",
            "baseReference": "station",
            "baseHeightMeters": 0.0,
        },
    )


def _calculate_max_distance_to_station(
    *,
    geometry: BaseGeometry,
    station_point: tuple[float, float],
) -> float:
    station_x, station_y = station_point
    max_distance = 0.0
    for point_x, point_y in _iter_geometry_points(geometry):
        max_distance = max(
            max_distance,
            math.hypot(point_x - station_x, point_y - station_y),
        )
    return max_distance


def _iter_geometry_points(geometry: BaseGeometry) -> Iterator[tuple[float, float]]:
    if isinstance(geometry, (Point, LineString)):
        yield from ((float(point_x), float(point_y)) for point_x, point_y in geometry.coords)
        return
    if isinstance(geometry, Polygon):
        yield from (
            (float(point_x), float(point_y))
            for point_x, point_y in geometry.exterior.coords
        )
        for interior in geometry.interiors:
            yield from (
                (float(point_x), float(point_y))
                for point_x, point_y in interior.coords
            )
        return
    if hasattr(geometry, "geoms"):
        for child_geometry in geometry.geoms:
            yield from _iter_geometry_points(child_geometry)


# 构建 NDB 锥形环带保护区规格。
def build_ndb_conical_protection_zone(
    *,
    station: object,
    rule_code: str,
    rule_name: str,
    zone_code: str,
    zone_name: str,
    station_point: tuple[float, float],
    station_altitude: float | None,
    inner_radius_meters: float,
    outer_radius_meters: float,
    elevation_angle_degrees: float,
) -> ProtectionZoneSpec:
    outer_zone = build_circle_polygon(
        center_point=station_point,
        radius_meters=outer_radius_meters,
    )
    inner_zone = build_circle_polygon(
        center_point=station_point,
        radius_meters=inner_radius_meters,
    )
    protection_zone = ensure_multipolygon(outer_zone.difference(inner_zone))
    base_height_meters = float(station_altitude or 0.0)
    return build_protection_zone_spec(
        station_id=int(station.id),
        station_type=str(station.station_type),
        rule_code=rule_code,
        rule_name=rule_name,
        zone_code=zone_code,
        zone_name=zone_name,
        region_code="default",
        region_name="default",
        local_geometry=protection_zone,
        vertical_definition={
            "mode": "analytic_surface",
            "baseReference": "station",
            "baseHeightMeters": base_height_meters,
            "surface": {
                "distanceSource": {
                    "kind": "point",
                    "point": [
                        float(getattr(station, "longitude")),
                        float(getattr(station, "latitude")),
                    ]
                    if getattr(station, "longitude", None) is not None
                    and getattr(station, "latitude", None) is not None
                    else None,
                },
                "distanceMetric": "radial",
                "clampRange": {
                    "startMeters": inner_radius_meters,
                    "endMeters": outer_radius_meters,
                },
                "heightModel": {
                    "type": "angle_linear_rise",
                    "angleDegrees": elevation_angle_degrees,
                    "distanceOffsetMeters": 0.0,
                },
            },
        },
    )
