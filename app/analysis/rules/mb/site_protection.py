import math
from dataclasses import dataclass

from shapely.geometry import Point, Polygon

from app.analysis.config import PROTECTION_ZONE_BUILDER_DISCRETIZATION
from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.result_helpers import (
    compute_azimuth_degrees,
    compute_horizontal_angle_range_from_geometry,
)
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import ensure_multipolygon, resolve_obstacle_shape
from app.analysis.rules.mb.config import MB_SITE_PROTECTION
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


def _normalize_degrees(value: float) -> float:
    return value % 360.0


def _build_sector_polygon(
    *,
    center_point: tuple[float, float],
    radius_m: float,
    start_azimuth_deg: float,
    end_azimuth_deg: float,
) -> Polygon:
    step_degrees = float(PROTECTION_ZONE_BUILDER_DISCRETIZATION["sector_step_degrees"])
    start = _normalize_degrees(start_azimuth_deg)
    end = _normalize_degrees(end_azimuth_deg)
    if end <= start:
        end += 360.0

    center_x, center_y = center_point
    ring: list[tuple[float, float]] = [(center_x, center_y)]
    current = start
    while current < end:
        radians = math.radians(current)
        ring.append(
            (
                center_x + radius_m * math.sin(radians),
                center_y + radius_m * math.cos(radians),
            )
        )
        current += step_degrees

    end_radians = math.radians(end)
    ring.append(
        (
            center_x + radius_m * math.sin(end_radians),
            center_y + radius_m * math.cos(end_radians),
        )
    )
    ring.append((center_x, center_y))
    return Polygon(ring)


@dataclass(slots=True)
class BoundMbSiteProtectionRule(BoundObstacleRule):
    station: object
    station_point: tuple[float, float]
    limit_angle_degrees: float
    radius_meters: float

    # 执行已绑定的 MB 场地保护区判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(
            self.protection_zone.local_geometry
        )
        station_shape = Point(self.station_point)
        min_distance_meters = float(obstacle_shape.distance(station_shape))
        distance_for_angle = max(min_distance_meters, 0.001)
        base_height_meters = float(getattr(self.station, "altitude", 0.0) or 0.0)
        top_elevation_meters = float(
            obstacle.get("topElevation")
            if obstacle.get("topElevation") is not None
            else base_height_meters
        )
        allowed_height_meters = base_height_meters + math.tan(
            math.radians(self.limit_angle_degrees)
        ) * min_distance_meters
        vertical_angle_degrees = math.degrees(
            math.atan((top_elevation_meters - base_height_meters) / distance_for_angle)
        )

        centroid = obstacle_shape.centroid
        azimuth_degrees = compute_azimuth_degrees(
            self.station_point[0], self.station_point[1], centroid.x, centroid.y
        )
        min_horizontal_angle_degrees, max_horizontal_angle_degrees = (
            compute_horizontal_angle_range_from_geometry(self.station_point, obstacle_shape)
        )
        relative_height_meters = top_elevation_meters - base_height_meters

        if not entered_protection_zone:
            is_compliant = True
            message = "obstacle outside MB site protection region"
            details = "障碍物位于保护区外。"
        else:
            is_compliant = vertical_angle_degrees <= self.limit_angle_degrees
            message = (
                "obstacle within MB site protection limit"
                if is_compliant
                else "obstacle exceeds MB site protection limit"
            )
            details = f"障碍物{'满足' if is_compliant else '不满足'}仰角限制要求。"

        return AnalysisRuleResult(
            station_id=self.protection_zone.station_id,
            station_type=self.protection_zone.station_type,
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=(
                None
                if obstacle.get("rawObstacleType") is None
                else str(obstacle["rawObstacleType"])
            ),
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
            over_distance_meters=0.0,
            metrics={
                "enteredProtectionZone": entered_protection_zone,
                "minDistanceMeters": min_distance_meters,
                "allowedHeightMeters": allowed_height_meters,
                "topElevationMeters": top_elevation_meters,
                "verticalAngleDegrees": vertical_angle_degrees,
                "limitAngleDegrees": self.limit_angle_degrees,
                "radiusMeters": self.radius_meters,
            },
            azimuth_degrees=azimuth_degrees,
            max_horizontal_angle_degrees=max_horizontal_angle_degrees,
            min_horizontal_angle_degrees=min_horizontal_angle_degrees,
            relative_height_meters=relative_height_meters,
            is_in_radius=entered_protection_zone,
            is_in_zone=entered_protection_zone,
            details=details,
        )


class MbSiteProtectionRule(ObstacleRule):
    rule_code = "mb_site_protection"
    rule_name = "mb_site_protection"
    zone_code = str(MB_SITE_PROTECTION["zone_code"])

    # 初始化 MB 场地保护区规则。
    def __init__(self) -> None:
        self.zone_name = resolve_protection_zone_name(zone_code=self.zone_code)

    # 绑定单个 MB 分区保护区。
    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
        runway_direction_degrees: float,
        region_definition: dict[str, object],
    ) -> BoundMbSiteProtectionRule:
        radius_meters = float(MB_SITE_PROTECTION["radius_m"])
        limit_angle_degrees = float(region_definition["limit_angle_deg"])
        local_geometry = ensure_multipolygon(
            _build_sector_polygon(
                center_point=station_point,
                radius_m=radius_meters,
                start_azimuth_deg=(
                    runway_direction_degrees
                    + float(region_definition["start_offset_deg"])
                ),
                end_azimuth_deg=(
                    runway_direction_degrees
                    + float(region_definition["end_offset_deg"])
                ),
            )
        )
        base_height_meters = float(getattr(station, "altitude", 0.0) or 0.0)
        longitude = getattr(station, "longitude", None)
        latitude = getattr(station, "latitude", None)
        return BoundMbSiteProtectionRule(
            protection_zone=build_protection_zone_spec(
                station_id=int(station.id),
                station_type=str(station.station_type),
                rule_code=str(region_definition["rule_code"]),
                rule_name=str(region_definition["rule_name"]),
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                region_code=str(region_definition["region_code"]),
                region_name=str(region_definition["region_name"]),
                local_geometry=local_geometry,
                vertical_definition={
                    "mode": "analytic_surface",
                    "baseReference": "station",
                    "baseHeightMeters": base_height_meters,
                    "surface": {
                        "distanceSource": {
                            "kind": "point",
                            "point": [float(longitude), float(latitude)]
                            if longitude is not None and latitude is not None
                            else None,
                        },
                        "distanceMetric": "radial",
                        "clampRange": {
                            "startMeters": 0.0,
                            "endMeters": radius_meters,
                        },
                        "heightModel": {
                            "type": "angle_linear_rise",
                            "angleDegrees": limit_angle_degrees,
                            "distanceOffsetMeters": 0.0,
                        },
                    },
                },
            ),
            station=station,
            station_point=station_point,
            limit_angle_degrees=limit_angle_degrees,
            radius_meters=radius_meters,
        )


__all__ = [
    "BoundMbSiteProtectionRule",
    "MbSiteProtectionRule",
]
