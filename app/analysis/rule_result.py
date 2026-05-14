from dataclasses import dataclass

from app.analysis.standards import AnalysisStandardSet


@dataclass(slots=True)
class AnalysisRuleResult:
    station_id: int
    station_type: str
    obstacle_id: int
    obstacle_name: str
    raw_obstacle_type: str | None
    global_obstacle_category: str
    rule_code: str
    rule_name: str
    zone_code: str
    zone_name: str
    region_code: str
    region_name: str
    is_applicable: bool
    is_compliant: bool
    message: str
    metrics: dict[str, float | str | bool | None]
    standards_rule_code: str | None = None
    standards: AnalysisStandardSet | None = None
    over_distance_meters: float = 0.0
    azimuth_degrees: float = 0.0
    max_horizontal_angle_degrees: float = 0.0
    min_horizontal_angle_degrees: float = 0.0
    relative_height_meters: float = 0.0
    is_in_radius: bool = False
    is_in_zone: bool = False
    is_mid: bool = False
    is_filter_limit: bool = False
    is_filter_intersect: bool = False
    details: str = ""
