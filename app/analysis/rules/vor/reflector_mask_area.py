# app/analysis/rules/vor/reflector_mask_area.py
import math
from dataclasses import dataclass

from shapely.geometry import Point

from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.result_helpers import (
    compute_azimuth_degrees,
    compute_horizontal_angle_range_from_geometry,
    compute_over_distance_meters,
)
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.vor.common import VorRule, _float_or_none, build_vor_ring_protection_zone


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
        shadow_radius = min(rt, 100.0)
        zone_outer_radius = 100.0

        if half_d >= shadow_radius:
            return None

        slope = -h2 / delta
        intercept = h1 - slope * half_d
        base_height = altitude + h1
        elevation_angle = math.degrees(math.atan(slope))

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
            outer_radius_m=zone_outer_radius,
            base_height_meters=base_height,
            elevation_angle_degrees=elevation_angle,
            distance_offset_meters=half_d,
            clamp_end_meters=shadow_radius,
            longitude=float(station.longitude) if station.longitude is not None else None,
            latitude=float(station.latitude) if station.latitude is not None else None,
        )

        return BoundVorReflectorMaskAreaRule(
            protection_zone=protection_zone,
            station_point=station_point,
            shadow_radius_m=shadow_radius,
            slope=slope,
            intercept=intercept,
            altitude=altitude,
        )


@dataclass(slots=True)
class BoundVorReflectorMaskAreaRule(BoundObstacleRule):
    station_point: tuple[float, float]
    shadow_radius_m: float
    slope: float
    intercept: float
    altitude: float

    # 执行已绑定保护区的障碍物判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        shape = resolve_obstacle_shape(obstacle)
        entered = shape.intersects(self.protection_zone.local_geometry)

        station_pt = Point(self.station_point)
        max_distance = float(shape.hausdorff_distance(station_pt))
        x = min(max_distance, self.shadow_radius_m)
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

        obstacle_centroid = shape.centroid
        az = compute_azimuth_degrees(
            self.station_point[0], self.station_point[1],
            obstacle_centroid.x, obstacle_centroid.y,
        )
        min_h, max_h = compute_horizontal_angle_range_from_geometry(
            self.station_point, shape,
        )
        over = compute_over_distance_meters(top_elevation, allowed_h)
        rel_h = top_elevation - self.altitude

        if not entered:
            details = "障碍物未进入反射网阴影区。"
        elif is_compliant:
            details = f"满足规定要求，障碍物高度{top_elevation}m，允许高度{round(allowed_h,2)}m。"
        else:
            details = f"不满足规定要求，障碍物高度{top_elevation}m，允许高度{round(allowed_h,2)}m，超出{round(over,2)}m。"

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
                "shadowRadiusMeters": self.shadow_radius_m,
            },
            standards_rule_code=self.protection_zone.rule_code,
            over_distance_meters=over,
            azimuth_degrees=az,
            max_horizontal_angle_degrees=max_h,
            min_horizontal_angle_degrees=min_h,
            relative_height_meters=rel_h,
            is_in_radius=entered,
            is_in_zone=entered,
            details=details,
        )
