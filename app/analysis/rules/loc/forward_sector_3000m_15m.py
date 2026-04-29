import math
from dataclasses import dataclass

from shapely.geometry import Polygon

from app.analysis.config import PROTECTION_ZONE_BUILDER_DISCRETIZATION
from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.loc.config import LOC_FORWARD_SECTOR_3000M_15M
from app.analysis.rules.geometry_helpers import ensure_multipolygon, resolve_obstacle_shape
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


@dataclass(slots=True)
class BoundLocForwardSector3000m15mRule(BoundObstacleRule):
    station: object
    height_limit_meters: float

    # 执行已绑定的 LOC 前向扇区判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_category = str(obstacle["globalObstacleCategory"])
        base_height_meters = float(getattr(self.station, "altitude", 0.0) or 0.0)
        top_elevation_meters = float(obstacle.get("topElevation") or base_height_meters)
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(
            self.protection_zone.local_geometry
        )

        is_compliant = True
        message = "obstacle outside forward sector"
        if entered_protection_zone:
            is_compliant = top_elevation_meters <= self.height_limit_meters
            message = (
                "obstacle within forward sector and below height limit"
                if is_compliant
                else "obstacle within forward sector above height limit"
            )

        return AnalysisRuleResult(
            station_id=self.protection_zone.station_id,
            station_type=self.protection_zone.station_type,
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=obstacle["rawObstacleType"],
            global_obstacle_category=obstacle_category,
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
                "heightLimitMeters": self.height_limit_meters,
                "elevationAngleDegrees": 0.0,
            },
            standards_rule_code=self.protection_zone.rule_code,
        )


class LocForwardSector3000m15mRule(ObstacleRule):
    rule_code = "loc_forward_sector_3000m_15m"
    rule_name = "loc_forward_sector_3000m_15m"
    zone_code = "loc_forward_sector_3000m_15m"
    zone_name = resolve_protection_zone_name(zone_code=zone_code)
    SUPPORTED_CATEGORIES = {
        "building_general",
        "power_line_high_voltage_overhead",
        "building_hangar",
        "building_terminal",
    }

    def __init__(self) -> None:
        resolved_sector_step_degrees = float(
            PROTECTION_ZONE_BUILDER_DISCRETIZATION["sector_step_degrees"]
        )
        minimum_step_degrees = float(
            PROTECTION_ZONE_BUILDER_DISCRETIZATION["minimum_step_degrees"]
        )
        maximum_step_degrees = float(
            PROTECTION_ZONE_BUILDER_DISCRETIZATION["maximum_step_degrees"]
        )
        if not (
            minimum_step_degrees
            <= resolved_sector_step_degrees
            < maximum_step_degrees
        ):
            raise ValueError(
                "sector_step_degrees must be within shared discretization bounds"
            )
        self._sector_step_degrees = resolved_sector_step_degrees

    # 校验障碍物是否适用前向扇区规则。
    def is_applicable(self, obstacle: dict[str, object]) -> bool:
        return str(obstacle["globalObstacleCategory"]) in self.SUPPORTED_CATEGORIES

    # 绑定单个 LOC 台站的前向扇区保护区。
    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
        runway_context: dict[str, object],
    ) -> BoundLocForwardSector3000m15mRule:
        base_height_meters = float(getattr(station, "altitude", 0.0) or 0.0)
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
        return BoundLocForwardSector3000m15mRule(
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
                    "baseHeightMeters": height_limit_meters,
                },
            ),
            station=station,
            height_limit_meters=height_limit_meters,
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
            degrees += self._sector_step_degrees
        end_radians = math.radians(90.0 - (direction_degrees + half_angle_degrees))
        end_point = (
            station_point[0] + math.cos(end_radians) * radius_meters,
            station_point[1] + math.sin(end_radians) * radius_meters,
        )
        if points[-1] != end_point:
            points.append(end_point)
        points.append(station_point)
        return Polygon(points)
