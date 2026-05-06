# app/analysis/rules/vor/datum_plane/_200m.py
from dataclasses import dataclass

from shapely.geometry import Point

from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.vor.common import VorRule
from app.analysis.rules.vor.datum_plane._base import (
    BoundVorDatumPlaneRule,
    _ensure_datum_plane_params,
    build_vor_circle_protection_zone,
)
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape


class Vor200mDatumPlaneRule(VorRule):
    rule_code = "vor_200m_datum_plane"
    rule_name = "vor_200m_datum_plane"
    zone_code = "vor_200m_datum_plane"
    zone_name = resolve_protection_zone_name(zone_code="vor_200m_datum_plane")
    radius_meters = 200.0

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

        return BoundVor200mDatumPlaneRule(
            protection_zone=protection_zone,
            station_point=station_point,
            benchmark_height=benchmark_height,
            radius_meters=self.radius_meters,
        )


@dataclass(slots=True)
class BoundVor200mDatumPlaneRule(BoundVorDatumPlaneRule):

    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        shape = resolve_obstacle_shape(obstacle)
        actual_distance = float(shape.distance(Point(self.station_point)))

        if actual_distance <= 100.0:
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
                message="obstacle within inner radius, skipped",
                metrics={
                    "enteredProtectionZone": True,
                    "actualDistanceMeters": actual_distance,
                    "benchmarkHeightMeters": self.benchmark_height,
                },
                standards_rule_code=self.protection_zone.rule_code,
            )

        return BoundVorDatumPlaneRule.analyze(self, obstacle)
