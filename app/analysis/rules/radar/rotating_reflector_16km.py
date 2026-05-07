from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rules.radar.common import BoundRadarCircleRule, RadarRule, build_radar_circle_protection_zone
from app.analysis.rules.radar.config import RADAR_C_ROTATING_REFLECTOR_RADIUS_METERS


class RadarRotatingReflector16kmRule(RadarRule):
    rule_code = "radar_rotating_reflector_16km"
    rule_name = "radar_rotating_reflector_16km"
    zone_code = "radar_rotating_reflector_zone_16km"
    standards_rule_code = "radar_rotating_reflector_16km_standard"

    # 初始化 Radar C 16KM 旋转反射体保护区规则。
    def __init__(self) -> None:
        self.zone_name = resolve_protection_zone_name(zone_code=self.zone_code)

    # 绑定单个 Radar C 16KM 圆形保护区。
    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
    ) -> BoundRadarCircleRule:
        return BoundRadarCircleRule(
            protection_zone=build_radar_circle_protection_zone(
                station=station,
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                station_point=station_point,
                radius_meters=RADAR_C_ROTATING_REFLECTOR_RADIUS_METERS,
            ),
            station_point=station_point,
            minimum_distance_meters=None,
            standards_rule_code=self.standards_rule_code,
        )
