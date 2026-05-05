# app/analysis/rules/vor/reflector_mask_area.py
import math
from dataclasses import dataclass

from shapely.geometry import Point

from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.vor.common import VorRule, build_vor_ring_protection_zone


class VorReflectorMaskAreaRule(VorRule):
    rule_code = "vor_reflector_mask_area"
    rule_name = "vor_reflector_mask_area"
    zone_code = "vor_reflector_mask_area"
    zone_name = resolve_protection_zone_name(zone_code="vor_reflector_mask_area")

    # 绑定单个 VOR 台站的阴影区保护区。
    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
    ):
        altitude = float(station.altitude) if station.altitude is not None else 0.0
        r = _float_or_none(station.b_to_center_distance)
        d = _float_or_none(station.reflection_diameter)
        h2 = _float_or_none(station.b_antenna_h)
        h1 = _float_or_none(station.reflection_net_hag)

        if any(v is None for v in (r, d, h2, h1)):
            return None

        half_d = d / 2.0
        delta = max(half_d - r, 0.001)  # 防止除零

        angle = math.atan(delta / h2)
        rt = math.tan(angle) * h1 + half_d
        outer_radius = min(rt, 100.0)

        if half_d >= outer_radius:
            return None

        slope = -h2 / delta
        intercept = h1 - slope * half_d
        base_height = altitude + h1

        protection_zone = build_vor_ring_protection_zone(
            station_id=int(station.id),
            station_type=str(station.station_type),
            rule_code=self.rule_code,
            rule_name=self.rule_name,
            zone_code=self.zone_code,
            zone_name=self.zone_name,
            region_code="default",
            region_name="default",
            station_point=station_point,
            inner_radius_m=half_d,
            outer_radius_m=outer_radius,
            base_height_meters=base_height,
            slope_meters_per_meter=slope,
            start_distance_meters=half_d,
            longitude=float(station.longitude) if station.longitude is not None else None,
            latitude=float(station.latitude) if station.latitude is not None else None,
        )

        return BoundVorReflectorMaskAreaRule(
            protection_zone=protection_zone,
            station_point=station_point,
            outer_radius_m=outer_radius,
            slope=slope,
            intercept=intercept,
            altitude=altitude,
        )


@dataclass(slots=True)
class BoundVorReflectorMaskAreaRule(BoundObstacleRule):
    station_point: tuple[float, float]
    outer_radius_m: float
    slope: float
    intercept: float
    altitude: float

    # 执行已绑定保护区的障碍物判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        shape = resolve_obstacle_shape(obstacle)
        entered = shape.intersects(self.protection_zone.local_geometry)

        station_pt = Point(self.station_point)
        max_distance = float(shape.hausdorff_distance(station_pt))
        x = min(max_distance, self.outer_radius_m)
        allowed_h = self.slope * x + self.intercept + self.altitude

        raw_top = obstacle.get("topElevation")
        top_elevation = float(raw_top if raw_top is not None else 0.0)

        is_compliant = not entered or top_elevation <= allowed_h
        if not entered:
            message = "obstacle outside reflector mask zone"
        elif is_compliant:
            message = "obstacle within reflector mask limit"
        else:
            message = "obstacle exceeds reflector mask height limit"

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
            is_compliant=is_compliant,
            message=message,
            metrics={
                "enteredProtectionZone": entered,
                "maxDistanceMeters": max_distance,
                "clampedDistanceMeters": x,
                "allowedHeightMeters": allowed_h,
                "topElevationMeters": top_elevation,
                "outerRadiusMeters": self.outer_radius_m,
            },
            standards_rule_code=self.protection_zone.rule_code,
        )


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    return float(value)
