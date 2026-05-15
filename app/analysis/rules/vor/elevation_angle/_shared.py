import math
from dataclasses import dataclass

from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry

from app.analysis.result_helpers import (
    _iter_boundary_coordinates,
    _normalize_azimuth_degrees,
    compute_azimuth_degrees,
    compute_horizontal_angle_range_from_geometry,
    compute_horizontal_angular_width,
)
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.vor.common import _float_or_none, build_vor_ring_protection_zone



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
        actual_distance = float(shape.distance(Point(self.station_point)))

        raw_top = obstacle.get("topElevation")
        top_elevation = float(raw_top if raw_top is not None else 0.0)
        height_diff = top_elevation - self.base_height

        obstacle_centroid = shape.centroid
        az = compute_azimuth_degrees(
            self.station_point[0], self.station_point[1],
            obstacle_centroid.x, obstacle_centroid.y,
        )
        min_h, max_h = compute_horizontal_angle_range_from_geometry(
            self.station_point, shape,
        )

        allowed_height_meters = (
            self.base_height
            + math.tan(math.radians(self.limit_angle_degrees)) * actual_distance
        )
        over_height_meters = max(0.0, top_elevation - allowed_height_meters)

        metrics: dict[str, object] = {
            "enteredProtectionZone": entered,
            "actualDistanceMeters": actual_distance,
            "topElevationMeters": top_elevation,
            "heightDiffMeters": height_diff,
            "baseHeightMeters": self.base_height,
            "innerRadiusMeters": self.inner_radius_m,
            "outerRadiusMeters": self.outer_radius_m,
            "limitAngleDegrees": self.limit_angle_degrees,
            "allowedHeightMeters": allowed_height_meters,
            "overHeightMeters": over_height_meters,
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
                message=f"不在VOR {self.inner_radius_m}-{self.outer_radius_m}m仰角限制范围内",
                metrics=metrics,
                standards_rule_code=self.protection_zone.rule_code,
                over_distance_meters=0.0,
                azimuth_degrees=az,
                max_horizontal_angle_degrees=max_h,
                min_horizontal_angle_degrees=min_h,
                relative_height_meters=height_diff,
                is_in_radius=entered,
                is_in_zone=entered,
                details="障碍物未进入仰角限制区。",
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
                message="障碍物低于基准面",
                metrics=metrics,
                standards_rule_code=self.protection_zone.rule_code,
                over_distance_meters=0.0,
                azimuth_degrees=az,
                max_horizontal_angle_degrees=max_h,
                min_horizontal_angle_degrees=min_h,
                relative_height_meters=height_diff,
                is_in_radius=entered,
                is_in_zone=entered,
                details="障碍物低于基准面，满足仰角要求。",
            )

        vertical_angle = math.degrees(math.atan(height_diff / max(actual_distance, 0.001)))
        metrics["verticalAngleDegrees"] = vertical_angle

        if vertical_angle > self.limit_angle_degrees:
            v_angle = round(vertical_angle, 2)
            if self.protection_zone.zone_code == "vor_300_outside_2_5_deg":
                message = f"与基准面形成的垂直仰角为{v_angle}°"
            else:
                hw = compute_horizontal_angular_width(
                    shape=shape,
                    station_point=self.station_point,
                )
                h_angle = round(hw, 2)
                message = f"与基准面形成的垂直仰角为{v_angle}°,超出基准面高度的水平张角为{h_angle}°"
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
                message=message,
                metrics=metrics,
                standards_rule_code=self.protection_zone.rule_code,
                over_distance_meters=0.0,
                azimuth_degrees=az,
                max_horizontal_angle_degrees=max_h,
                min_horizontal_angle_degrees=min_h,
                relative_height_meters=height_diff,
                is_in_radius=entered,
                is_in_zone=entered,
                details=f"不满足仰角限制要求，实际仰角{round(vertical_angle,2)}°，限值{self.limit_angle_degrees}°。",
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
                        "与基准面形成的垂直仰角为"
                        f"{round(vertical_angle, 2)}°,超出基准面高度的水平张角为"
                        f"{round(horizontal_width, 2)}°"
                    ),
                    metrics=metrics,
                    standards_rule_code=self.protection_zone.rule_code,
                    over_distance_meters=0.0,
                    azimuth_degrees=az,
                    max_horizontal_angle_degrees=max_h,
                    min_horizontal_angle_degrees=min_h,
                    relative_height_meters=height_diff,
                    is_in_radius=entered,
                    is_in_zone=entered,
                    details=f"不满足水平角限制要求，实际水平角{round(horizontal_width,2)}°，限值{self.horizontal_angle_limit_degrees}°。",
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
            message=(
                "与基准面形成的垂直仰角为"
                f"{round(vertical_angle, 2)}°,超出基准面高度的水平张角为"
                f"{round(horizontal_width, 2)}°"
            ) if self.horizontal_angle_limit_degrees is not None
            else f"与基准面形成的垂直仰角为{round(vertical_angle, 2)}°",
            metrics=metrics,
            standards_rule_code=self.protection_zone.rule_code,
            over_distance_meters=0.0,
            azimuth_degrees=az,
            max_horizontal_angle_degrees=max_h,
            min_horizontal_angle_degrees=min_h,
            relative_height_meters=height_diff,
            is_in_radius=entered,
            is_in_zone=entered,
            details=f"满足仰角限制要求，实际仰角{round(vertical_angle,2)}°，限值{self.limit_angle_degrees}°。",
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
