from dataclasses import dataclass

from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.result_helpers import (
    compute_azimuth_degrees,
    compute_horizontal_angle_range_from_geometry,
    compute_over_distance_meters,
)
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import ObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.gp.site_protection.common import BoundGpSiteProtectionRegionRule
from app.analysis.rules.gp.site_protection.judgement import is_gp_cable_category
from app.analysis.rules.gp.site_protection.helpers import (
    GpSiteProtectionSharedContext,
    build_gp_site_protection_region_a_geometry,
)
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


@dataclass(slots=True)
class BoundGpSiteProtectionRegionARule(BoundGpSiteProtectionRegionRule):
    def _resolve_result_standards_rule_code(self, obstacle: dict[str, object]) -> str:
        if is_gp_cable_category(str(obstacle.get("globalObstacleCategory"))):
            return f"{self.standards_rule_code}_cable"
        return self.standards_rule_code

    # 执行 GP 场地保护区 A 区真实判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(
            self.protection_zone.local_geometry
        )
        base_height_meters = float(
            self.protection_zone.vertical_definition.get("baseHeightMeters", 0.0) or 0.0
        )
        top_elevation_meters = float(obstacle.get("topElevation", 0.0) or 0.0)
        is_cable = is_gp_cable_category(str(obstacle.get("globalObstacleCategory")))

        obstacle_centroid = obstacle_shape.centroid
        az = compute_azimuth_degrees(
            self.station_point[0], self.station_point[1],
            obstacle_centroid.x, obstacle_centroid.y,
        )
        min_h, max_h = compute_horizontal_angle_range_from_geometry(
            self.station_point, obstacle_shape,
        )
        rel_height = top_elevation_meters - base_height_meters

        if not entered_protection_zone:
            is_compliant = True
            message = "obstacle outside GP site protection region A"
            over = 0.0
            details = "障碍物未进入GP场地保护区A区。"
        elif is_cable:
            is_compliant = top_elevation_meters < base_height_meters
            message = (
                "cable within region A and below station altitude"
                if is_compliant
                else "cable within region A above station altitude"
            )
            over = compute_over_distance_meters(top_elevation_meters, base_height_meters)
            if is_compliant:
                details = f"满足规定要求，障碍物高度{top_elevation_meters}m，允许高度{base_height_meters}m。"
            else:
                details = f"不满足规定要求，障碍物高度{top_elevation_meters}m，允许高度{base_height_meters}m，超出{over}m。"
        else:
            is_compliant = False
            message = "non-cable obstacle enters region A"
            over = compute_over_distance_meters(top_elevation_meters, base_height_meters)
            details = f"障碍物进入{self.protection_zone.zone_name}A区。"

        metrics = {
            "enteredProtectionZone": entered_protection_zone,
            "isCable": is_cable,
            "baseHeightMeters": base_height_meters,
            "topElevationMeters": top_elevation_meters,
        }
        if is_cable:
            metrics["allowedHeightMeters"] = base_height_meters

        return self.build_result(
            obstacle=obstacle,
            is_compliant=is_compliant,
            message=message,
            metrics=metrics,
            standards_rule_code=self._resolve_result_standards_rule_code(obstacle),
            over_distance_meters=over,
            azimuth_degrees=az,
            max_horizontal_angle_degrees=max_h,
            min_horizontal_angle_degrees=min_h,
            relative_height_meters=rel_height,
            is_in_radius=entered_protection_zone,
            is_in_zone=entered_protection_zone,
            details=details,
        )


class _GpSiteProtectionRegionARuleBase(ObstacleRule):
    region_code = "A"
    region_name = "A"

    # 绑定 GP 场地保护区 A 区。
    def bind(
        self,
        *,
        station: object,
        shared_context: GpSiteProtectionSharedContext,
    ) -> BoundGpSiteProtectionRegionARule:
        region_geometry = build_gp_site_protection_region_a_geometry(shared_context)
        return BoundGpSiteProtectionRegionARule(
            protection_zone=build_protection_zone_spec(
                station_id=int(station.id),
                station_type=str(station.station_type),
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                region_code=self.region_code,
                region_name=self.region_name,
                local_geometry=region_geometry.local_geometry,
                vertical_definition={
                    "mode": "flat",
                    "baseReference": "station",
                    "baseHeightMeters": float(getattr(station, "altitude", 0.0) or 0.0),
                },
            ),
            station_sub_type=(
                None
                if getattr(station, "station_sub_type", None) is None
                else str(getattr(station, "station_sub_type"))
            ),
            standards_rule_code=self._resolve_standards_rule_code(station=station),
            station_point=shared_context.station_point,
        )

    def _resolve_standards_rule_code(self, *, station: object) -> str:
        return self.rule_code


class GpSiteProtectionGbRegionARule(_GpSiteProtectionRegionARuleBase):
    rule_code = "gp_site_protection_gb_region_a"
    rule_name = "gp_site_protection_gb_region_a"
    zone_code = "gp_site_protection_gb"
    zone_name = resolve_protection_zone_name(zone_code=zone_code)


class GpSiteProtectionMhRegionARule(_GpSiteProtectionRegionARuleBase):
    rule_code = "gp_site_protection_mh_region_a"
    rule_name = "gp_site_protection_mh_region_a"
    zone_code = "gp_site_protection_mh"
    zone_name = resolve_protection_zone_name(zone_code=zone_code)


__all__ = [
    "BoundGpSiteProtectionRegionRule",
    "GpSiteProtectionGbRegionARule",
    "GpSiteProtectionMhRegionARule",
]
