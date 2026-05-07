from dataclasses import dataclass

from shapely.geometry import Point

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.radar.common import BoundRadarCircleRule
from app.analysis.rules.radar.config import (
    RADAR_A_HORIZONTAL_LIMIT_ANGLE_DEGREES,
    RADAR_A_SITE_PROTECTION_RADIUS_METERS,
    RADAR_A_VERTICAL_LIMIT_ANGLE_DEGREES,
    RADAR_B_MINIMUM_DISTANCE_BY_CATEGORY,
    RADAR_C_ROTATING_REFLECTOR_CATEGORY,
)
from app.analysis.rules.radar.minimum_distance import RadarMinimumDistanceRule
from app.analysis.rules.radar.rotating_reflector_16km import RadarRotatingReflector16kmRule
from app.analysis.rules.radar.site_protection import RadarSiteProtectionRule


@dataclass(slots=True)
class RadarStationAnalysisPayload:
    rule_results: list[AnalysisRuleResult]
    protection_zones: list[ProtectionZoneSpec]


class RadarRuleProfile:
    # 初始化 Radar A/B/C 规则集合。
    def __init__(self) -> None:
        self._site_protection_rule = RadarSiteProtectionRule()
        self._minimum_distance_rules_by_radius = {
            radius: RadarMinimumDistanceRule(minimum_distance_meters=radius)
            for radius in sorted(set(RADAR_B_MINIMUM_DISTANCE_BY_CATEGORY.values()))
        }
        self._rotating_reflector_rule = RadarRotatingReflector16kmRule()

    # 执行 Radar A/B/C 规则。
    def analyze(
        self,
        *,
        station: object,
        obstacles: list[dict[str, object]],
        station_point: tuple[float, float],
    ) -> RadarStationAnalysisPayload:
        rule_results: list[AnalysisRuleResult] = []
        protection_zones: list[ProtectionZoneSpec] = []
        bound_site_protection_rule = self._site_protection_rule.bind(
            station=station,
            station_point=station_point,
            radius_meters=RADAR_A_SITE_PROTECTION_RADIUS_METERS,
            vertical_limit_angle_degrees=RADAR_A_VERTICAL_LIMIT_ANGLE_DEGREES,
            horizontal_limit_angle_degrees=RADAR_A_HORIZONTAL_LIMIT_ANGLE_DEGREES,
        )
        bound_minimum_distance_rules: dict[float, BoundRadarCircleRule] = {}
        bound_rotating_reflector_rule: BoundRadarCircleRule | None = None

        if bound_site_protection_rule is not None:
            protection_zones.append(bound_site_protection_rule.protection_zone)

        for obstacle in obstacles:
            category = str(obstacle["globalObstacleCategory"])
            if bound_site_protection_rule is not None:
                obstacle_shape = resolve_obstacle_shape(obstacle)
                actual_distance_meters = float(obstacle_shape.distance(Point(station_point)))
                if actual_distance_meters <= RADAR_A_SITE_PROTECTION_RADIUS_METERS:
                    rule_results.append(bound_site_protection_rule.analyze(obstacle))

            minimum_distance = RADAR_B_MINIMUM_DISTANCE_BY_CATEGORY.get(category)
            if minimum_distance is not None:
                bound_rule = bound_minimum_distance_rules.get(minimum_distance)
                if bound_rule is None:
                    bound_rule = self._minimum_distance_rules_by_radius[minimum_distance].bind(
                        station=station,
                        station_point=station_point,
                    )
                    bound_minimum_distance_rules[minimum_distance] = bound_rule
                    protection_zones.append(bound_rule.protection_zone)
                rule_results.append(bound_rule.analyze(obstacle))

            if category == RADAR_C_ROTATING_REFLECTOR_CATEGORY:
                if bound_rotating_reflector_rule is None:
                    bound_rotating_reflector_rule = self._rotating_reflector_rule.bind(
                        station=station,
                        station_point=station_point,
                    )
                    protection_zones.append(bound_rotating_reflector_rule.protection_zone)
                rule_results.append(bound_rotating_reflector_rule.analyze(obstacle))

        return RadarStationAnalysisPayload(
            rule_results=rule_results,
            protection_zones=protection_zones,
        )
