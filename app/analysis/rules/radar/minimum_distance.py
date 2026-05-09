from app.analysis.rules.radar.common import BoundRadarCircleRule, RadarRule, build_radar_circle_protection_zone
from app.analysis.protection_zone_style import resolve_protection_zone_name


class RadarMinimumDistanceRule(RadarRule):
    # 初始化单档 Radar B 最小间距规则。
    def __init__(self, *, minimum_distance_meters: float) -> None:
        distance_text = self._format_distance_text(minimum_distance_meters)
        self.minimum_distance_meters = float(minimum_distance_meters)
        self.rule_code = f"radar_minimum_distance_{distance_text}m"
        self.rule_name = self.rule_code
        self.zone_code = f"radar_minimum_distance_zone_{distance_text}m"
        self.zone_name = resolve_protection_zone_name(zone_code=self.zone_code)
        self.standards_rule_code = f"radar_minimum_distance_{distance_text}m_standard"

    # 绑定单个 Radar B 圆形保护区。
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
                radius_meters=self.minimum_distance_meters,
            ),
            station_point=station_point,
            minimum_distance_meters=self.minimum_distance_meters,
            standards_rule_code=self.standards_rule_code,
            base_height_meters=float(getattr(station, "altitude", 0.0) or 0.0),
        )

    def _format_distance_text(self, distance_meters: float) -> str:
        if float(distance_meters).is_integer():
            return str(int(distance_meters))
        return str(distance_meters).replace(".", "_")
