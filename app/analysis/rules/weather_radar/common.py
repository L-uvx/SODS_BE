from dataclasses import dataclass

from shapely.geometry import Point

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.result_helpers import (
    compute_azimuth_degrees,
    compute_horizontal_angle_range_from_geometry,
    compute_over_distance_meters,
)
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import build_circle_polygon, ensure_multipolygon, resolve_obstacle_shape
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


class WeatherRadarRule(ObstacleRule):
    # 绑定单个 WeatherRadar 台站上下文。
    def bind(self, *args, **kwargs) -> BoundObstacleRule:  # pragma: no cover
        raise NotImplementedError


@dataclass(slots=True)
class BoundWeatherRadarCircleRule(BoundObstacleRule):
    station_point: tuple[float, float]
    minimum_distance_meters: float
    standards_rule_code: str
    base_height_meters: float = 0.0

    # 执行已绑定的 WeatherRadar 圆形防护间距判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(self.protection_zone.local_geometry)
        actual_distance_meters = float(obstacle_shape.distance(Point(self.station_point)))
        top_elevation_meters = float(
            obstacle.get("topElevation") if obstacle.get("topElevation") is not None else 0.0
        )
        is_compliant = actual_distance_meters >= self.minimum_distance_meters
        metrics: dict[str, float | bool] = {
            "enteredProtectionZone": entered_protection_zone,
            "actualDistanceMeters": actual_distance_meters,
            "minimumDistanceMeters": self.minimum_distance_meters,
            "topElevationMeters": top_elevation_meters,
        }

        centroid = obstacle_shape.centroid
        azimuth_degrees = compute_azimuth_degrees(
            self.station_point[0], self.station_point[1], centroid.x, centroid.y
        )
        min_horizontal_angle_degrees, max_horizontal_angle_degrees = (
            compute_horizontal_angle_range_from_geometry(self.station_point, obstacle_shape)
        )
        relative_height_meters = top_elevation_meters - self.base_height_meters
        over_distance = 0.0
        if not is_compliant:
            over_distance = compute_over_distance_meters(
                self.minimum_distance_meters, actual_distance_meters
            )
            details = f"不满足规定要求，实际距离{int(actual_distance_meters)}m，所需最小间距{int(self.minimum_distance_meters)}m。"
        else:
            details = f"满足规定要求，实际距离{int(actual_distance_meters)}m。"

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
            is_filter_limit=True,
            message=(
                f"在{self.minimum_distance_meters}米范围内"
                if not is_compliant
                else f"不在{self.minimum_distance_meters}米范围内"
            ),
            metrics=metrics,
            standards_rule_code=self.standards_rule_code,
            azimuth_degrees=azimuth_degrees,
            max_horizontal_angle_degrees=max_horizontal_angle_degrees,
            min_horizontal_angle_degrees=min_horizontal_angle_degrees,
            relative_height_meters=relative_height_meters,
            is_in_radius=entered_protection_zone,
            is_in_zone=entered_protection_zone,
            over_distance_meters=top_elevation_meters,
            details=details,
        )
def build_weather_radar_circle_protection_zone(
    *,
    station: object,
    rule_code: str,
    rule_name: str,
    zone_code: str,
    zone_name: str,
    station_point: tuple[float, float],
    radius_meters: float,
    vertical_definition: dict[str, object] | None = None,
) -> ProtectionZoneSpec:
    local_geometry = ensure_multipolygon(
        build_circle_polygon(center_point=station_point, radius_meters=radius_meters)
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
        local_geometry=local_geometry,
        vertical_definition=vertical_definition
        or {
            "mode": "flat",
            "baseReference": "station",
            "baseHeightMeters": 0.0,
        },
    )
