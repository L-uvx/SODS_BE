import math
from dataclasses import dataclass

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

from app.analysis.config import PROTECTION_ZONE_BUILDER_DISCRETIZATION
from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import ensure_multipolygon, resolve_obstacle_shape
from app.analysis.rules.loc.config import LOC_SITE_PROTECTION
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


@dataclass(slots=True)
class BoundLocSiteProtectionRule(BoundObstacleRule):
    station: object
    rectangle_length_meters: float

    # 执行已绑定的 LOC 场地保护区判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(
            self.protection_zone.local_geometry
        )
        base_height_meters = float(getattr(self.station, "altitude", 0.0) or 0.0)
        top_elevation_meters = float(obstacle.get("topElevation") or base_height_meters)
        is_cable = (
            str(obstacle["globalObstacleCategory"]) == "power_or_communication_cable"
        )

        is_compliant = True
        message = "obstacle outside site protection zone"
        if entered_protection_zone:
            if is_cable:
                is_compliant = top_elevation_meters < base_height_meters
                message = (
                    "cable below station base height"
                    if is_compliant
                    else "cable enters site protection zone above station base height"
                )
            else:
                is_compliant = False
                message = "obstacle enters site protection zone"

        return AnalysisRuleResult(
            station_id=self.protection_zone.station_id,
            station_type=self.protection_zone.station_type,
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=obstacle["rawObstacleType"],
            global_obstacle_category=str(obstacle["globalObstacleCategory"]),
            rule_code=self.protection_zone.rule_code,
            rule_name=self.protection_zone.rule_name,
            zone_code=self.protection_zone.zone_code,
            zone_name=self.protection_zone.zone_name,
            region_code=self.protection_zone.region_code,
            region_name=self.protection_zone.region_name,
            is_applicable=True,
            is_compliant=is_compliant,
            message=message,
            metrics={
                "enteredProtectionZone": entered_protection_zone,
                "baseHeightMeters": base_height_meters,
                "topElevationMeters": top_elevation_meters,
                "rectangleLengthMeters": self.rectangle_length_meters,
            },
            standards_rule_code=(
                "loc_site_protection_cable"
                if is_cable
                else self.protection_zone.rule_code
            ),
        )


