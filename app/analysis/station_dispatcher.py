from dataclasses import dataclass

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.gp import GpRuleProfile
from app.analysis.rules.loc import LocRuleProfile
from app.analysis.rules.mb import MbRuleProfile
from app.analysis.rules.ndb import NdbRuleProfile
from app.analysis.rules.vor import VorRuleProfile


@dataclass(slots=True)
class StationAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class StationAnalysisDispatcher:
    # 初始化按台站类型分发的分析入口。
    def __init__(self) -> None:
        self._ndb_profile = NdbRuleProfile()
        self._loc_profile = LocRuleProfile()
        self._mb_profile = MbRuleProfile()
        self._gp_profile = GpRuleProfile()
        self._vor_profile = VorRuleProfile()

    # 按台站类型执行分析并返回规则结果与保护区集合。
    def analyze_station(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
        runways: list[dict[str, object]],
    ) -> StationAnalysisPayload:
        if station.station_type == "LOC":
            payload = self._loc_profile.analyze(
                station=station,
                obstacles=obstacles,
                station_point=station_point,
                runways=runways,
            )
            return StationAnalysisPayload(
                rule_results=payload.rule_results,
                protection_zones=payload.protection_zones,
            )

        if station.station_type == "NDB":
            payload = self._ndb_profile.analyze(
                station=station,
                obstacles=obstacles,
                station_point=station_point,
            )
            return StationAnalysisPayload(
                rule_results=payload.rule_results,
                protection_zones=payload.protection_zones,
            )

        if station.station_type == "MB":
            payload = self._mb_profile.analyze(
                station=station,
                obstacles=obstacles,
                station_point=station_point,
                runways=runways,
            )
            return StationAnalysisPayload(
                rule_results=payload.rule_results,
                protection_zones=payload.protection_zones,
            )

        if station.station_type == "GP":
            payload = self._gp_profile.analyze(
                station=station,
                obstacles=obstacles,
                station_point=station_point,
                runways=runways,
            )
            return StationAnalysisPayload(
                rule_results=payload.rule_results,
                protection_zones=payload.protection_zones,
            )
        if station.station_type == "VOR":
            payload = self._vor_profile.analyze(
                station=station,
                obstacles=obstacles,
                station_point=station_point,
            )
            return StationAnalysisPayload(
                rule_results=payload.rule_results,
                protection_zones=payload.protection_zones,
            )
        return StationAnalysisPayload(rule_results=[], protection_zones=[])
