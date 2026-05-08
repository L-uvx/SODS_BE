from dataclasses import dataclass

from shapely.geometry import Point

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.vhf.config import VHF_STANDARDS_RULE_CODE_BY_CATEGORY
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import (
    build_circle_polygon,
    ensure_multipolygon,
    resolve_obstacle_shape,
)
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


class VhfRule(ObstacleRule):
    # 绑定单个 VHF 台站上下文。
    def bind(self, *args, **kwargs) -> BoundObstacleRule:  # pragma: no cover
        raise NotImplementedError


@dataclass(slots=True)
class BoundVhfCircleRule(BoundObstacleRule):
    station_point: tuple[float, float]
    minimum_distance_meters: float

    # 按障碍物分类解析 VHF 条文键，避免共用规则档位时标准错配。
    def _resolve_standards_rule_code(self, obstacle: dict[str, object]) -> str:
        category = str(obstacle["globalObstacleCategory"])
        return VHF_STANDARDS_RULE_CODE_BY_CATEGORY.get(category, self.protection_zone.rule_code)

    # 执行已绑定的 VHF 圆形最小间距判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(self.protection_zone.local_geometry)
        actual_distance_meters = float(obstacle_shape.distance(Point(self.station_point)))
        top_elevation_meters = float(
            obstacle.get("topElevation") if obstacle.get("topElevation") is not None else 0.0
        )
        is_compliant = actual_distance_meters >= self.minimum_distance_meters
        return AnalysisRuleResult(
            station_id=self.protection_zone.station_id,
            station_type=self.protection_zone.station_type,
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=(
                None if obstacle.get("rawObstacleType") is None else str(obstacle["rawObstacleType"])
            ),
            global_obstacle_category=str(obstacle["globalObstacleCategory"]),
            rule_code=self.protection_zone.rule_code,
            rule_name=self.protection_zone.rule_name,
            zone_code=self.protection_zone.zone_code,
            zone_name=self.protection_zone.zone_name,
            region_code=self.protection_zone.region_code,
            region_name=self.protection_zone.region_name,
            is_applicable=True,
            is_compliant=is_compliant,
            message=(
                "obstacle outside vhf protection zone"
                if is_compliant
                else "obstacle entered vhf protection zone"
            ),
            metrics={
                "enteredProtectionZone": entered_protection_zone,
                "actualDistanceMeters": actual_distance_meters,
                "minimumDistanceMeters": self.minimum_distance_meters,
                "topElevationMeters": top_elevation_meters,
            },
            standards_rule_code=self._resolve_standards_rule_code(obstacle),
        )


def build_vhf_circle_protection_zone(
    *,
    station: object,
    rule_code: str,
    rule_name: str,
    zone_code: str,
    zone_name: str,
    station_point: tuple[float, float],
    radius_meters: float,
) -> ProtectionZoneSpec:
    local_geometry = ensure_multipolygon(
        build_circle_polygon(center_point=station_point, radius_meters=radius_meters)
    )
    return build_protection_zone_spec(
        station_id=int(station.id),
        station_type=str(station.station_type),
        rule_code=rule_code,
        rule_name=rule_name,
        zone_code=zone_code,
        zone_name=zone_name,
        region_code="default",
        region_name="default",
        local_geometry=local_geometry,
        vertical_definition={
            "mode": "flat",
            "baseReference": "station",
            "baseHeightMeters": 0.0,
        },
    )
