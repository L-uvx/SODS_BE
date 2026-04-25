from app.analysis.rules.ndb.common import (
    BoundNdbConicalClearanceRule,
    NdbRule,
    build_ndb_conical_protection_zone,
)


class NdbConicalClearance3DegRule(NdbRule):
    rule_code = "ndb_conical_clearance_3deg"
    rule_name = "ndb_conical_clearance_3deg"
    zone_code = "ndb_conical_clearance_3deg"
    zone_name = "NDB 3 degree conical clearance zone"
    zone_definition = {
        "shape": "radial_band",
        "min_radius_m": 50.0,
        "max_radius_m": 37040.0,
        "vertical_angle_deg": 3.0,
    }

    # 绑定单个 NDB 台站的 3 度锥形净空保护区。
    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
        station_altitude: float | None,
    ) -> BoundNdbConicalClearanceRule:
        inner_radius_m = float(self.zone_definition["min_radius_m"])
        outer_radius_m = float(self.zone_definition["max_radius_m"])
        elevation_angle_degrees = float(self.zone_definition["vertical_angle_deg"])
        return BoundNdbConicalClearanceRule(
            protection_zone=build_ndb_conical_protection_zone(
                station=station,
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                station_point=station_point,
                station_altitude=station_altitude,
                inner_radius_meters=inner_radius_m,
                outer_radius_meters=outer_radius_m,
                elevation_angle_degrees=elevation_angle_degrees,
            ),
            station_point=station_point,
            station_altitude=station_altitude,
            inner_radius_meters=inner_radius_m,
            outer_radius_meters=outer_radius_m,
            elevation_angle_degrees=elevation_angle_degrees,
        )
