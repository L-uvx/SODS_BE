from app.analysis.rules.ndb.common import (
    BoundNdbMinimumDistanceRule,
    NdbRule,
    build_ndb_circle_protection_zone,
)


class NdbMinimumDistance50mRule(NdbRule):
    rule_code = "ndb_minimum_distance_50m"
    rule_name = "ndb_minimum_distance_50m"
    zone_code = "ndb_minimum_distance_50m"
    zone_name = "NDB 50m minimum distance zone"
    radius_meters = 50.0

    # 绑定单个 NDB 台站的 50 米最小间距保护区。
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
        )
