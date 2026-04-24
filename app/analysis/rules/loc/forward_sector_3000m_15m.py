import math

from shapely.geometry import MultiPolygon, Polygon, shape

from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import ObstacleRule
from app.analysis.rules.loc.config import LOC_FORWARD_SECTOR_3000M_15M


class LocForwardSector3000m15mRule(ObstacleRule):
    rule_name = "loc_forward_sector_3000m_15m"
    zone_name = "LOC forward sector 3000m 15m"
    SUPPORTED_CATEGORIES = {
        "building_general",
        "power_line_high_voltage_overhead",
        "building_hangar",
        "building_terminal",
    }

    # 校验障碍物是否满足 LOC 前向扇区净空要求。
    def analyze(
        self,
        *,
        station: object,
        obstacle: dict[str, object],
        station_point: tuple[float, float],
        runway_context: dict[str, object],
    ) -> AnalysisRuleResult:
        obstacle_category = str(obstacle["globalObstacleCategory"])
        base_height_meters = float(getattr(station, "altitude", 0.0) or 0.0)
        top_elevation_meters = float(obstacle.get("topElevation") or base_height_meters)
        height_limit_meters = (
            base_height_meters
            + float(LOC_FORWARD_SECTOR_3000M_15M["height_limit_offset_m"])
        )
        forward_direction_degrees = (
            float(runway_context["directionDegrees"]) + 180.0
        ) % 360.0
        protection_zone = self._build_sector(
            station_point=station_point,
            direction_degrees=forward_direction_degrees,
            radius_meters=float(LOC_FORWARD_SECTOR_3000M_15M["radius_m"]),
            half_angle_degrees=float(LOC_FORWARD_SECTOR_3000M_15M["half_angle_degrees"]),
        )
        obstacle_shape = shape(obstacle.get("localGeometry") or obstacle["geometry"])
        if not isinstance(obstacle_shape, MultiPolygon):
            obstacle_shape = MultiPolygon([obstacle_shape])
        entered_protection_zone = obstacle_shape.intersects(protection_zone)

        is_compliant = True
        message = "obstacle outside forward sector"
        if entered_protection_zone:
            is_compliant = top_elevation_meters <= height_limit_meters
            message = (
                "obstacle within forward sector and below height limit"
                if is_compliant
                else "obstacle within forward sector above height limit"
            )

        direction_degrees = forward_direction_degrees
        half_angle_degrees = float(LOC_FORWARD_SECTOR_3000M_15M["half_angle_degrees"])
        return AnalysisRuleResult(
            station_id=station.id,
            station_type=str(station.station_type),
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=obstacle["rawObstacleType"],
            global_obstacle_category=obstacle_category,
            rule_name=self.rule_name,
            zone_code=self.rule_name,
            zone_name=self.zone_name,
            region_code="default",
            region_name="default",
            zone_definition={
                "shape": "sector",
                "min_radius_m": 0.0,
                "max_radius_m": LOC_FORWARD_SECTOR_3000M_15M["radius_m"],
                "start_azimuth_deg": (direction_degrees - half_angle_degrees) % 360.0,
                "end_azimuth_deg": (direction_degrees + half_angle_degrees) % 360.0,
                "vertical_mode": "flat",
                "flat_height_m": height_limit_meters,
            },
            is_applicable=True,
            is_compliant=is_compliant,
            message=message,
            metrics={
                "enteredProtectionZone": entered_protection_zone,
                "baseHeightMeters": base_height_meters,
                "topElevationMeters": top_elevation_meters,
                "heightLimitMeters": height_limit_meters,
                "elevationAngleDegrees": 0.0,
            },
        )

    # 构建以前向轴为中心的扇形区。
    def _build_sector(
        self,
        *,
        station_point: tuple[float, float],
        direction_degrees: float,
        radius_meters: float,
        half_angle_degrees: float,
    ) -> Polygon:
        points = [station_point]
        degrees = direction_degrees - half_angle_degrees
        while degrees <= direction_degrees + half_angle_degrees:
            radians = math.radians(90.0 - degrees)
            points.append(
                (
                    station_point[0] + math.cos(radians) * radius_meters,
                    station_point[1] + math.sin(radians) * radius_meters,
                )
            )
            degrees += 1.0
        end_radians = math.radians(90.0 - (direction_degrees + half_angle_degrees))
        end_point = (
            station_point[0] + math.cos(end_radians) * radius_meters,
            station_point[1] + math.sin(end_radians) * radius_meters,
        )
        if points[-1] != end_point:
            points.append(end_point)
        points.append(station_point)
        return Polygon(points)
