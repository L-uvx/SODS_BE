# app/analysis/rules/vor/datum_plane_200m.py
from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rules.vor.common import (
    BoundVorDatumPlaneRule,
    VorRule,
    _ensure_datum_plane_params,
    build_vor_circle_protection_zone,
)

# C# 200m 通用规则跳过：高压线 + 铁路 + 树木
_SKIP_CATEGORIES = frozenset({
    "power_line_high_voltage_35kv_below",
    "power_line_high_voltage_35kv",
    "power_line_high_voltage_110kv",
    "power_line_high_voltage_220kv",
    "power_line_high_voltage_330kv",
    "power_line_high_voltage_500kv_and_above",
    "railway_electrified",
    "railway_non_electrified",
    "tree_or_forest",
})


class Vor200mDatumPlaneRule(VorRule):
    rule_code = "vor_200m_datum_plane"
    rule_name = "vor_200m_datum_plane"
    zone_code = "vor_200m_datum_plane"
    zone_name = resolve_protection_zone_name(zone_code="vor_200m_datum_plane")
    radius_meters = 200.0

    # 绑定单个 VOR 台站的 200 米基准面保护区（通用）。
    def bind(self, *, station, station_point):
        params = _ensure_datum_plane_params(station)
        if params is None:
            return None
        altitude, h1 = params
        benchmark_height = altitude + h1

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
            min_distance_gate_meters=100.0,
        )
