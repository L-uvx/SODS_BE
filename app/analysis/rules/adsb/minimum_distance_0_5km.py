from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rules.adsb.common import (
    AdsbRule,
    BoundAdsbCircleRule,
    build_adsb_circle_protection_zone,
)


class AdsbMinimumDistance0_5kmRule(AdsbRule):
    rule_code = "adsb_minimum_distance_0_5km"
    rule_name = "adsb_minimum_distance_0_5km"
    zone_code = "adsb_minimum_distance_0_5km"
    minimum_distance_meters = 500.0

    def __init__(self) -> None:
        self.zone_name = resolve_protection_zone_name(zone_code=self.zone_code)

    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
    ) -> BoundAdsbCircleRule:
        return BoundAdsbCircleRule(
            protection_zone=build_adsb_circle_protection_zone(
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
