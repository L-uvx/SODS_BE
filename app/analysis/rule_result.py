from dataclasses import dataclass


@dataclass(slots=True)
class AnalysisRuleResult:
    station_id: int
    station_type: str
    obstacle_id: int
    obstacle_name: str
    raw_obstacle_type: str | None
    global_obstacle_category: str
    rule_name: str
    zone_code: str
    zone_name: str
    region_code: str
    region_name: str
    zone_definition: dict[str, object]
    is_applicable: bool
    is_compliant: bool
    message: str
    metrics: dict[str, float | str | bool | None]
