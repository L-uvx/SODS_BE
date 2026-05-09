from dataclasses import dataclass

from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule


@dataclass(slots=True)
class BoundGpSiteProtectionRegionRule(BoundObstacleRule):
    station_sub_type: str | None
    standards_rule_code: str
    station_point: tuple[float, float]

    def build_result(
        self,
        *,
        obstacle: dict[str, object],
        is_compliant: bool,
        message: str,
        metrics: dict[str, float | str | bool | None],
        standards_rule_code: str | None = None,
        over_distance_meters: float = 0.0,
        azimuth_degrees: float = 0.0,
        max_horizontal_angle_degrees: float = 0.0,
        min_horizontal_angle_degrees: float = 0.0,
        relative_height_meters: float = 0.0,
        is_in_radius: bool = False,
        is_in_zone: bool = False,
        details: str = "",
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
            standards_rule_code=(
                self.standards_rule_code
                if standards_rule_code is None
                else standards_rule_code
            ),
            over_distance_meters=over_distance_meters,
            azimuth_degrees=azimuth_degrees,
            max_horizontal_angle_degrees=max_horizontal_angle_degrees,
            min_horizontal_angle_degrees=min_horizontal_angle_degrees,
            relative_height_meters=relative_height_meters,
            is_in_radius=is_in_radius,
            is_in_zone=is_in_zone,
            details=details,
        )


__all__ = ["BoundGpSiteProtectionRegionRule"]
