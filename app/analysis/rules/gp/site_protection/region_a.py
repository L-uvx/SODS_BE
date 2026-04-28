from dataclasses import dataclass

from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.gp.site_protection.helpers import (
    GpSiteProtectionSharedContext,
    build_gp_site_protection_region_a_geometry,
)
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


@dataclass(slots=True)
class BoundGpSiteProtectionRegionRule(BoundObstacleRule):
    station_sub_type: str | None
    standards_rule_code: str

    def _resolve_result_standards_rule_code(self, obstacle: dict[str, object]) -> str:
        if self.protection_zone.region_code == "A" and str(
            obstacle.get("globalObstacleCategory")
        ) == "power_line_high_voltage_overhead":
            return f"{self.standards_rule_code}_cable"
        return self.standards_rule_code

    # 执行 GP 场地保护区最小入区判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(
            self.protection_zone.local_geometry
        )
        standards_rule_code = self._resolve_result_standards_rule_code(obstacle)
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
            is_compliant=not entered_protection_zone,
            message=(
                "obstacle outside GP site protection region"
                if not entered_protection_zone
                else "obstacle enters GP site protection region"
            ),
            metrics={"enteredProtectionZone": entered_protection_zone},
            standards_rule_code=standards_rule_code,
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
    ) -> BoundGpSiteProtectionRegionRule:
        region_geometry = build_gp_site_protection_region_a_geometry(shared_context)
        return BoundGpSiteProtectionRegionRule(
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
