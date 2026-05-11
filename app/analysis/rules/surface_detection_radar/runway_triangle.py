from dataclasses import dataclass

from shapely.geometry import Point

from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.result_helpers import (
    compute_azimuth_degrees,
    compute_horizontal_angle_range_from_geometry,
)
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec

from .triangle_utils import build_runway_triangle_geometry


@dataclass(slots=True)
class BoundSurfaceDetectionRadarRunwayTriangleRule(BoundObstacleRule):
    runway: dict[str, object]
    station_point: tuple[float, float]
    base_height_meters: float

    # 执行已绑定的跑道三角区判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(self.protection_zone.local_geometry)
        actual_distance_meters = float(obstacle_shape.distance(Point(self.station_point)))
        top_elevation_meters = float(
            obstacle.get("topElevation") if obstacle.get("topElevation") is not None else 0.0
        )

        centroid = obstacle_shape.centroid
        azimuth_degrees = compute_azimuth_degrees(
            self.station_point[0], self.station_point[1], centroid.x, centroid.y
        )
        min_horizontal_angle_degrees, max_horizontal_angle_degrees = (
            compute_horizontal_angle_range_from_geometry(self.station_point, obstacle_shape)
        )
        relative_height_meters = top_elevation_meters - self.base_height_meters
        is_in_runway_triangle = entered_protection_zone
        runway_number = str(self.runway["runNumber"])

        return AnalysisRuleResult(
            station_id=self.protection_zone.station_id,
            station_type=self.protection_zone.station_type,
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=(
                None
                if obstacle.get("rawObstacleType") is None
                else str(obstacle["rawObstacleType"])
            ),
            global_obstacle_category=str(obstacle["globalObstacleCategory"]),
            rule_code=self.protection_zone.rule_code,
            rule_name=self.protection_zone.rule_name,
            zone_code=self.protection_zone.zone_code,
            zone_name=self.protection_zone.zone_name,
            region_code=self.protection_zone.region_code,
            region_name=self.protection_zone.region_name,
            is_applicable=True,
            is_compliant=not entered_protection_zone,
            message=(
                f"障碍物不位于场监雷达与{runway_number}号跑道之间"
                if not is_in_runway_triangle
                else f"障碍物位于场监雷达与{runway_number}号跑道之间"
            ),
            metrics={
                "enteredProtectionZone": entered_protection_zone,
                "isInRunwayTriangle": entered_protection_zone,
                "actualDistanceMeters": actual_distance_meters,
                "runwayNumber": str(self.runway["runNumber"]),
                "runwayLengthMeters": float(self.runway["lengthMeters"]),
                "runwayDirectionDegrees": float(self.runway["directionDegrees"]),
                "topElevationMeters": top_elevation_meters,
            },
            standards_rule_code=None,
            over_distance_meters=top_elevation_meters,
            azimuth_degrees=azimuth_degrees,
            max_horizontal_angle_degrees=max_horizontal_angle_degrees,
            min_horizontal_angle_degrees=min_horizontal_angle_degrees,
            relative_height_meters=relative_height_meters,
            is_in_radius=entered_protection_zone,
            is_in_zone=entered_protection_zone,
            details=(
                "障碍物进入跑道三角区。"
                if entered_protection_zone
                else "障碍物位于保护区外。"
            ),
        )


class SurfaceDetectionRadarRunwayTriangleRule(ObstacleRule):
    rule_code = "surface_detection_radar_runway_triangle"
    rule_name = "surface_detection_radar_runway_triangle"
    zone_code = "surface_detection_radar_runway_triangle"
    standards_rule_code = None

    def __init__(self) -> None:
        self.zone_name = resolve_protection_zone_name(zone_code=self.zone_code)

    # 绑定单个场面监视雷达跑道三角区。
    def bind(
        self,
        *,
        station: object,
        station_point: tuple[float, float],
        runway: dict[str, object],
    ) -> BoundSurfaceDetectionRadarRunwayTriangleRule | None:
        return BoundSurfaceDetectionRadarRunwayTriangleRule(
            protection_zone=build_protection_zone_spec(
                station_id=int(station.id),
                station_type=str(station.station_type),
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                region_code="default",
                region_name="default",
                local_geometry=build_runway_triangle_geometry(
                    station_point=station_point,
                    runway=runway,
                ),
                vertical_definition={
                    "mode": "flat",
                    "baseReference": "station",
                    "baseHeightMeters": 0.0,
                },
            ),
            runway=runway,
            station_point=station_point,
            base_height_meters=float(getattr(station, "altitude", 0.0) or 0.0),
        )
