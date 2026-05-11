from dataclasses import dataclass

from shapely.geometry import Point

from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.result_helpers import (
    compute_azimuth_degrees,
    compute_horizontal_angle_range_from_geometry,
)
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.vor.common import VorRule, _float_or_none
from app.analysis.rules.vor.elevation_angle._shared import (
    BoundVorElevationAngleRule,
    bind_elevation_angle_rule,
)


_DELEGATED_500M_CATEGORIES = frozenset({
    "power_line_high_voltage_110kv",
    "power_line_high_voltage_220kv",
    "power_line_high_voltage_330kv",
    "power_line_high_voltage_500kv_and_above",
})


@dataclass(slots=True)
class BoundVor300Outside2_5_Rule(BoundVorElevationAngleRule):
    # 执行 300m 外 2.5° 仰角区判定，并处理基准面规则委托口径。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        shape = resolve_obstacle_shape(obstacle)
        min_distance = float(shape.distance(Point(self.station_point)))
        category = str(obstacle["globalObstacleCategory"])

        raw_top = obstacle.get("topElevation")
        top_elevation = float(raw_top if raw_top is not None else 0.0)

        obstacle_centroid = shape.centroid
        az = compute_azimuth_degrees(
            self.station_point[0], self.station_point[1],
            obstacle_centroid.x, obstacle_centroid.y,
        )
        min_h, max_h = compute_horizontal_angle_range_from_geometry(
            self.station_point, shape,
        )

        if min_distance < 300.0:
            return AnalysisRuleResult(
                station_id=self.protection_zone.station_id,
                station_type=self.protection_zone.station_type,
                obstacle_id=int(obstacle["obstacleId"]),
                obstacle_name=str(obstacle["name"]),
                raw_obstacle_type=obstacle["rawObstacleType"],
                global_obstacle_category=category,
                rule_code=self.protection_zone.rule_code,
                rule_name=self.protection_zone.rule_name,
                zone_code=self.protection_zone.zone_code,
                zone_name=self.protection_zone.zone_name,
                region_code=self.protection_zone.region_code,
                region_name=self.protection_zone.region_name,
                is_applicable=False,
                is_compliant=True,
                message="obstacle delegated to 300m datum plane",
                metrics={
                    "enteredProtectionZone": False,
                    "actualDistanceMeters": min_distance,
                    "topElevationMeters": top_elevation,
                    "minDistanceMeters": min_distance,
                    "delegatedRule": "vor_300m_datum_plane",
                },
                standards_rule_code=self.protection_zone.rule_code,
                over_distance_meters=0.0,
                azimuth_degrees=az,
                max_horizontal_angle_degrees=max_h,
                min_horizontal_angle_degrees=min_h,
                relative_height_meters=0.0,
                is_in_radius=False,
                is_in_zone=False,
                details="该障碍物已委托给300m基准面处理。",
            )

        if category in _DELEGATED_500M_CATEGORIES and min_distance <= 500.0:
            return AnalysisRuleResult(
                station_id=self.protection_zone.station_id,
                station_type=self.protection_zone.station_type,
                obstacle_id=int(obstacle["obstacleId"]),
                obstacle_name=str(obstacle["name"]),
                raw_obstacle_type=obstacle["rawObstacleType"],
                global_obstacle_category=category,
                rule_code=self.protection_zone.rule_code,
                rule_name=self.protection_zone.rule_name,
                zone_code=self.protection_zone.zone_code,
                zone_name=self.protection_zone.zone_name,
                region_code=self.protection_zone.region_code,
                region_name=self.protection_zone.region_name,
                is_applicable=False,
                is_compliant=True,
                message="obstacle delegated to 500m datum plane",
                metrics={
                    "enteredProtectionZone": False,
                    "actualDistanceMeters": min_distance,
                    "topElevationMeters": top_elevation,
                    "minDistanceMeters": min_distance,
                    "delegatedRule": "vor_500m_datum_plane",
                },
                standards_rule_code=self.protection_zone.rule_code,
                over_distance_meters=0.0,
                azimuth_degrees=az,
                max_horizontal_angle_degrees=max_h,
                min_horizontal_angle_degrees=min_h,
                relative_height_meters=0.0,
                is_in_radius=False,
                is_in_zone=False,
                details="该障碍物已委托给500m基准面处理。",
            )

        return BoundVorElevationAngleRule.analyze(self, obstacle)


class Vor300Outside2_5_Rule(VorRule):
    zone_code = "vor_300_outside_2_5_deg"
    zone_name = resolve_protection_zone_name(zone_code=zone_code)
    rule_code = "vor_300_outside_2_5_deg"
    rule_name = "vor_300_outside_2_5_deg"
    region_code = "default"
    region_name = "default"

    def bind(self, *, station, station_point):
        coverage_radius = _float_or_none(station.coverage_radius)
        outer_radius_m = max(coverage_radius if coverage_radius is not None else 2000.0, 300.0)
        return bind_elevation_angle_rule(
            station=station,
            station_point=station_point,
            rule_code=self.rule_code,
            rule_name=self.rule_name,
            zone_code=self.zone_code,
            zone_name=self.zone_name,
            region_code=self.region_code,
            region_name=self.region_name,
            inner_radius_m=300.0,
            outer_radius_m=outer_radius_m,
            limit_angle_degrees=2.5,
            horizontal_angle_limit_degrees=None,
            bound_rule_cls=BoundVor300Outside2_5_Rule,
        )
