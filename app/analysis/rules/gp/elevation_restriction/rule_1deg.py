import math
from dataclasses import dataclass

from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import ObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.gp.elevation_restriction.common import (
    BoundGpElevationRestrictionRule,
)
from app.analysis.rules.gp.elevation_restriction.helpers import (
    Gp1DegSharedContext,
    build_gp_1deg_zone_geometry,
)
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


@dataclass(slots=True)
class BoundGpElevationRestriction1DegRule(BoundGpElevationRestrictionRule):
    shared_context: Gp1DegSharedContext
    base_height_meters: float

    # 执行 GP 1 度仰角限制区真实判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(
            self.protection_zone.local_geometry
        )
        base_height_meters = self.base_height_meters
        top_elevation_meters = float(obstacle.get("topElevation") or base_height_meters)
        limit_height_meters = base_height_meters

        if not entered_protection_zone:
            is_compliant = True
            message = "obstacle outside GP 1 degree elevation restriction zone"
            obstacle_metrics = None
        else:
            obstacle_metrics = _calculate_gp_1deg_obstacle_metrics(
                obstacle_shape=obstacle_shape,
                shared_context=self.shared_context,
            )
            limit_height_meters = base_height_meters + math.tan(math.radians(1.0)) * max(
                obstacle_metrics.effective_forward_distance_meters,
                0.0,
            )
            is_compliant = top_elevation_meters <= limit_height_meters
            message = (
                "obstacle within GP 1 degree elevation limit"
                if is_compliant
                else "obstacle exceeds GP 1 degree elevation limit"
            )

        return self.build_result(
            obstacle=obstacle,
            is_compliant=is_compliant,
            message=message,
            metrics={
                "enteredProtectionZone": entered_protection_zone,
                "limitHeightMeters": limit_height_meters,
                "topElevationMeters": top_elevation_meters,
                "actualDistanceMeters": (
                    None
                    if obstacle_metrics is None
                    else obstacle_metrics.actual_distance_meters
                ),
                "centerDirectionDegrees": (
                    None
                    if obstacle_metrics is None
                    else obstacle_metrics.center_direction_degrees
                ),
                "effectiveForwardDistanceMeters": (
                    None
                    if obstacle_metrics is None
                    else obstacle_metrics.effective_forward_distance_meters
                ),
            },
        )


class GpElevationRestriction1DegRule(ObstacleRule):
    rule_code = "gp_elevation_restriction_1deg"
    rule_name = "gp_elevation_restriction_1deg"
    zone_code = "gp_elevation_restriction_1deg"
    zone_name = resolve_protection_zone_name(zone_code=zone_code)

    # 绑定 GP 1 度仰角限制区。
    def bind(
        self,
        *,
        station: object,
        shared_context: Gp1DegSharedContext,
    ) -> BoundGpElevationRestriction1DegRule:
        zone_geometry = build_gp_1deg_zone_geometry(shared_context)
        base_height_meters = shared_context.reference_height_meters
        return BoundGpElevationRestriction1DegRule(
            protection_zone=build_protection_zone_spec(
                station_id=int(station.id),
                station_type=str(station.station_type),
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                region_code="default",
                region_name="default",
                local_geometry=zone_geometry.local_geometry,
                vertical_definition={
                    "mode": "analytic_surface",
                    "baseReference": "gp360_altitude",
                    "baseHeightMeters": base_height_meters,
                    "surface": {
                        "distanceSource": {
                            "kind": "front_reference_line",
                            "frontLeftPoint": [
                                shared_context.front_left_point[0],
                                shared_context.front_left_point[1],
                            ],
                            "frontRightPoint": [
                                shared_context.front_right_point[0],
                                shared_context.front_right_point[1],
                            ],
                        },
                        "distanceMetric": "forward_offset",
                        "clampRange": {
                            "startMeters": 0.0,
                            "endMeters": shared_context.radius_meters
                            - shared_context.front_offset_meters,
                        },
                        "heightModel": {
                            "type": "angle_linear_rise",
                            "angleDegrees": 1.0,
                            "distanceOffsetMeters": 0.0,
                        },
                    },
                },
            ),
            standards_rule_code=self.rule_code,
            shared_context=shared_context,
            base_height_meters=base_height_meters,
        )


@dataclass(slots=True)
class Gp1DegObstacleMetrics:
    actual_distance_meters: float
    center_direction_degrees: float
    effective_forward_distance_meters: float


def _calculate_gp_1deg_obstacle_metrics(
    *,
    obstacle_shape: BaseGeometry,
    shared_context: Gp1DegSharedContext,
) -> Gp1DegObstacleMetrics:
    station_point = Point(shared_context.station_point)
    min_x, min_y, max_x, max_y = obstacle_shape.bounds
    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    actual_distance_meters = obstacle_shape.distance(station_point)
    center_direction_radians = math.atan2(
        center_x - shared_context.station_point[0],
        center_y - shared_context.station_point[1],
    )
    center_direction_degrees = math.degrees(center_direction_radians)
    axis_heading_radians = math.atan2(
        shared_context.axis_unit[0],
        shared_context.axis_unit[1],
    )
    angle_delta_radians = abs(center_direction_radians - axis_heading_radians)
    angle_delta_radians = min(
        angle_delta_radians,
        abs((2.0 * math.pi) - angle_delta_radians),
    )
    cosine_value = abs(math.cos(angle_delta_radians))
    runway_project_meters = (
        math.inf
        if cosine_value <= 1e-12
        else shared_context.front_offset_meters / cosine_value
    )
    return Gp1DegObstacleMetrics(
        actual_distance_meters=actual_distance_meters,
        center_direction_degrees=center_direction_degrees,
        effective_forward_distance_meters=max(
            actual_distance_meters - runway_project_meters,
            0.0,
        ),
    )


__all__ = [
    "BoundGpElevationRestriction1DegRule",
    "GpElevationRestriction1DegRule",
]
