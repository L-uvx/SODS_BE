from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rules.hf.common import BoundHfCircleRule, HfRule, build_hf_circle_protection_zone


class HfMinimumDistance2kmRule(HfRule):
    rule_code = "hf_minimum_distance_2km"
    rule_name = "hf_minimum_distance_2km"
    zone_code = "hf_minimum_distance_2km"
    minimum_distance_meters = 2000.0

    def __init__(self) -> None:
        self.zone_name = resolve_protection_zone_name(zone_code=self.zone_code)

    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
    ) -> BoundHfCircleRule:
        return BoundHfCircleRule(
            protection_zone=build_hf_circle_protection_zone(
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
        )
