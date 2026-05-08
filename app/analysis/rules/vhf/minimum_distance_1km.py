from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rules.vhf.common import (
    BoundVhfCircleRule,
    VhfRule,
    build_vhf_circle_protection_zone,
)


class VhfMinimumDistance1kmRule(VhfRule):
    rule_code = "vhf_minimum_distance_1km"
    rule_name = "vhf_minimum_distance_1km"
    zone_code = "vhf_minimum_distance_1km"
    minimum_distance_meters = 1000.0

    def __init__(self) -> None:
        self.zone_name = resolve_protection_zone_name(zone_code=self.zone_code)

    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
    ) -> BoundVhfCircleRule:
        return BoundVhfCircleRule(
            protection_zone=build_vhf_circle_protection_zone(
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
