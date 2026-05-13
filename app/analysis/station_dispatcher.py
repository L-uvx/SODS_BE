from dataclasses import dataclass

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.adsb import AdsbRuleProfile
from app.analysis.rules.gp import GpRuleProfile
from app.analysis.rules.hf import HfRuleProfile
from app.analysis.rules.loc import LocRuleProfile
from app.analysis.rules.mb import MbRuleProfile
from app.analysis.rules.ndb import NdbRuleProfile
from app.analysis.rules.radar import RadarRuleProfile
from app.analysis.rules.surface_detection_radar import SurfaceDetectionRadarRuleProfile
from app.analysis.rules.vhf import VhfRuleProfile
from app.analysis.rules.vor import VorRuleProfile
from app.analysis.rules.weather_radar import WeatherRadarRuleProfile
from app.analysis.rules.wind_radar import WindRadarRuleProfile


@dataclass(slots=True)
class StationAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class StationAnalysisDispatcher:
    # 初始化按台站类型分发的分析入口。
    def __init__(self) -> None:
        self._adsb_profile = AdsbRuleProfile()
        self._ndb_profile = NdbRuleProfile()
        self._loc_profile = LocRuleProfile()
        self._hf_profile = HfRuleProfile()
        self._mb_profile = MbRuleProfile()
        self._gp_profile = GpRuleProfile()
        self._vor_profile = VorRuleProfile()
        self._vhf_profile = VhfRuleProfile()
        self._radar_profile = RadarRuleProfile()
        self._weather_radar_profile = WeatherRadarRuleProfile()
        self._wind_radar_profile = WindRadarRuleProfile()
        self._surface_detection_radar_profile = SurfaceDetectionRadarRuleProfile()
        self._bind_paths: dict[str, tuple[object, bool]] = {
            "ADS_B": (self._adsb_profile, False),
            "LOC": (self._loc_profile, True),
            "NDB": (self._ndb_profile, False),
            "HF": (self._hf_profile, False),
            "MB": (self._mb_profile, True),
            "GP": (self._gp_profile, True),
            "VOR": (self._vor_profile, False),
            "VHF": (self._vhf_profile, False),
            "RADAR": (self._radar_profile, False),
            "WeatherRadar": (self._weather_radar_profile, False),
            "WindRadar": (self._wind_radar_profile, False),
            "Surface_Detection_Radar": (self._surface_detection_radar_profile, True),
        }

    # 按台站类型执行分析并返回规则结果与保护区集合。
    def analyze_station(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
        runways: list[dict[str, object]],
    ) -> StationAnalysisPayload:
        if station.station_type == "ADS_B":
            payload = self._adsb_profile.analyze(
                station=station,
                obstacles=obstacles,
                station_point=station_point,
            )
            return StationAnalysisPayload(
                rule_results=payload.rule_results,
                protection_zones=payload.protection_zones,
            )

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

        if station.station_type == "HF":
            payload = self._hf_profile.analyze(
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
        if station.station_type == "VHF":
            payload = self._vhf_profile.analyze(
                station=station,
                obstacles=obstacles,
                station_point=station_point,
            )
            return StationAnalysisPayload(
                rule_results=payload.rule_results,
                protection_zones=payload.protection_zones,
            )
        if station.station_type == "RADAR":
            payload = self._radar_profile.analyze(
                station=station,
                obstacles=obstacles,
                station_point=station_point,
            )
            return StationAnalysisPayload(
                rule_results=payload.rule_results,
                protection_zones=payload.protection_zones,
            )
        if station.station_type == "WeatherRadar":
            payload = self._weather_radar_profile.analyze(
                station=station,
                obstacles=obstacles,
                station_point=station_point,
            )
            return StationAnalysisPayload(
                rule_results=payload.rule_results,
                protection_zones=payload.protection_zones,
            )
        if station.station_type == "WindRadar":
            payload = self._wind_radar_profile.analyze(
                station=station,
                obstacles=obstacles,
                station_point=station_point,
            )
            return StationAnalysisPayload(
                rule_results=payload.rule_results,
                protection_zones=payload.protection_zones,
            )
        if station.station_type == "Surface_Detection_Radar":
            payload = self._surface_detection_radar_profile.analyze(
                station=station,
                obstacles=obstacles,
                station_point=station_point,
                runways=runways,
            )
            return StationAnalysisPayload(
                rule_results=payload.rule_results,
                protection_zones=payload.protection_zones,
            )
        return StationAnalysisPayload(rule_results=[], protection_zones=[])

    # 按台站类型绑定全部规则并返回保护区集合（不含障碍物分析）。
    def bind_station_protection_zones(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
        runways: list[dict[str, object]],
    ) -> list[ProtectionZoneSpec]:
        path = self._bind_paths.get(station.station_type)
        if path is None:
            return []
        profile, needs_runways = path
        if needs_runways:
            return profile.bind_protection_zones(
                station=station, station_point=station_point, runways=runways,
            )
        return profile.bind_protection_zones(
            station=station, station_point=station_point,
        )
