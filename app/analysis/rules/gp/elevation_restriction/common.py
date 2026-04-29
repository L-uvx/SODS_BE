from dataclasses import dataclass

from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule


@dataclass(slots=True)
class BoundGpElevationRestrictionRule(BoundObstacleRule):
    standards_rule_code: str

    def build_result(
        self,
        *,
        obstacle: dict[str, object],
        is_compliant: bool,
        message: str,
        metrics: dict[str, float | str | bool | None],
    ) -> AnalysisRuleResult:
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
            standards_rule_code=self.standards_rule_code,
        )


__all__ = ["BoundGpElevationRestrictionRule"]
