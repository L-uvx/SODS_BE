from dataclasses import dataclass

from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.loc.run_area_protection.constants import SUPPORTED_CATEGORIES
from app.analysis.rules.loc.run_area_protection.helpers import (
    LocRunAreaProtectionSharedContext,
    build_loc_run_area_region_d_geometry,
)
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


@dataclass(slots=True)
class BoundLocRunAreaProtectionRegionDRule(BoundObstacleRule):
    # 执行 LOC 运行保护区第 D 区判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_category = str(obstacle["globalObstacleCategory"])
        is_applicable = obstacle_category in SUPPORTED_CATEGORIES
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(
            self.protection_zone.local_geometry
        )
        return AnalysisRuleResult(
            station_id=self.protection_zone.station_id,
            station_type=self.protection_zone.station_type,
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=obstacle["rawObstacleType"],
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
                "obstacle type not restricted by run area sensitive standard"
                if not is_applicable
                else (
                    "obstacle outside run area sensitive region"
                    if not entered_protection_zone
                    else "obstacle enters run area sensitive region"
                )
            ),
            metrics={
                "areaType": "sensitive",
                "enteredProtectionZone": entered_protection_zone,
            },
            standards_rule_code="loc_run_area_protection_sensitive",
        )


class LocRunAreaProtectionRegionDRule(ObstacleRule):
    rule_code = "loc_run_area_protection_region_d"
    rule_name = "loc_run_area_protection_region_d"
    zone_code = "loc_run_area_protection"
    zone_name = resolve_protection_zone_name(zone_code=zone_code)

    # 绑定 LOC 运行保护区第 D 区。
    def bind(
        self,
        *,
        station: object,
        shared_context: LocRunAreaProtectionSharedContext,
    ) -> BoundLocRunAreaProtectionRegionDRule:
        region_geometry = build_loc_run_area_region_d_geometry(shared_context)
        return BoundLocRunAreaProtectionRegionDRule(
            protection_zone=build_protection_zone_spec(
                station_id=int(station.id),
                station_type=str(station.station_type),
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                region_code="D",
                region_name="D",
                local_geometry=region_geometry.local_geometry,
                vertical_definition={
                    "mode": "flat",
                    "baseReference": "station",
                    "baseHeightMeters": float(getattr(station, "altitude", 0.0) or 0.0),
                },
            )
        )
