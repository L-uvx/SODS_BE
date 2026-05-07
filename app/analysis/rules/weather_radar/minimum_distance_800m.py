from app.analysis.rules.weather_radar.common import (
    BoundWeatherRadarCircleRule,
    WeatherRadarRule,
    build_weather_radar_circle_protection_zone,
)
from app.analysis.protection_zone_style import resolve_protection_zone_name


class WeatherRadarMinimumDistance800mRule(WeatherRadarRule):
    rule_code = "weather_radar_minimum_distance_800m"
    rule_name = "weather_radar_minimum_distance_800m"
    zone_code = "weather_radar_minimum_distance_800m"
    standards_rule_code = "weather_radar_minimum_distance_800m"
    minimum_distance_meters = 800.0

    def __init__(self) -> None:
        self.zone_name = resolve_protection_zone_name(zone_code=self.zone_code)

    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
    ) -> BoundWeatherRadarCircleRule:
        return BoundWeatherRadarCircleRule(
            protection_zone=build_weather_radar_circle_protection_zone(
                station=station,
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                station_point=station_point,
                radius_meters=self.minimum_distance_meters,
            ),
            station_point=station_point,
            minimum_distance_meters=self.minimum_distance_meters,
            standards_rule_code=self.standards_rule_code,
        )
