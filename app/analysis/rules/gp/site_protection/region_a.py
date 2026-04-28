from dataclasses import dataclass

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

        if not entered_protection_zone:
            is_compliant = True
            message = "obstacle outside GP site protection region A"
        elif is_cable:
            is_compliant = top_elevation_meters < base_height_meters
            message = (
                "cable within region A and below station altitude"
                if is_compliant
                else "cable within region A above station altitude"
            )
        else:
            is_compliant = False
            message = "non-cable obstacle enters region A"

        metrics = {
            "enteredProtectionZone": entered_protection_zone,
            "isCable": is_cable,
            "baseHeightMeters": base_height_meters,
            "topElevationMeters": top_elevation_meters,
        }
        if is_cable:
            metrics["allowedHeightMeters"] = base_height_meters

        return AnalysisRuleResult(
            station_id=self.protection_zone.station_id,
            station_type=self.protection_zone.station_type,
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=(
                None
                if obstacle.get("rawObstacleType") is None
                else str(obstacle["rawObstacleType"])
            ),
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
            metrics=metrics,
            standards_rule_code=self._resolve_result_standards_rule_code(obstacle),
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
        )

    def _resolve_standards_rule_code(self, *, station: object) -> str:
        return self.rule_code


class GpSiteProtectionGbRegionARule(_GpSiteProtectionRegionARuleBase):
    rule_code = "gp_site_protection_gb_region_a"
    rule_name = "gp_site_protection_gb_region_a"
    zone_code = "gp_site_protection_gb"
    zone_name = "GP site protection (GB)"


class GpSiteProtectionMhRegionARule(_GpSiteProtectionRegionARuleBase):
    rule_code = "gp_site_protection_mh_region_a"
    rule_name = "gp_site_protection_mh_region_a"
    zone_code = "gp_site_protection_mh"
    zone_name = "GP site protection (MH)"


__all__ = [
    "BoundGpSiteProtectionRegionRule",
    "GpSiteProtectionGbRegionARule",
    "GpSiteProtectionMhRegionARule",
]
