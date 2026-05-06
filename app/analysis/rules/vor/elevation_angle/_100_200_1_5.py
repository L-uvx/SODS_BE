from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rules.vor.common import VorRule
from app.analysis.rules.vor.elevation_angle._shared import bind_elevation_angle_rule


class Vor100_200_1_5_Rule(VorRule):
    zone_code = "vor_100_200_1_5_deg"
    zone_name = resolve_protection_zone_name(zone_code=zone_code)
    rule_code = "vor_100_200_1_5_deg"
    rule_name = "vor_100_200_1_5_deg"
    region_code = "default"
    region_name = "default"

    def bind(self, *, station, station_point):
        return bind_elevation_angle_rule(
            station=station,
            station_point=station_point,
            rule_code=self.rule_code,
            rule_name=self.rule_name,
            zone_code=self.zone_code,
            zone_name=self.zone_name,
            region_code=self.region_code,
            region_name=self.region_name,
            inner_radius_m=100.0,
            outer_radius_m=200.0,
            limit_angle_degrees=1.5,
            horizontal_angle_limit_degrees=7.0,
        )
