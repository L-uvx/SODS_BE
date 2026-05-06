import math
from dataclasses import dataclass

from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry

from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.vor.common import _float_or_none, build_vor_ring_protection_zone


def _normalize_azimuth_degrees(angle: float) -> float:
    return angle % 360.0


def _iter_boundary_coordinates(shape: BaseGeometry):
    if isinstance(shape, Point):
        yield from shape.coords
        return

    if isinstance(shape, Polygon):
        yield from shape.exterior.coords
        return

    if isinstance(shape, MultiPolygon):
        for polygon in shape.geoms:
            yield from _iter_boundary_coordinates(polygon)
        return

    boundary = shape.boundary
    if hasattr(boundary, "geoms"):
        for boundary_part in boundary.geoms:
            yield from boundary_part.coords
        return

    yield from boundary.coords


# 计算障碍物相对台站点的最小包络水平夹角。
def compute_horizontal_angular_width(
    shape: BaseGeometry,
    station_point: tuple[float, float],
) -> float:
    sx, sy = station_point
    azimuths: list[float] = []
    for x, y in _iter_boundary_coordinates(shape):
        azimuth = math.degrees(math.atan2(y - sy, x - sx))
        azimuths.append(_normalize_azimuth_degrees(azimuth))

    if len(azimuths) <= 1:
        return 0.0

    azimuths.sort()
    gaps = [
        azimuths[index + 1] - azimuths[index]
        for index in range(len(azimuths) - 1)
    ]
    gaps.append((azimuths[0] + 360.0) - azimuths[-1])
    max_gap = max(gaps)
    return 360.0 - max_gap


@dataclass(slots=True)
class BoundVorElevationAngleRule(BoundObstacleRule):
    station_point: tuple[float, float]
    base_height: float
    limit_angle_degrees: float
    inner_radius_m: float
    outer_radius_m: float
    horizontal_angle_limit_degrees: float | None

    # 执行已绑定的 VOR 仰角限制区判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        shape = resolve_obstacle_shape(obstacle)
        entered = shape.intersects(self.protection_zone.local_geometry)
        min_distance = float(shape.distance(Point(self.station_point)))

        raw_top = obstacle.get("topElevation")
        top_elevation = float(raw_top if raw_top is not None else 0.0)
        height_diff = top_elevation - self.base_height

        metrics: dict[str, object] = {
            "enteredProtectionZone": entered,
            "minDistanceMeters": min_distance,
            "topElevationMeters": top_elevation,
            "heightDiffMeters": height_diff,
            "baseHeightMeters": self.base_height,
            "innerRadiusMeters": self.inner_radius_m,
            "outerRadiusMeters": self.outer_radius_m,
            "limitAngleDegrees": self.limit_angle_degrees,
        }

        if not entered:
            metrics["verticalAngleDegrees"] = None
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
                is_compliant=True,
                message="obstacle outside elevation angle zone",
                metrics=metrics,
                standards_rule_code=self.protection_zone.rule_code,
            )

        if height_diff <= 0:
            metrics["verticalAngleDegrees"] = 0.0
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
                is_compliant=True,
                message="obstacle below benchmark plane",
                metrics=metrics,
                standards_rule_code=self.protection_zone.rule_code,
            )

        vertical_angle = math.degrees(math.atan(height_diff / max(min_distance, 0.001)))
        metrics["verticalAngleDegrees"] = vertical_angle

        if vertical_angle > self.limit_angle_degrees:
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
                is_compliant=False,
                message=(
                    "obstacle exceeds elevation angle limit: "
                    f"{vertical_angle:.2f}deg > {self.limit_angle_degrees:.2f}deg"
                ),
                metrics=metrics,
                standards_rule_code=self.protection_zone.rule_code,
            )

        if self.horizontal_angle_limit_degrees is not None:
            horizontal_width = compute_horizontal_angular_width(
                shape=shape,
                station_point=self.station_point,
            )
            metrics["horizontalAngularWidthDegrees"] = horizontal_width
            if horizontal_width > self.horizontal_angle_limit_degrees:
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
                    is_compliant=False,
                    message=(
                        "obstacle exceeds horizontal angle limit: "
                        f"{horizontal_width:.2f}deg > "
                        f"{self.horizontal_angle_limit_degrees:.2f}deg"
                    ),
                    metrics=metrics,
                    standards_rule_code=self.protection_zone.rule_code,
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
            is_compliant=True,
            message="obstacle within elevation angle limit",
            metrics=metrics,
            standards_rule_code=self.protection_zone.rule_code,
        )


# 绑定 VOR 仰角限制区通用规则。
def bind_elevation_angle_rule(
    *,
    station: object,
    station_point: tuple[float, float],
    rule_code: str,
    rule_name: str,
    zone_code: str,
    zone_name: str,
    region_code: str,
    region_name: str,
    inner_radius_m: float,
    outer_radius_m: float,
    limit_angle_degrees: float,
    horizontal_angle_limit_degrees: float | None,
    bound_rule_cls: type[BoundVorElevationAngleRule] = BoundVorElevationAngleRule,
):
    altitude = _float_or_none(station.altitude)
    reflection_net_hag = _float_or_none(station.reflection_net_hag)
    if altitude is None or reflection_net_hag is None:
        return None

    base_height = float(altitude) + float(reflection_net_hag)
    protection_zone = build_vor_ring_protection_zone(
        station_id=int(station.id),
        station_type=str(station.station_type),
        rule_code=rule_code,
        rule_name=rule_name,
        zone_code=zone_code,
        zone_name=zone_name,
        region_code=region_code,
        region_name=region_name,
        station_point=station_point,
        inner_radius_m=inner_radius_m,
        outer_radius_m=outer_radius_m,
        base_height_meters=base_height,
        elevation_angle_degrees=limit_angle_degrees,
        distance_offset_meters=0.0,
        clamp_end_meters=outer_radius_m,
        longitude=float(station.longitude) if station.longitude is not None else None,
        latitude=float(station.latitude) if station.latitude is not None else None,
    )
    return bound_rule_cls(
        protection_zone=protection_zone,
        station_point=station_point,
        base_height=base_height,
        limit_angle_degrees=limit_angle_degrees,
        inner_radius_m=inner_radius_m,
        outer_radius_m=outer_radius_m,
        horizontal_angle_limit_degrees=horizontal_angle_limit_degrees,
    )
