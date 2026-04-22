from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.loc import LocRuleProfile
from app.analysis.rules.ndb import NdbRuleProfile


class StationAnalysisDispatcher:
    # 初始化按台站类型分发的分析入口。
    def __init__(self) -> None:
        self._ndb_profile = NdbRuleProfile()
        self._loc_profile = LocRuleProfile()

    # 按台站类型执行分析并返回规则结果集合。
    def analyze_station(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
        runways: list[dict[str, object]],
    ) -> list[AnalysisRuleResult]:
        if station.station_type == "LOC":
            return self._loc_profile.analyze(
                station=station,
                obstacles=obstacles,
                station_point=station_point,
                runways=runways,
            )

        if station.station_type == "NDB":
            return self._ndb_profile.analyze(
                station=station,
                obstacles=obstacles,
                station_point=station_point,
                runways=runways,
            )
        return []