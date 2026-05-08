import math

import math
from dataclasses import dataclass

from shapely.geometry import Point

from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.weather_radar.common import WeatherRadarRule, build_weather_radar_circle_protection_zone
from app.analysis.rules.weather_radar.config import WEATHER_RADAR_ELEVATION_ANGLE_1DEG


@dataclass(slots=True)
class BoundWeatherRadarElevationAngleRule(BoundObstacleRule):
    station_point: tuple[float, float]
    base_height_meters: float
    coverage_radius_meters: float
    limit_angle_degrees: float
    standards_rule_code: str

    # 执行已绑定的 WeatherRadar 仰角判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        actual_distance_meters = float(obstacle_shape.distance(Point(self.station_point)))
        top_elevation_meters = float(
            obstacle.get("topElevation") if obstacle.get("topElevation") is not None else 0.0
        )
        relative_height_meters = top_elevation_meters - self.base_height_meters
        angle_degrees = math.degrees(math.atan(relative_height_meters / max(actual_distance_meters, 0.001)))
        limit_height_meters = self.base_height_meters + (
            actual_distance_meters * math.tan(math.radians(self.limit_angle_degrees))
        )
        metrics: dict[str, float | bool] = {
            "enteredProtectionZone": actual_distance_meters <= self.coverage_radius_meters,
            "actualDistanceMeters": actual_distance_meters,
            "coverageRadiusMeters": self.coverage_radius_meters,
            "topElevationMeters": top_elevation_meters,
            "baseHeightMeters": self.base_height_meters,
            "relativeHeightMeters": relative_height_meters,
            "elevationAngleDegrees": angle_degrees,
            "limitAngleDegrees": self.limit_angle_degrees,
            "limitHeightMeters": limit_height_meters,
        }
        is_compliant = angle_degrees <= self.limit_angle_degrees
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
            message=(
                "obstacle within weather radar elevation angle limit"
                if is_compliant
                else "obstacle exceeds weather radar elevation angle limit"
            ),
            metrics=metrics,
            standards_rule_code=self.standards_rule_code,
        )


class WeatherRadarElevationAngle1degRule(WeatherRadarRule):
    rule_code = "weather_radar_elevation_angle_1deg"
    rule_name = "weather_radar_elevation_angle_1deg"
    zone_code = "weather_radar_elevation_angle_1deg"
    standards_rule_code = "weather_radar_elevation_angle_1deg"
    limit_angle_degrees = WEATHER_RADAR_ELEVATION_ANGLE_1DEG

    def __init__(self) -> None:
        self.zone_name = resolve_protection_zone_name(zone_code=self.zone_code)

    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
    ) -> BoundWeatherRadarElevationAngleRule | None:
        altitude = getattr(station, "altitude", None)
        antenna_hag = getattr(station, "antenna_hag", None)
        coverage_radius = getattr(station, "coverage_radius", None)
        if altitude is None or antenna_hag is None or coverage_radius is None:
            return None

        base_height_meters = float(altitude) + float(antenna_hag)
        coverage_radius_meters = float(coverage_radius)
        return BoundWeatherRadarElevationAngleRule(
            protection_zone=build_weather_radar_circle_protection_zone(
                station=station,
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                station_point=station_point,
                radius_meters=coverage_radius_meters,
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
                            "endMeters": coverage_radius_meters,
                        },
                        "heightModel": {
                            "type": "angle_linear_rise",
                            "angleDegrees": self.limit_angle_degrees,
                            "distanceOffsetMeters": 0.0,
                        },
                    },
                },
            ),
            station_point=station_point,
            base_height_meters=base_height_meters,
            coverage_radius_meters=coverage_radius_meters,
            limit_angle_degrees=self.limit_angle_degrees,
            standards_rule_code=self.standards_rule_code,
        )
