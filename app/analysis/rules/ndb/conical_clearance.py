from app.analysis.rules.ndb.config import NDB_CONICAL_CLEARANCE
from app.analysis.rules.ndb.common import (
    BoundNdbConicalClearanceRule,
    NdbRule,
    build_ndb_conical_protection_zone,
)
from app.analysis.protection_zone_style import resolve_protection_zone_name


class NdbConicalClearance3DegRule(NdbRule):
    rule_code = "ndb_conical_clearance_3deg"
    rule_name = "ndb_conical_clearance_3deg"
    zone_code = "ndb_conical_clearance_3deg"
    zone_name = resolve_protection_zone_name(zone_code=zone_code)

    def __init__(self) -> None:
        self.inner_radius_meters = float(NDB_CONICAL_CLEARANCE["inner_radius_m"])
        self.outer_radius_meters = float(NDB_CONICAL_CLEARANCE["outer_radius_m"])
        self.elevation_angle_degrees = float(
            NDB_CONICAL_CLEARANCE["vertical_angle_deg"]
        )

    # 绑定单个 NDB 台站的 3 度锥形净空保护区。
    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
        station_altitude: float | None,
    ) -> BoundNdbConicalClearanceRule:
        return BoundNdbConicalClearanceRule(
            protection_zone=build_ndb_conical_protection_zone(
                station=station,
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                station_point=station_point,
                station_altitude=station_altitude,
                inner_radius_meters=self.inner_radius_meters,
                outer_radius_meters=self.outer_radius_meters,
                elevation_angle_degrees=self.elevation_angle_degrees,
            ),
            station_point=station_point,
            station_altitude=station_altitude,
            inner_radius_meters=self.inner_radius_meters,
            outer_radius_meters=self.outer_radius_meters,
            elevation_angle_degrees=self.elevation_angle_degrees,
        )
