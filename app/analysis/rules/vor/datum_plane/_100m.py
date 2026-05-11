# app/analysis/rules/vor/datum_plane/_100m.py
import math
from dataclasses import dataclass

from shapely.geometry import Point

from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.result_helpers import (
    compute_azimuth_degrees,
    compute_horizontal_angle_range_from_geometry,
)
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.vor.common import VorRule, _float_or_none
from app.analysis.rules.vor.datum_plane._base import (
    BoundVorDatumPlaneRule,
    _ensure_datum_plane_params,
    build_vor_circle_protection_zone,
)
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape


# 计算反射网阴影区外缘半径 rt。
def _compute_shadow_radius(station: object) -> float | None:
    d_val = _float_or_none(station.reflection_diameter)
    r_val = _float_or_none(station.b_to_center_distance)
    h2_val = _float_or_none(station.b_antenna_h)
    h1_val = _float_or_none(station.reflection_net_hag)
    if any(v is None for v in (d_val, r_val, h2_val, h1_val)):
        return None
    half_d = d_val / 2.0
    delta = max(half_d - r_val, 0.001)
    angle = math.atan(delta / h2_val)
    rt = math.tan(angle) * h1_val + half_d
    return min(rt, 100.0)


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
            raw_top = obstacle.get("topElevation")
            top_elevation = float(raw_top if raw_top is not None else 0.0)
            obstacle_centroid = shape.centroid
            az = compute_azimuth_degrees(
                self.station_point[0], self.station_point[1],
                obstacle_centroid.x, obstacle_centroid.y,
            )
            min_h, max_h = compute_horizontal_angle_range_from_geometry(
                self.station_point, shape,
            )
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
                    "allowedHeightMeters": self.benchmark_height,
                    "overHeightMeters": max(0.0, top_elevation - self.benchmark_height),
                    "topElevationMeters": top_elevation,
                    "shadowRadiusMeters": self.shadow_radius,
                    "benchmarkHeightMeters": self.benchmark_height,
                },
                standards_rule_code=self.protection_zone.rule_code,
                over_distance_meters=0.0,
                azimuth_degrees=az,
                max_horizontal_angle_degrees=max_h,
                min_horizontal_angle_degrees=min_h,
                relative_height_meters=0.0,
                is_in_radius=entered,
                is_in_zone=entered,
                details="该障碍物已委托给反射网阴影区处理。",
            )

        return BoundVorDatumPlaneRule.analyze(self, obstacle)
