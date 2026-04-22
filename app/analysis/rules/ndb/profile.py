from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.ndb.conical_clearance import NdbConicalClearance3DegRule
from app.analysis.rules.ndb.minimum_distance_150m import NdbMinimumDistance150mRule
from app.analysis.rules.ndb.minimum_distance_300m import NdbMinimumDistance300mRule
from app.analysis.rules.ndb.minimum_distance_500m import NdbMinimumDistance500mRule
from app.analysis.rules.ndb.minimum_distance_50m import NdbMinimumDistance50mRule


class NdbRuleProfile:
    # 初始化 NDB 分类到规则实例的映射。
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
        self._conical_rule = NdbConicalClearance3DegRule()

    # 按障碍物分类执行 NDB 规则集合。
    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
        runways: list[dict[str, object]],
    ) -> list[AnalysisRuleResult]:
        del runways
        results: list[AnalysisRuleResult] = []
        for obstacle in obstacles:
            category = str(obstacle["globalObstacleCategory"])
            rule = self._rules.get(category)
            if rule is not None:
                results.append(
                    rule.analyze(
                        station=station,
                        obstacle=obstacle,
                        station_point=station_point,
                    )
                )
            results.append(
                self._conical_rule.analyze(
                    station=station,
                    obstacle=obstacle,
                    station_point=station_point,
                    station_altitude=(
                        float(station.altitude) if station.altitude is not None else None
                    ),
                )
            )
        return results
