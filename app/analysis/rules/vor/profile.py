# app/analysis/rules/vor/profile.py
from dataclasses import dataclass

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.vor.datum_plane import (
    Vor100mDatumPlaneRule,
    Vor200mDatumPlaneHighVoltageRule,
    Vor200mDatumPlaneRule,
    Vor300mDatumPlaneRule,
    Vor500mDatumPlaneRule,
)
from app.analysis.rules.vor.elevation_angle import (
    Vor100_200_1_5_Rule,
    Vor200_300_1_5_Rule,
    Vor300Outside2_5_Rule,
)
from app.analysis.rules.vor.reflector_mask_area import VorReflectorMaskAreaRule


@dataclass(slots=True)
class VorStationAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class VorRuleProfile:
    def __init__(self) -> None:
        self._reflector_mask_rule = VorReflectorMaskAreaRule()
        self._datum_plane_100m = Vor100mDatumPlaneRule()
        self._elevation_angle_100_200 = Vor100_200_1_5_Rule()
        self._datum_plane_200m = Vor200mDatumPlaneRule()
        self._datum_plane_200m_hv = Vor200mDatumPlaneHighVoltageRule()
        self._elevation_angle_200_300 = Vor200_300_1_5_Rule()
        self._datum_plane_300m = Vor300mDatumPlaneRule()
        self._datum_plane_500m = Vor500mDatumPlaneRule()
        self._elevation_angle_300_outside = Vor300Outside2_5_Rule()

    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
    ) -> VorStationAnalysisPayload:
        categories_present = {
            str(obstacle["globalObstacleCategory"]) for obstacle in obstacles
        }

        protection_zones: list[ProtectionZoneSpec] = []
        results: list[AnalysisRuleResult] = []

        # 反射网阴影区（全类型通用）
        bound_reflector = self._reflector_mask_rule.bind(
            station=station, station_point=station_point,
        )
        if bound_reflector is not None:
            protection_zones.append(bound_reflector.protection_zone)
            for obstacle in obstacles:
                results.append(bound_reflector.analyze(obstacle))

        # 100m 基准面：排除高压+铁路，匹配后才 bind
        if categories_present - _SKIP_100M:
            bound_100m = self._datum_plane_100m.bind(
                station=station, station_point=station_point,
            )
            if bound_100m is not None:
                protection_zones.append(bound_100m.protection_zone)
                for obstacle in obstacles:
                    if str(obstacle["globalObstacleCategory"]) not in _SKIP_100M:
                        results.append(bound_100m.analyze(obstacle))

        # 100m-200m 1.5° 仰角区（仅树木）
        if categories_present & _MATCHED_100_200_1_5:
            bound_100_200_1_5 = self._elevation_angle_100_200.bind(
                station=station, station_point=station_point,
            )
            if bound_100_200_1_5 is not None:
                protection_zones.append(bound_100_200_1_5.protection_zone)
                for obstacle in obstacles:
                    if str(obstacle["globalObstacleCategory"]) in _MATCHED_100_200_1_5:
                        results.append(bound_100_200_1_5.analyze(obstacle))

        # 200m 基准面（通用）：排除高压+铁路+树木
        if categories_present - _SKIP_200M:
            bound_200m = self._datum_plane_200m.bind(
                station=station, station_point=station_point,
            )
            if bound_200m is not None:
                protection_zones.append(bound_200m.protection_zone)
                for obstacle in obstacles:
                    if str(obstacle["globalObstacleCategory"]) not in _SKIP_200M:
                        results.append(bound_200m.analyze(obstacle))

        # 200m-300m 1.5° 仰角区：排除高压+铁路，匹配后才 bind
        if categories_present - _SKIP_200_300_1_5:
            bound_200_300_1_5 = self._elevation_angle_200_300.bind(
                station=station, station_point=station_point,
            )
            if bound_200_300_1_5 is not None:
                protection_zones.append(bound_200_300_1_5.protection_zone)
                for obstacle in obstacles:
                    if str(obstacle["globalObstacleCategory"]) not in _SKIP_200_300_1_5:
                        results.append(bound_200_300_1_5.analyze(obstacle))

        # 200m 基准面（35kV 高压线）
        if "power_line_high_voltage_35kv" in categories_present:
            bound_200m_hv = self._datum_plane_200m_hv.bind(
                station=station, station_point=station_point,
            )
            if bound_200m_hv is not None:
                protection_zones.append(bound_200m_hv.protection_zone)
                for obstacle in obstacles:
                    if str(obstacle["globalObstacleCategory"]) == "power_line_high_voltage_35kv":
                        results.append(bound_200m_hv.analyze(obstacle))

        # 300m 基准面（仅铁路）
        if categories_present & _MATCHED_300M:
            bound_300m = self._datum_plane_300m.bind(
                station=station, station_point=station_point,
            )
            if bound_300m is not None:
                protection_zones.append(bound_300m.protection_zone)
                for obstacle in obstacles:
                    if str(obstacle["globalObstacleCategory"]) in _MATCHED_300M:
                        results.append(bound_300m.analyze(obstacle))

        # 500m 基准面（仅 110kV+ 高压线）
        if categories_present & _MATCHED_500M:
            bound_500m = self._datum_plane_500m.bind(
                station=station, station_point=station_point,
            )
            if bound_500m is not None:
                protection_zones.append(bound_500m.protection_zone)
                for obstacle in obstacles:
                    if str(obstacle["globalObstacleCategory"]) in _MATCHED_500M:
                        results.append(bound_500m.analyze(obstacle))

        # 300m 外 2.5° 仰角区（全类型；距离委托逻辑由规则内部处理）
        bound_300_outside_2_5 = self._elevation_angle_300_outside.bind(
            station=station, station_point=station_point,
        )
        if bound_300_outside_2_5 is not None:
            protection_zones.append(bound_300_outside_2_5.protection_zone)
            for obstacle in obstacles:
                results.append(bound_300_outside_2_5.analyze(obstacle))

        return VorStationAnalysisPayload(
            rule_results=results,
            protection_zones=protection_zones,
        )


_SKIP_HIGH_VOLTAGE_AND_RAILWAY = frozenset({
    "power_line_high_voltage_35kv_below",
    "power_line_high_voltage_35kv",
    "power_line_high_voltage_110kv",
    "power_line_high_voltage_220kv",
    "power_line_high_voltage_330kv",
    "power_line_high_voltage_500kv_and_above",
    "railway_electrified",
    "railway_non_electrified",
})

_SKIP_100M = _SKIP_HIGH_VOLTAGE_AND_RAILWAY

_SKIP_200M = _SKIP_HIGH_VOLTAGE_AND_RAILWAY | frozenset({
    "tree_or_forest",
})

_MATCHED_100_200_1_5 = frozenset({
    "tree_or_forest",
})

_SKIP_200_300_1_5 = frozenset({
    "power_line_high_voltage_110kv",
    "power_line_high_voltage_220kv",
    "power_line_high_voltage_330kv",
    "power_line_high_voltage_500kv_and_above",
    "railway_electrified",
    "railway_non_electrified",
})

_MATCHED_300M = frozenset({
    "railway_electrified",
    "railway_non_electrified",
})

_MATCHED_500M = frozenset({
    "power_line_high_voltage_110kv",
    "power_line_high_voltage_220kv",
    "power_line_high_voltage_330kv",
    "power_line_high_voltage_500kv_and_above",
})