class LocSiteProtectionRule(ObstacleRule):
    rule_code = "loc_site_protection"
    rule_name = "loc_site_protection"
    zone_code = "loc_site_protection"
    zone_name = resolve_protection_zone_name(zone_code=zone_code)

    def __init__(self, *, circle_step_degrees: float | None = None) -> None:
        resolved_circle_step_degrees = float(
            circle_step_degrees
            if circle_step_degrees is not None
            else PROTECTION_ZONE_BUILDER_DISCRETIZATION["circle_step_degrees"]
        )
        minimum_step_degrees = float(
            PROTECTION_ZONE_BUILDER_DISCRETIZATION["minimum_step_degrees"]
        )
        maximum_step_degrees = float(
            PROTECTION_ZONE_BUILDER_DISCRETIZATION["maximum_step_degrees"]
        )
        if not (
            minimum_step_degrees
            <= resolved_circle_step_degrees
            < maximum_step_degrees
        ):
            raise ValueError(
                "circle_step_degrees must be within shared discretization bounds"
            )
        self._circle_step_degrees = resolved_circle_step_degrees

    # 绑定单个 LOC 台站的场地保护区。
    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
        runway_context: dict[str, object],
    ) -> BoundLocSiteProtectionRule:
        protection_zone, rectangle_length_meters = self._build_zone_geometry(
            station_point=station_point,
            runway_context=runway_context,
        )
        base_height_meters = float(getattr(station, "altitude", 0.0) or 0.0)
        return BoundLocSiteProtectionRule(
            protection_zone=build_protection_zone_spec(
                station_id=int(station.id),
                station_type=str(station.station_type),
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                region_code="default",
                region_name="default",
                local_geometry=ensure_multipolygon(protection_zone),
                vertical_definition={
                    "mode": "flat",
                    "baseReference": "station",
                    "baseHeightMeters": base_height_meters,
                },
            ),
            station=station,
            rectangle_length_meters=rectangle_length_meters,
        )

    # 构建 LOC 场地保护区组合面与矩形长度。
    def _build_zone_geometry(
        self,
        *,
        station_point: tuple[float, float],
        runway_context: dict[str, object],
    ) -> tuple[MultiPolygon, float]:
        rectangle_length_meters, axis_unit, normal_unit = self._resolve_axis(
            station_point=station_point,
            runway_context=runway_context,
        )
        rectangle = self._build_rectangle(
            station_point=station_point,
            axis_unit=axis_unit,
            normal_unit=normal_unit,
            length_meters=rectangle_length_meters,
            width_meters=float(LOC_SITE_PROTECTION["rectangle_width_m"]),
        )
        circle = self._build_circle(
            station_point=station_point,
            radius_meters=float(LOC_SITE_PROTECTION["circle_radius_m"]),
        )
        return ensure_multipolygon(unary_union([circle, rectangle])), rectangle_length_meters

    # 解析朝向跑道的矩形延伸方向与长度。
    def _resolve_axis(
        self,
        *,
        station_point: tuple[float, float],
        runway_context: dict[str, object],
    ) -> tuple[float, tuple[float, float], tuple[float, float]]:
        center_x, center_y = runway_context["localCenterPoint"]
        original_direction_degrees = float(runway_context["directionDegrees"])
        direction_degrees = (original_direction_degrees + 180.0) % 360.0
        runway_length_meters = float(runway_context["lengthMeters"])
        radians = math.radians(direction_degrees)
        axis_unit = (math.sin(radians), math.cos(radians))
        original_radians = math.radians(original_direction_degrees)
        original_axis_unit = (math.sin(original_radians), math.cos(original_radians))
        original_direction_end_point = (
            center_x + original_axis_unit[0] * (runway_length_meters / 2.0),
            center_y + original_axis_unit[1] * (runway_length_meters / 2.0),
        )
        projected_distance = max(
            0.0,
            (original_direction_end_point[0] - station_point[0]) * axis_unit[0]
            + (original_direction_end_point[1] - station_point[1]) * axis_unit[1],
        )
        rectangle_length_meters = max(
            float(LOC_SITE_PROTECTION["minimum_rectangle_length_m"]),
            projected_distance,
        )
        normal_unit = (-axis_unit[1], axis_unit[0])
        return rectangle_length_meters, axis_unit, normal_unit

    # 构建沿保护区轴向延伸的矩形。
    def _build_rectangle(
        self,
        *,
        station_point: tuple[float, float],
        axis_unit: tuple[float, float],
        normal_unit: tuple[float, float],
        length_meters: float,
        width_meters: float,
    ) -> Polygon:
        half_width = width_meters / 2.0
        start_left = (
            station_point[0] + normal_unit[0] * half_width,
            station_point[1] + normal_unit[1] * half_width,
        )
        start_right = (
            station_point[0] - normal_unit[0] * half_width,
            station_point[1] - normal_unit[1] * half_width,
        )
        end_left = (
            start_left[0] + axis_unit[0] * length_meters,
            start_left[1] + axis_unit[1] * length_meters,
        )
        end_right = (
            start_right[0] + axis_unit[0] * length_meters,
            start_right[1] + axis_unit[1] * length_meters,
        )
        return Polygon([start_left, end_left, end_right, start_right, start_left])

    # 构建按固定角度离散的圆形。
    def _build_circle(
        self,
        *,
        station_point: tuple[float, float],
        radius_meters: float,
    ) -> Polygon:
        points: list[tuple[float, float]] = []
        degrees = 0.0
        while degrees < 360.0:
            radians = math.radians(degrees)
            points.append(
                (
                    station_point[0] + math.cos(radians) * radius_meters,
                    station_point[1] + math.sin(radians) * radius_meters,
                )
            )
            degrees += self._circle_step_degrees
        points.append(points[0])
        return Polygon(points)
