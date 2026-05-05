# app/analysis/rules/vor/profile.py
from dataclasses import dataclass

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.vor.reflector_mask_area import VorReflectorMaskAreaRule


@dataclass(slots=True)
class VorStationAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class VorRuleProfile:
    # 初始化 VOR 规则实例。
    def __init__(self) -> None:
        self._reflector_mask_rule = VorReflectorMaskAreaRule()

    # 执行 VOR 台站分析。
    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
    ) -> VorStationAnalysisPayload:
        bound_rule = self._reflector_mask_rule.bind(
            station=station,
            station_point=station_point,
        )

        if bound_rule is None:
            return VorStationAnalysisPayload(
                rule_results=[], protection_zones=[]
            )
        results: list[AnalysisRuleResult] = []
        protection_zones = [bound_rule.protection_zone]
        for obstacle in obstacles:
            results.append(bound_rule.analyze(obstacle))
        return VorStationAnalysisPayload(
            rule_results=results,
            protection_zones=protection_zones,
        )
