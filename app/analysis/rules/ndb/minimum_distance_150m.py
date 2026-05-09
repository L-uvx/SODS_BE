from app.analysis.rules.ndb.common import (
    BoundNdbMinimumDistanceRule,
    NdbRule,
    build_ndb_circle_protection_zone,
)
from app.analysis.protection_zone_style import resolve_protection_zone_name


class NdbMinimumDistance150mRule(NdbRule):
    rule_code = "ndb_minimum_distance_150m"
    rule_name = "ndb_minimum_distance_150m"
    zone_code = "ndb_minimum_distance_150m"
    zone_name = resolve_protection_zone_name(zone_code=zone_code)
    radius_meters = 150.0

    # 绑定单个 NDB 台站的 150 米最小间距保护区。
    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
    ) -> BoundNdbMinimumDistanceRule:
        return BoundNdbMinimumDistanceRule(
            protection_zone=build_ndb_circle_protection_zone(
                station=station,
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                station_point=station_point,
                radius_meters=self.radius_meters,
            ),
            station_point=station_point,
            required_distance_meters=self.radius_meters,
            station_altitude=float(getattr(station, "altitude", 0.0) or 0.0),
        )
