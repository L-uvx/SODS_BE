import math

from shapely.geometry import MultiPolygon, Point, Polygon, shape
from shapely.ops import unary_union

from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.loc.config import LOC_SITE_PROTECTION
from app.analysis.rules.base import ObstacleRule


class LocSiteProtectionRule(ObstacleRule):
    rule_name = "loc_site_protection"
    zone_name = "LOC site protection zone"

    def __init__(self, *, circle_step_degrees: float = 2.5) -> None:
        self._circle_step_degrees = float(
            circle_step_degrees or LOC_SITE_PROTECTION["circle_step_degrees"]
        )

    # 校验障碍物是否满足 LOC 场地保护区要求。
    def analyze(
        self,
        *,
        station: object,
        obstacle: dict[str, object],
        station_point: tuple[float, float],
        runway_context: dict[str, object],
    ) -> AnalysisRuleResult:
        protection_zone, rectangle_length_meters = self._build_zone_geometry(
            station_point=station_point,
            runway_context=runway_context,
        )
        obstacle_shape = shape(obstacle.get("localGeometry") or obstacle["geometry"])
        if not isinstance(obstacle_shape, MultiPolygon):
            obstacle_shape = MultiPolygon([obstacle_shape])

        entered_protection_zone = obstacle_shape.intersects(protection_zone)
        base_height_meters = float(getattr(station, "altitude", 0.0) or 0.0)
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
            station_id=station.id,
            station_type=str(station.station_type),
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=obstacle["rawObstacleType"],
            global_obstacle_category=str(obstacle["globalObstacleCategory"]),
            rule_name=self.rule_name,
            zone_code=self.rule_name,
            zone_name=self.zone_name,
            region_code="default",
            region_name="default",
            zone_definition={
                "shape": "multipolygon",
                "circle_radius_m": LOC_SITE_PROTECTION["circle_radius_m"],
                "rectangle_width_m": LOC_SITE_PROTECTION["rectangle_width_m"],
                "rectangle_length_m": rectangle_length_meters,
                "circle_step_degrees": self._circle_step_degrees,
                "coordinates": self._serialize_multipolygon(protection_zone),
            },
            is_applicable=True,
            is_compliant=is_compliant,
            message=message,
            metrics={
                "enteredProtectionZone": entered_protection_zone,
                "baseHeightMeters": base_height_meters,
                "topElevationMeters": top_elevation_meters,
                "rectangleLengthMeters": rectangle_length_meters,
            },
        )

    # 构建 LOC 场地保护区组合面与矩形长度。
    def _build_zone_geometry(
        self,
        *,
        station_point: tuple[float, float],
        runway_context: dict[str, object],
    ) -> tuple[Polygon | MultiPolygon, float]:
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
        return unary_union([circle, rectangle]), rectangle_length_meters

    # 解析矩形延伸方向与长度。
    def _resolve_axis(
        self,
        *,
        station_point: tuple[float, float],
        runway_context: dict[str, object],
    ) -> tuple[float, tuple[float, float], tuple[float, float]]:
        center_x, center_y = runway_context["localCenterPoint"]
        direction_degrees = float(runway_context["directionDegrees"])
        runway_length_meters = float(runway_context["lengthMeters"])
        radians = math.radians(direction_degrees)
        forward_unit = (math.sin(radians), math.cos(radians))
        reverse_unit = (-forward_unit[0], -forward_unit[1])
        to_center = (center_x - station_point[0], center_y - station_point[1])
        axis_unit = (
            forward_unit
            if forward_unit[0] * to_center[0] + forward_unit[1] * to_center[1] >= 0.0
            else reverse_unit
        )
        endpoints = [
            (
                center_x + forward_unit[0] * (runway_length_meters / 2.0),
                center_y + forward_unit[1] * (runway_length_meters / 2.0),
            ),
            (
                center_x + reverse_unit[0] * (runway_length_meters / 2.0),
                center_y + reverse_unit[1] * (runway_length_meters / 2.0),
            ),
        ]
        nearest_distance = min(
            max(
                0.0,
                (endpoint[0] - station_point[0]) * axis_unit[0]
                + (endpoint[1] - station_point[1]) * axis_unit[1],
            )
            for endpoint in endpoints
        )
        rectangle_length_meters = max(
            float(LOC_SITE_PROTECTION["minimum_rectangle_length_m"]),
            nearest_distance,
        )
        normal_unit = (-axis_unit[1], axis_unit[0])
        return rectangle_length_meters, axis_unit, normal_unit

    # 构建沿跑道方向延伸的矩形。
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

    # 将组合保护区序列化为 MultiPolygon 坐标列表。
    def _serialize_multipolygon(
        self, geometry: Polygon | MultiPolygon
    ) -> list[list[list[list[float]]]]:
        multipolygon = (
            geometry if isinstance(geometry, MultiPolygon) else MultiPolygon([geometry])
        )
        return [
            [
                [[float(x), float(y)] for x, y in polygon.exterior.coords],
                *[
                    [[float(x), float(y)] for x, y in ring.coords]
                    for ring in polygon.interiors
                ],
            ]
            for polygon in multipolygon.geoms
        ]
