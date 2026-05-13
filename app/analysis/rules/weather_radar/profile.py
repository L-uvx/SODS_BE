from dataclasses import dataclass

from shapely.geometry import Point

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.weather_radar.config import (
    WEATHER_RADAR_MINIMUM_DISTANCE_450M,
    WEATHER_RADAR_MINIMUM_DISTANCE_800M,
    WEATHER_RADAR_SPECIAL_INTERFERENCE_CATEGORIES,
)
from app.analysis.rules.weather_radar.elevation_angle_1deg import WeatherRadarElevationAngle1degRule
from app.analysis.rules.weather_radar.minimum_distance_450m import WeatherRadarMinimumDistance450mRule
from app.analysis.rules.weather_radar.minimum_distance_800m import WeatherRadarMinimumDistance800mRule


@dataclass(slots=True)
class WeatherRadarStationAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class WeatherRadarRuleProfile:
    # 执行 WeatherRadar 450m/800m/1deg 规则。
    def __init__(self) -> None:
        self._minimum_distance_450m_rule = WeatherRadarMinimumDistance450mRule()
        self._minimum_distance_800m_rule = WeatherRadarMinimumDistance800mRule()
        self._elevation_angle_1deg_rule = WeatherRadarElevationAngle1degRule()

    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
    ) -> WeatherRadarStationAnalysisPayload:
        rule_results: list[AnalysisRuleResult] = []
        protection_zones: list[ProtectionZoneSpec] = []
        obstacle_categories = {
            str(obstacle["globalObstacleCategory"])
            for obstacle in obstacles
            if obstacle.get("globalObstacleCategory") is not None
        }
        has_non_special_categories = bool(
            obstacle_categories - WEATHER_RADAR_SPECIAL_INTERFERENCE_CATEGORIES
        )
        has_special_categories = bool(
            obstacle_categories & WEATHER_RADAR_SPECIAL_INTERFERENCE_CATEGORIES
        )

        bound_450m_rule = None
        if has_non_special_categories:
            bound_450m_rule = self._minimum_distance_450m_rule.bind(
                station=station,
                station_point=station_point,
            )
            protection_zones.append(bound_450m_rule.protection_zone)

        bound_800m_rule = None
        if has_special_categories:
            bound_800m_rule = self._minimum_distance_800m_rule.bind(
                station=station,
                station_point=station_point,
            )
            protection_zones.append(bound_800m_rule.protection_zone)

        bound_1deg_rule = self._elevation_angle_1deg_rule.bind(
            station=station,
            station_point=station_point,
        )
        if bound_1deg_rule is not None:
            protection_zones.append(bound_1deg_rule.protection_zone)

        for obstacle in obstacles:
            category = str(obstacle["globalObstacleCategory"])
            obstacle_shape = resolve_obstacle_shape(obstacle)
            actual_distance_meters = float(obstacle_shape.distance(Point(station_point)))
            is_special_category = category in WEATHER_RADAR_SPECIAL_INTERFERENCE_CATEGORIES

            if not is_special_category and bound_450m_rule is not None:
                rule_results.append(bound_450m_rule.analyze(obstacle))

            if is_special_category and bound_800m_rule is not None:
                rule_results.append(bound_800m_rule.analyze(obstacle))

            should_apply_1deg = True
            if actual_distance_meters < WEATHER_RADAR_MINIMUM_DISTANCE_450M:
                should_apply_1deg = False
            elif actual_distance_meters < WEATHER_RADAR_MINIMUM_DISTANCE_800M and is_special_category:
                should_apply_1deg = False
            elif actual_distance_meters > float(getattr(station, "coverage_radius", 0.0) or 0.0):
                should_apply_1deg = False

            if should_apply_1deg and bound_1deg_rule is not None:
                    rule_results.append(bound_1deg_rule.analyze(obstacle))

        return WeatherRadarStationAnalysisPayload(
            rule_results=rule_results,
            protection_zones=protection_zones,
        )

    # 无条件绑定 WeatherRadar 全部规则并返回所有保护区（不含障碍物分析）。
    def bind_protection_zones(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
    ) -> list[ProtectionZoneSpec]:
        protection_zones: list[ProtectionZoneSpec] = []

        bound_450m = self._minimum_distance_450m_rule.bind(
            station=station, station_point=station_point,
        )
        protection_zones.append(bound_450m.protection_zone)

        bound_800m = self._minimum_distance_800m_rule.bind(
            station=station, station_point=station_point,
        )
        protection_zones.append(bound_800m.protection_zone)

        bound_1deg = self._elevation_angle_1deg_rule.bind(
            station=station, station_point=station_point,
        )
        if bound_1deg is not None:
            protection_zones.append(bound_1deg.protection_zone)

        return protection_zones
