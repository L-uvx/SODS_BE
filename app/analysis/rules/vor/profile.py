# app/analysis/rules/vor/profile.py
from dataclasses import dataclass

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.vor.datum_plane_100m import Vor100mDatumPlaneRule
from app.analysis.rules.vor.datum_plane_200m import Vor200mDatumPlaneRule
from app.analysis.rules.vor.datum_plane_200m_high_voltage import Vor200mDatumPlaneHighVoltageRule
from app.analysis.rules.vor.datum_plane_300m import Vor300mDatumPlaneRule
from app.analysis.rules.vor.datum_plane_500m import Vor500mDatumPlaneRule
from app.analysis.rules.vor.reflector_mask_area import VorReflectorMaskAreaRule


@dataclass(slots=True)
class VorStationAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class VorRuleProfile:
    # 初始化 VOR 规则实例。
    def __init__(self) -> None:
        self._reflector_mask_rule = VorReflectorMaskAreaRule()
        self._datum_plane_100m = Vor100mDatumPlaneRule()
        self._datum_plane_200m = Vor200mDatumPlaneRule()
        self._datum_plane_200m_hv = Vor200mDatumPlaneHighVoltageRule()
        self._datum_plane_300m = Vor300mDatumPlaneRule()
        self._datum_plane_500m = Vor500mDatumPlaneRule()

    # 执行 VOR 台站分析。
    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
    ) -> VorStationAnalysisPayload:
        # 绑定所有规则（缺参静默跳过）
        bound_reflector = self._reflector_mask_rule.bind(
            station=station,
            station_point=station_point,
        )
        bound_100m = self._datum_plane_100m.bind(
            station=station,
            station_point=station_point,
        )
        bound_200m = self._datum_plane_200m.bind(
            station=station,
            station_point=station_point,
        )
        bound_200m_hv = self._datum_plane_200m_hv.bind(
            station=station,
            station_point=station_point,
        )
        bound_300m = self._datum_plane_300m.bind(
            station=station,
            station_point=station_point,
        )
        bound_500m = self._datum_plane_500m.bind(
            station=station,
            station_point=station_point,
        )

        protection_zones: list[ProtectionZoneSpec] = []
        results: list[AnalysisRuleResult] = []

        # 反射网阴影区（全障碍物类型通用）
        if bound_reflector is not None:
            if bound_reflector.protection_zone not in protection_zones:
                protection_zones.append(bound_reflector.protection_zone)
            for obstacle in obstacles:
                results.append(bound_reflector.analyze(obstacle))

        # 100m 基准面：排除高压+铁路
        if bound_100m is not None:
            if bound_100m.protection_zone not in protection_zones:
                protection_zones.append(bound_100m.protection_zone)
            for obstacle in obstacles:
                category = str(obstacle["globalObstacleCategory"])
                if category not in _SKIP_100M:
                    results.append(bound_100m.analyze(obstacle))

        # 200m 基准面（通用）：排除高压+铁路+树木，距离门槛 100m
        if bound_200m is not None:
            if bound_200m.protection_zone not in protection_zones:
                protection_zones.append(bound_200m.protection_zone)
            for obstacle in obstacles:
                category = str(obstacle["globalObstacleCategory"])
                if category not in _SKIP_200M:
                    results.append(bound_200m.analyze(obstacle))

        # 200m 基准面（35kV 高压线）
        if bound_200m_hv is not None:
            if bound_200m_hv.protection_zone not in protection_zones:
                protection_zones.append(bound_200m_hv.protection_zone)
            for obstacle in obstacles:
                category = str(obstacle["globalObstacleCategory"])
                if category == "power_line_high_voltage_35kv":
                    results.append(bound_200m_hv.analyze(obstacle))

        # 300m 基准面（仅铁路）
        if bound_300m is not None:
            if bound_300m.protection_zone not in protection_zones:
                protection_zones.append(bound_300m.protection_zone)
            for obstacle in obstacles:
                category = str(obstacle["globalObstacleCategory"])
                if category in _MATCHED_300M:
                    results.append(bound_300m.analyze(obstacle))

        # 500m 基准面（仅 110kV+ 高压线）
        if bound_500m is not None:
            if bound_500m.protection_zone not in protection_zones:
                protection_zones.append(bound_500m.protection_zone)
            for obstacle in obstacles:
                category = str(obstacle["globalObstacleCategory"])
                if category in _MATCHED_500M:
                    results.append(bound_500m.analyze(obstacle))

        return VorStationAnalysisPayload(
            rule_results=results,
            protection_zones=protection_zones,
        )


_SKIP_100M = frozenset({
    "power_line_high_voltage_35kv_below",
    "power_line_high_voltage_35kv",
    "power_line_high_voltage_110kv",
    "power_line_high_voltage_220kv",
    "power_line_high_voltage_330kv",
    "power_line_high_voltage_500kv_and_above",
    "railway_electrified",
    "railway_non_electrified",
})

_SKIP_200M = frozenset({
    "power_line_high_voltage_35kv_below",
    "power_line_high_voltage_35kv",
    "power_line_high_voltage_110kv",
    "power_line_high_voltage_220kv",
    "power_line_high_voltage_330kv",
    "power_line_high_voltage_500kv_and_above",
    "railway_electrified",
    "railway_non_electrified",
    "tree_or_forest",
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
