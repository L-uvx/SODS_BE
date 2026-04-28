from dataclasses import dataclass

from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape


@dataclass(slots=True)
class BoundGpSiteProtectionRegionRule(BoundObstacleRule):
    station_sub_type: str | None
    standards_rule_code: str

    # 执行 GP 场地保护区最小入区判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(
            self.protection_zone.local_geometry
        )
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
            standards_rule_code=self.standards_rule_code,
        )


__all__ = ["BoundGpSiteProtectionRegionRule"]
