import math
from dataclasses import dataclass

from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

from app.analysis.protection_zone_style import resolve_protection_zone_name
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import ObstacleRule
from app.analysis.rules.geometry_evaluation import evaluate_geometry_metric
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
        else:
            distance_after_front_edge_meters = (
                _calculate_distance_after_front_edge_meters(
                    obstacle_shape=obstacle_shape,
                    protection_zone_geometry=self.protection_zone.local_geometry,
                    shared_context=self.shared_context,
                )
            )
            limit_height_meters = base_height_meters + math.tan(math.radians(1.0)) * max(
                distance_after_front_edge_meters,
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


def _calculate_distance_after_front_edge_meters(
    *,
    obstacle_shape: BaseGeometry,
    protection_zone_geometry: BaseGeometry,
    shared_context: Gp1DegSharedContext,
) -> float:
    evaluation = evaluate_geometry_metric(
        obstacle_geometry=obstacle_shape,
        protection_zone_geometry=protection_zone_geometry,
        point_metric=lambda point: _calculate_point_distance_after_front_edge_meters(
            target_point=point,
            shared_context=shared_context,
        ),
        collect_point_candidates=True,
    )
    if evaluation.min_metric is not None:
        return evaluation.min_metric

    fallback_evaluation = evaluate_geometry_metric(
        geometry=obstacle_shape,
        point_metric=lambda point: _calculate_point_distance_after_front_edge_meters(
            target_point=point,
            shared_context=shared_context,
        ),
        collect_point_candidates=True,
    )
    if fallback_evaluation.min_metric is None:
        raise ValueError("gp 1deg geometry metric evaluation returned no candidates")
    return fallback_evaluation.min_metric


def _calculate_point_distance_after_front_edge_meters(
    *,
    target_point: Point,
    shared_context: Gp1DegSharedContext,
) -> float:
    radial_distance_meters = math.hypot(
        target_point.x - shared_context.station_point[0],
        target_point.y - shared_context.station_point[1],
    )
    direction_radians = math.atan2(
        target_point.x - shared_context.station_point[0],
        target_point.y - shared_context.station_point[1],
    )
    axis_heading_radians = math.atan2(
        shared_context.axis_unit[0],
        shared_context.axis_unit[1],
    )
    angle_delta_radians = abs(direction_radians - axis_heading_radians)
    angle_delta_radians = min(
        angle_delta_radians,
        abs((2.0 * math.pi) - angle_delta_radians),
    )
    runway_project_meters = shared_context.front_offset_meters / abs(
        math.cos(angle_delta_radians)
    )
    return radial_distance_meters - runway_project_meters
__all__ = [
    "BoundGpElevationRestriction1DegRule",
    "GpElevationRestriction1DegRule",
]
