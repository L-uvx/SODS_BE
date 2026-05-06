# app/analysis/rules/vor/datum_plane_100m.py
from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rules.vor.common import (
    BoundVorDatumPlaneRule,
    VorRule,
    _compute_shadow_radius,
    _ensure_datum_plane_params,
    build_vor_circle_protection_zone,
)

# C# 100m 规则跳过的障碍物类型：高压线 + 铁路
_SKIP_CATEGORIES = frozenset({
    "power_line_high_voltage_35kv_below",
    "power_line_high_voltage_35kv",
    "power_line_high_voltage_110kv",
    "power_line_high_voltage_220kv",
    "power_line_high_voltage_330kv",
    "power_line_high_voltage_500kv_and_above",
    "railway_electrified",
    "railway_non_electrified",
})


class Vor100mDatumPlaneRule(VorRule):
    rule_code = "vor_100m_datum_plane"
    rule_name = "vor_100m_datum_plane"
    zone_code = "vor_100m_datum_plane"
    zone_name = resolve_protection_zone_name(zone_code="vor_100m_datum_plane")
    radius_meters = 100.0

    # 绑定单个 VOR 台站的 100 米基准面保护区。
    def bind(self, *, station, station_point):
        params = _ensure_datum_plane_params(station)
        if params is None:
            return None
        altitude, h1 = params
        benchmark_height = altitude + h1
        shadow_radius = _compute_shadow_radius(station)
        half_d = float(station.reflection_diameter or 0) / 2.0

        protection_zone = build_vor_circle_protection_zone(
            station_id=int(station.id),
            station_type=str(station.station_type),
            rule_code=self.rule_code,
            rule_name=self.rule_name,
            zone_code=self.zone_code,
            zone_name=self.zone_name,
            region_code="default",
            region_name="default",
            station_point=station_point,
            radius_meters=self.radius_meters,
            base_height_meters=benchmark_height,
        )

        return BoundVorDatumPlaneRule(
            protection_zone=protection_zone,
            station_point=station_point,
            benchmark_height=benchmark_height,
            radius_meters=self.radius_meters,
            shadow_radius=shadow_radius,
            _half_d=half_d,
        )
