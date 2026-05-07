from dataclasses import dataclass

from app.analysis.rules.radar import RadarRuleProfile
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.protection_zone_spec import ProtectionZoneSpec

from .runway_triangle import SurfaceDetectionRadarRunwayTriangleRule
from .triangle_utils import find_matching_runway


@dataclass(slots=True)
class SurfaceDetectionRadarAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class SurfaceDetectionRadarRuleProfile:
    def __init__(self) -> None:
        self._radar_profile = RadarRuleProfile()
        self._runway_triangle_rule = SurfaceDetectionRadarRunwayTriangleRule()

    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
        runways: list[dict[str, object]],
    ) -> SurfaceDetectionRadarAnalysisPayload:
        runway = find_matching_runway(station=station, runways=runways)
        if runway is None:
            return SurfaceDetectionRadarAnalysisPayload(rule_results=[], protection_zones=[])

        bound_triangle_rule = self._runway_triangle_rule.bind(
            station=station,
            station_point=station_point,
            runway=runway,
        )
        base_payload = self._radar_profile.analyze(
            station=station,
            obstacles=obstacles,
            station_point=station_point,
        )

        triangle_results: list[AnalysisRuleResult] = []
        is_in_triangle_by_obstacle_id: dict[int, bool] = {}
        for obstacle in obstacles:
            triangle_result = bound_triangle_rule.analyze(obstacle)
            triangle_results.append(triangle_result)
            is_in_triangle_by_obstacle_id[int(obstacle["obstacleId"])] = bool(
                triangle_result.metrics["isInRunwayTriangle"]
            )

        gated_base_results: list[AnalysisRuleResult] = []
        for result in base_payload.rule_results:
            is_in_triangle = is_in_triangle_by_obstacle_id.get(result.obstacle_id, False)
            metrics = dict(result.metrics)
            metrics["triangleGateApplied"] = True
            metrics["isInRunwayTriangle"] = is_in_triangle
            metrics["gatedByRunwayTriangle"] = not is_in_triangle
            gated_base_results.append(
                AnalysisRuleResult(
                    station_id=result.station_id,
                    station_type=result.station_type,
                    obstacle_id=result.obstacle_id,
                    obstacle_name=result.obstacle_name,
                    raw_obstacle_type=result.raw_obstacle_type,
                    global_obstacle_category=result.global_obstacle_category,
                    rule_code=result.rule_code,
                    rule_name=result.rule_name,
                    zone_code=result.zone_code,
                    zone_name=result.zone_name,
                    region_code=result.region_code,
                    region_name=result.region_name,
                    is_applicable=result.is_applicable if is_in_triangle else False,
                    is_compliant=result.is_compliant,
                    message=result.message,
                    metrics=metrics,
                    standards_rule_code=result.standards_rule_code,
                    standards=result.standards,
                )
            )

        protection_zones: list[ProtectionZoneSpec] = [bound_triangle_rule.protection_zone]
        protection_zones.extend(base_payload.protection_zones)

        return SurfaceDetectionRadarAnalysisPayload(
            rule_results=[*triangle_results, *gated_base_results],
            protection_zones=protection_zones,
        )
