from dataclasses import dataclass

from shapely.geometry import Point

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.result_helpers import (
    ceil2,
    compute_azimuth_degrees,
    compute_horizontal_angle_range_from_geometry,
)
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.adsb.config import (
    ADS_B_BOUNDARY_MODE_BY_CATEGORY,
    ADS_B_STANDARDS_RULE_CODE_BY_CATEGORY,
)
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import (
    build_circle_polygon,
    ensure_multipolygon,
    resolve_obstacle_shape,
)
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


class AdsbRule(ObstacleRule):
    # 绑定单个 ADS-B 台站上下文。
    def bind(self, *args, **kwargs) -> BoundObstacleRule:  # pragma: no cover
        raise NotImplementedError


@dataclass(slots=True)
class BoundAdsbCircleRule(BoundObstacleRule):
    station_point: tuple[float, float]
    minimum_distance_meters: float

    # 按障碍物分类解析 ADS-B 条文键与边界语义。
    def _resolve_category_config(self, obstacle: dict[str, object]) -> tuple[str, str]:
        category = str(obstacle["globalObstacleCategory"])
        return (
            ADS_B_BOUNDARY_MODE_BY_CATEGORY.get(category, "lte"),
            ADS_B_STANDARDS_RULE_CODE_BY_CATEGORY.get(category, self.protection_zone.rule_code),
        )

    # 执行已绑定的 ADS-B 圆形最小间距判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(self.protection_zone.local_geometry)
        actual_distance_meters = float(obstacle_shape.distance(Point(self.station_point)))
        top_elevation_meters = float(
            obstacle.get("topElevation") if obstacle.get("topElevation") is not None else 0.0
        )
        boundary_mode, standards_rule_code = self._resolve_category_config(obstacle)
        if boundary_mode == "lte":
            is_compliant = actual_distance_meters > self.minimum_distance_meters
        else:
            is_compliant = actual_distance_meters >= self.minimum_distance_meters

        obstacle_centroid = obstacle_shape.centroid
        az = compute_azimuth_degrees(
            self.station_point[0], self.station_point[1],
            obstacle_centroid.x, obstacle_centroid.y,
        )
        min_h, max_h = compute_horizontal_angle_range_from_geometry(
            self.station_point, obstacle_shape,
        )
        over_distance = (
            max(0.0, self.minimum_distance_meters - actual_distance_meters)
            if not is_compliant
            else 0.0
        )
        actual_dist = ceil2(actual_distance_meters)
        min_dist = self.minimum_distance_meters
        details_text = (
            f"不满足最小防护间距要求，实际距离{actual_dist}m，所需最小间距{min_dist}m。"
            if not is_compliant
            else f"实际距离{actual_dist}m，最小防护间距{min_dist}m。"
        )

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
            is_filter_limit=True,
            message=(
                "在平面防护间距要求内"
                if entered_protection_zone
                else "不在平面防护间距要求内"
            ),
            metrics={
                "enteredProtectionZone": entered_protection_zone,
                "actualDistanceMeters": actual_distance_meters,
                "minimumDistanceMeters": self.minimum_distance_meters,
                "topElevationMeters": top_elevation_meters,
                "boundaryMode": boundary_mode,
            },
            standards_rule_code=standards_rule_code,
            over_distance_meters=top_elevation_meters,
            azimuth_degrees=az,
            max_horizontal_angle_degrees=max_h,
            min_horizontal_angle_degrees=min_h,
            relative_height_meters=top_elevation_meters,
            is_in_radius=entered_protection_zone,
            is_in_zone=entered_protection_zone,
            details=details_text,
        )


def build_adsb_circle_protection_zone(
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
