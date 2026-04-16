from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.ndb.minimum_distance_150m import NdbMinimumDistance150mRule
from app.analysis.rules.ndb.minimum_distance_300m import NdbMinimumDistance300mRule
from app.analysis.rules.ndb.minimum_distance_500m import NdbMinimumDistance500mRule
from app.analysis.rules.ndb.minimum_distance_50m import NdbMinimumDistance50mRule


class NdbRuleProfile:
    def __init__(self) -> None:
        self._rules = {
            "building_general": NdbMinimumDistance50mRule(),
            "building_hangar": NdbMinimumDistance50mRule(),
            "building_terminal": NdbMinimumDistance50mRule(),
            "road": NdbMinimumDistance50mRule(),
            "airport_ring_road": NdbMinimumDistance50mRule(),
            "tree_or_forest": NdbMinimumDistance50mRule(),
            "railway_electrified": NdbMinimumDistance150mRule(),
            "railway_non_electrified": NdbMinimumDistance150mRule(),
            "power_line_low_voltage_overhead": NdbMinimumDistance150mRule(),
            "power_or_communication_cable": NdbMinimumDistance150mRule(),
            "hill": NdbMinimumDistance300mRule(),
            "embankment": NdbMinimumDistance300mRule(),
            "power_line_high_voltage_overhead": NdbMinimumDistance500mRule(),
        }

    def analyze(
        self,
        *,
        station: object,
        obstacle: dict[str, object],
        station_point: tuple[float, float],
    ) -> AnalysisRuleResult | None:
        category = str(obstacle["globalObstacleCategory"])
        rule = self._rules.get(category)
        if rule is None:
            return None
        return rule.analyze(
            station=station,
            obstacle=obstacle,
            station_point=station_point,
        )
