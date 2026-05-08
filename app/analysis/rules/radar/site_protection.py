import math
from dataclasses import dataclass

from shapely.geometry import Point

from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.radar.common import RadarRule, build_radar_circle_protection_zone
from app.analysis.rules.base import BoundObstacleRule
from app.analysis.rules.vor.elevation_angle._shared import compute_horizontal_angular_width


@dataclass(slots=True)
class BoundRadarSiteProtectionRule(BoundObstacleRule):
    station_point: tuple[float, float]
    base_height_meters: float
    radius_meters: float
    vertical_limit_angle_degrees: float
    horizontal_limit_angle_degrees: float
    standards_rule_code: str

    # 执行已绑定的 Radar A 场地保护区判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(self.protection_zone.local_geometry)
        actual_distance_meters = float(obstacle_shape.distance(Point(self.station_point)))
        top_elevation_meters = float(
            obstacle.get("topElevation") if obstacle.get("topElevation") is not None else 0.0
        )
        horizontal_mask_angle_degrees = compute_horizontal_angular_width(
            shape=obstacle_shape,
            station_point=self.station_point,
        )

        metrics: dict[str, float | bool] = {
            "enteredProtectionZone": entered_protection_zone,
            "actualDistanceMeters": actual_distance_meters,
            "verticalMaskAngleDegrees": 0.0,
            "horizontalMaskAngleDegrees": horizontal_mask_angle_degrees,
            "verticalLimitAngleDegrees": self.vertical_limit_angle_degrees,
            "horizontalLimitAngleDegrees": self.horizontal_limit_angle_degrees,
            "limitHeightMeters": self.base_height_meters,
            "topElevationMeters": top_elevation_meters,
            "baseHeightMeters": self.base_height_meters,
        }

        if (not entered_protection_zone) or actual_distance_meters > self.radius_meters:
            return self._build_result(
                obstacle=obstacle,
                is_compliant=True,
                message="obstacle outside radar site protection zone",
                metrics=metrics,
            )

        distance_km = actual_distance_meters / 1000.0
        if actual_distance_meters <= 0.0:
            height_delta_meters = top_elevation_meters - self.base_height_meters
            vertical_mask_angle_degrees = 90.0 if height_delta_meters > 0.0 else 0.0
            limit_height_meters = self.base_height_meters
        else:
            vertical_mask_angle_degrees = math.degrees(
                math.atan(
                    ((top_elevation_meters - self.base_height_meters) / actual_distance_meters)
                    - (distance_km / 16970.0)
                )
            )
            limit_height_meters = (
                math.tan(math.radians(self.vertical_limit_angle_degrees) + (distance_km / 16970.0))
                * actual_distance_meters
                + self.base_height_meters
            )
        metrics["verticalMaskAngleDegrees"] = vertical_mask_angle_degrees
        metrics["limitHeightMeters"] = limit_height_meters

        is_compliant = not (
            vertical_mask_angle_degrees > self.vertical_limit_angle_degrees
            and horizontal_mask_angle_degrees > self.horizontal_limit_angle_degrees
        )
        message = (
            "obstacle exceeds radar site protection mask angles"
            if not is_compliant
            else "obstacle within radar site protection angle limits"
        )
        return self._build_result(
            obstacle=obstacle,
            is_compliant=is_compliant,
            message=message,
            metrics=metrics,
        )

    def _build_result(
        self,
        *,
        obstacle: dict[str, object],
        is_compliant: bool,
        message: str,
        metrics: dict[str, float | bool],
    ) -> AnalysisRuleResult:
        return AnalysisRuleResult(
            station_id=self.protection_zone.station_id,
            station_type=self.protection_zone.station_type,
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=(
                None if obstacle.get("rawObstacleType") is None else str(obstacle["rawObstacleType"])
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
            metrics=metrics,
            standards_rule_code=self.standards_rule_code,
        )


class RadarSiteProtectionRule(RadarRule):
    rule_code = "radar_site_protection"
    rule_name = "radar_site_protection"
    zone_code = "radar_site_protection"
    standards_rule_code = "radar_site_protection"

    # 初始化 Radar A 场地保护区规则。
    def __init__(self) -> None:
        self.zone_name = resolve_protection_zone_name(zone_code=self.zone_code)

    # 绑定单个 Radar A 圆形保护区。
    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
        radius_meters: float,
        vertical_limit_angle_degrees: float,
        horizontal_limit_angle_degrees: float,
    ) -> BoundRadarSiteProtectionRule | None:
        altitude = station.altitude
        antenna_hag = getattr(station, "antenna_hag", None)
        if altitude is None or antenna_hag is None:
            return None

        base_height_meters = float(altitude) + float(antenna_hag)
        return BoundRadarSiteProtectionRule(
            protection_zone=build_radar_circle_protection_zone(
                station=station,
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                station_point=station_point,
                radius_meters=radius_meters,
                vertical_definition={
                    "mode": "analytic_surface",
                    "baseReference": "station",
                    "baseHeightMeters": base_height_meters,
                    "surface": {
                        "type": "radial_cone_surface",
                        "distanceSource": {
                            "kind": "point",
                            "point": [
                                float(station.longitude),
                                float(station.latitude),
                            ]
                            if station.longitude is not None and station.latitude is not None
                            else None,
                        },
                        "distanceMetric": "radial",
                        "clampRange": {
                            "startMeters": 0.0,
                            "endMeters": float(radius_meters),
                        },
                        "heightModel": {
                            "type": "radar_site_protection_mask_angle",
                            "maskAngleDegrees": float(vertical_limit_angle_degrees),
                            "distanceOffsetMeters": 0.0,
                            "distanceKilometersCorrectionDivisor": 16970.0,
                        },
                    },
                },
            ),
            station_point=station_point,
            base_height_meters=base_height_meters,
            radius_meters=radius_meters,
            vertical_limit_angle_degrees=vertical_limit_angle_degrees,
            horizontal_limit_angle_degrees=horizontal_limit_angle_degrees,
            standards_rule_code=self.standards_rule_code,
        )
