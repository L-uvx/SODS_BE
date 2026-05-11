from dataclasses import dataclass

from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.result_helpers import (
    compute_azimuth_degrees,
    compute_horizontal_angle_range_from_geometry,
)
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.gp.run_area_protection.constants import SUPPORTED_CATEGORIES
from app.analysis.rules.gp.run_area_protection.helpers import (
    GpRunAreaProtectionSharedContext,
    build_gp_run_area_region_b_geometry,
)
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


@dataclass(slots=True)
class BoundGpRunAreaProtectionRegionBRule(BoundObstacleRule):
    station_point: tuple[float, float]

    # 执行 GP 运行保护区第 B 区判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_category = str(obstacle["globalObstacleCategory"])
        is_applicable = obstacle_category in SUPPORTED_CATEGORIES
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(
            self.protection_zone.local_geometry
        )

        obstacle_centroid = obstacle_shape.centroid
        az = compute_azimuth_degrees(
            self.station_point[0], self.station_point[1],
            obstacle_centroid.x, obstacle_centroid.y,
        )
        min_h, max_h = compute_horizontal_angle_range_from_geometry(
            self.station_point, obstacle_shape,
        )
        top_elevation_meters = float(obstacle.get("topElevation") or 0.0)

        if is_applicable and entered_protection_zone:
            details = "障碍物进入运行保护区敏感区域。"
        elif not is_applicable:
            details = "障碍物类型不适用GP运行保护区敏感区规则。"
        else:
            details = "障碍物未进入GP运行保护区敏感区域。"

        return AnalysisRuleResult(
            station_id=self.protection_zone.station_id,
            station_type=self.protection_zone.station_type,
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=obstacle.get("rawObstacleType"),
            global_obstacle_category=obstacle_category,
            rule_code=self.protection_zone.rule_code,
            rule_name=self.protection_zone.rule_name,
            zone_code=self.protection_zone.zone_code,
            zone_name=self.protection_zone.zone_name,
            region_code=self.protection_zone.region_code,
            region_name=self.protection_zone.region_name,
            is_applicable=is_applicable,
            is_compliant=(not entered_protection_zone) if is_applicable else True,
            message=(
                "在运行保护区范围内,但标准未明确对该障碍物类型进行限制"
                if not is_applicable
                else (
                    "不在运行保护区敏感区范围内"
                    if not entered_protection_zone
                    else "在敏感区范围内"
                )
            ),
            metrics={
                "areaType": "sensitive",
                "enteredProtectionZone": entered_protection_zone,
                "topElevationMeters": top_elevation_meters,
            },
            standards_rule_code="gp_run_area_protection_sensitive",
            over_distance_meters=top_elevation_meters,
            azimuth_degrees=az,
            max_horizontal_angle_degrees=max_h,
            min_horizontal_angle_degrees=min_h,
            relative_height_meters=0.0,
            is_in_radius=entered_protection_zone,
            is_in_zone=entered_protection_zone,
            details=details,
        )


class GpRunAreaProtectionRegionBRule(ObstacleRule):
    rule_code = "gp_run_area_protection_region_b"
    rule_name = "gp_run_area_protection_region_b"
    zone_code = "gp_run_area_protection"
    zone_name = resolve_protection_zone_name(zone_code=zone_code)

    # 绑定 GP 运行保护区第 B 区。
    def bind(
        self,
        *,
        station: object,
        shared_context: GpRunAreaProtectionSharedContext,
    ) -> BoundGpRunAreaProtectionRegionBRule:
        region_geometry = build_gp_run_area_region_b_geometry(shared_context)
        return BoundGpRunAreaProtectionRegionBRule(
            protection_zone=build_protection_zone_spec(
                station_id=int(station.id),
                station_type=str(station.station_type),
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                region_code="B",
                region_name="B",
                local_geometry=region_geometry.local_geometry,
                vertical_definition={
                    "mode": "flat",
                    "baseReference": "station",
                    "baseHeightMeters": float(getattr(station, "altitude", 0.0) or 0.0),
                },
            ),
            station_point=shared_context.station_point,
        )
