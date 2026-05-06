# app/analysis/rules/vor/datum_plane/_100m.py
from dataclasses import dataclass

from shapely.geometry import Point

from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.vor.common import (
    BoundVorDatumPlaneRule,
    VorRule,
    _compute_shadow_radius,
    _ensure_datum_plane_params,
    build_vor_circle_protection_zone,
)
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape


class Vor100mDatumPlaneRule(VorRule):
    rule_code = "vor_100m_datum_plane"
    rule_name = "vor_100m_datum_plane"
    zone_code = "vor_100m_datum_plane"
    zone_name = resolve_protection_zone_name(zone_code="vor_100m_datum_plane")
    radius_meters = 100.0

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

        return BoundVor100mDatumPlaneRule(
            protection_zone=protection_zone,
            station_point=station_point,
            benchmark_height=benchmark_height,
            radius_meters=self.radius_meters,
            shadow_radius=shadow_radius,
            _half_d=half_d,
        )


@dataclass(slots=True)
class BoundVor100mDatumPlaneRule(BoundVorDatumPlaneRule):
    shadow_radius: float | None = None
    _half_d: float = 0.0

    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        shape = resolve_obstacle_shape(obstacle)
        entered = shape.intersects(self.protection_zone.local_geometry)
        actual_distance = float(shape.distance(Point(self.station_point)))

        # 阴影区预过滤
        if (
            self.shadow_radius is not None
            and actual_distance > self._half_d
            and actual_distance < self.shadow_radius
        ):
            return AnalysisRuleResult(
                station_id=self.protection_zone.station_id,
                station_type=self.protection_zone.station_type,
                obstacle_id=int(obstacle["obstacleId"]),
                obstacle_name=str(obstacle["name"]),
                raw_obstacle_type=obstacle["rawObstacleType"],
                global_obstacle_category=str(obstacle["globalObstacleCategory"]),
                rule_code=self.protection_zone.rule_code,
                rule_name=self.protection_zone.rule_name,
                zone_code=self.protection_zone.zone_code,
                zone_name=self.protection_zone.zone_name,
                region_code=self.protection_zone.region_code,
                region_name=self.protection_zone.region_name,
                is_applicable=True,
                is_compliant=True,
                message="obstacle within reflector shadow zone, skipped",
                metrics={
                    "enteredProtectionZone": entered,
                    "actualDistanceMeters": actual_distance,
                    "shadowRadiusMeters": self.shadow_radius,
                    "benchmarkHeightMeters": self.benchmark_height,
                },
                standards_rule_code=self.protection_zone.rule_code,
            )

        return BoundVorDatumPlaneRule.analyze(self, obstacle)
