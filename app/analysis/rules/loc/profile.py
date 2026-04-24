from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.loc.forward_sector_3000m_15m import (
    LocForwardSector3000m15mRule,
)
from app.analysis.rules.loc.site_protection import LocSiteProtectionRule


class LocRuleProfile:
    # 初始化 LOC 最小规则集合。
    def __init__(self) -> None:
        self._site_protection_rule = LocSiteProtectionRule()
        self._forward_sector_rule = LocForwardSector3000m15mRule()

    # 执行 LOC 场地保护区规则。
    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
        runways: list[dict[str, object]],
    ) -> list[AnalysisRuleResult]:
        runway_context = self._resolve_runway_context(station=station, runways=runways)
        if runway_context is None:
            return []

        results: list[AnalysisRuleResult] = []
        for obstacle in obstacles:
            results.append(
                self._site_protection_rule.analyze(
                    station=station,
                    obstacle=obstacle,
                    station_point=station_point,
                    runway_context=runway_context,
                )
            )
            if self._is_forward_sector_applicable(obstacle=obstacle):
                results.append(
                    self._forward_sector_rule.analyze(
                        station=station,
                        obstacle=obstacle,
                        station_point=station_point,
                        runway_context=runway_context,
                    )
                )
        return results

    # 按障碍物分类筛选 LOC 前向扇区规则。
    def _is_forward_sector_applicable(self, *, obstacle: dict[str, object]) -> bool:
        return (
            str(obstacle["globalObstacleCategory"])
            in LocForwardSector3000m15mRule.SUPPORTED_CATEGORIES
        )

    # 按跑道号解析 LOC 所属跑道上下文。
    def _resolve_runway_context(
        self,
        *,
        station: object,
        runways: list[dict[str, object]],
    ) -> dict[str, object] | None:
        runway_no = getattr(station, "runway_no", None)
        if runway_no is None:
            return None

        for runway in runways:
            if runway.get("runNumber") == runway_no:
                return runway
        return None
