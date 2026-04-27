import math
from dataclasses import dataclass

from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.geometry.base import BaseGeometry

from app.analysis.config import PROTECTION_ZONE_BUILDER_DISCRETIZATION
from app.analysis.rules.geometry_helpers import ensure_multipolygon
from app.analysis.rules.loc.config import LOC_BUILDING_RESTRICTION_ZONE


@dataclass(slots=True)
class LocBuildingRestrictionZoneSharedContext:
    station_point: tuple[float, float]
    apex_point: tuple[float, float]
    root_left_point: tuple[float, float]
    root_right_point: tuple[float, float]
    station_to_apex_distance_meters: float
    arc_radius_meters: float
    arc_height_offset_meters: float
    alpha_degrees: float
    axis_unit: tuple[float, float]
    normal_unit: tuple[float, float]
    runway_axis_unit: tuple[float, float]


@dataclass(slots=True)
class LocBuildingRestrictionZoneRegion1Geometry:
    local_geometry: MultiPolygon


@dataclass(slots=True)
class LocBuildingRestrictionZoneRegion2Geometry:
    local_geometry: MultiPolygon


@dataclass(slots=True)
class LocBuildingRestrictionZoneRegion3Geometry:
    local_geometry: MultiPolygon
    arc_points: list[tuple[float, float]]


@dataclass(slots=True)
class LocBuildingRestrictionZoneRegion3AnalysisGeometry:
    apex_point: tuple[float, float]
    arc_height_offset_meters: float
    arc_points: list[tuple[float, float]]
    local_geometry: MultiPolygon


@dataclass(slots=True)
class LocBuildingRestrictionZoneRegion4Geometry:
    local_geometry: MultiPolygon
    front_left_point: tuple[float, float]
    front_right_point: tuple[float, float]
    back_left_point: tuple[float, float]
    back_right_point: tuple[float, float]


# 构建 LOC 建筑物限制区共享上下文。
def build_loc_building_restriction_zone_shared_context(
    *,
    station_point: tuple[float, float],
    runway_context: dict[str, object],
) -> LocBuildingRestrictionZoneSharedContext:
    center_x, center_y = runway_context["localCenterPoint"]
    original_direction_degrees = float(runway_context["directionDegrees"])
    runway_length_meters = float(runway_context["lengthMeters"])
    original_radians = math.radians(original_direction_degrees)
    original_axis_unit = (math.sin(original_radians), math.cos(original_radians))

    apex_point = (
        center_x - original_axis_unit[0] * (runway_length_meters / 2.0),
        center_y - original_axis_unit[1] * (runway_length_meters / 2.0),
    )
    station_to_apex_distance_meters = math.hypot(
        apex_point[0] - station_point[0],
        apex_point[1] - station_point[1],
    )
    axis_unit = _normalize_vector(
        (
            apex_point[0] - station_point[0],
            apex_point[1] - station_point[1],
        )
    )
    normal_unit = (-axis_unit[1], axis_unit[0])
    root_half_width_m = float(LOC_BUILDING_RESTRICTION_ZONE["root_half_width_m"])
    root_left_point = (
        apex_point[0] + normal_unit[0] * root_half_width_m,
        apex_point[1] + normal_unit[1] * root_half_width_m,
    )
    root_right_point = (
        apex_point[0] - normal_unit[0] * root_half_width_m,
        apex_point[1] - normal_unit[1] * root_half_width_m,
    )

    arc_radius_meters = (
        station_to_apex_distance_meters
        + float(LOC_BUILDING_RESTRICTION_ZONE["arc_radius_offset_m"])
    )
    alpha_degrees = _resolve_alpha_degrees(
        station_to_apex_distance_meters=station_to_apex_distance_meters,
        root_half_width_m=root_half_width_m,
    )
    return LocBuildingRestrictionZoneSharedContext(
        station_point=station_point,
        apex_point=apex_point,
        root_left_point=root_left_point,
        root_right_point=root_right_point,
        station_to_apex_distance_meters=station_to_apex_distance_meters,
        arc_radius_meters=arc_radius_meters,
        arc_height_offset_meters=float(
            LOC_BUILDING_RESTRICTION_ZONE["arc_height_offset_m"]
        ),
        alpha_degrees=alpha_degrees,
        axis_unit=axis_unit,
        normal_unit=normal_unit,
        runway_axis_unit=original_axis_unit,
    )


# 构建 LOC 建筑物限制区第 1 区几何。
def build_loc_building_restriction_zone_region_1_geometry(
    shared_context: LocBuildingRestrictionZoneSharedContext,
) -> LocBuildingRestrictionZoneRegion1Geometry:
    trapezoid_points = _build_region_1_2_trapezoid_points(
        shared_context=shared_context,
        side_sign=1.0,
    )
    return LocBuildingRestrictionZoneRegion1Geometry(
        local_geometry=ensure_multipolygon(
            Polygon([*trapezoid_points, trapezoid_points[0]])
        )
    )


# 构建 LOC 建筑物限制区第 2 区几何。
def build_loc_building_restriction_zone_region_2_geometry(
    shared_context: LocBuildingRestrictionZoneSharedContext,
) -> LocBuildingRestrictionZoneRegion2Geometry:
    trapezoid_points = _build_region_1_2_trapezoid_points(
        shared_context=shared_context,
        side_sign=-1.0,
    )
    return LocBuildingRestrictionZoneRegion2Geometry(
        local_geometry=ensure_multipolygon(
            Polygon([*trapezoid_points, trapezoid_points[0]])
        )
    )


# 构建 LOC 建筑物限制区第 3 区几何。
def build_loc_building_restriction_zone_region_3_geometry(
    shared_context: LocBuildingRestrictionZoneSharedContext,
) -> LocBuildingRestrictionZoneRegion3Geometry:
    arc_points = _build_arc_points(
        station_point=shared_context.station_point,
        axis_unit=shared_context.axis_unit,
        radius_meters=shared_context.arc_radius_meters,
        alpha_degrees=shared_context.alpha_degrees,
    )
    return LocBuildingRestrictionZoneRegion3Geometry(
        local_geometry=ensure_multipolygon(
            Polygon(
                [
                    shared_context.root_left_point,
                    *arc_points,
                    shared_context.root_right_point,
                    shared_context.root_left_point,
                ]
            )
        ),
        arc_points=arc_points,
    )


# 构建 LOC 建筑物限制区第 4 区几何。
def build_loc_building_restriction_zone_region_4_geometry(
    shared_context: LocBuildingRestrictionZoneSharedContext,
) -> LocBuildingRestrictionZoneRegion4Geometry:
    reverse_axis_unit = (
        -shared_context.runway_axis_unit[0],
        -shared_context.runway_axis_unit[1],
    )
    region_4_side_offset_m = float(
        LOC_BUILDING_RESTRICTION_ZONE["region_4_side_offset_m"]
    )
    region_4_backward_length_m = float(
        LOC_BUILDING_RESTRICTION_ZONE["region_4_backward_length_m"]
    )
    region_4_normal_unit = (-reverse_axis_unit[1], reverse_axis_unit[0])
    region_4_back_center_point = (
        shared_context.station_point[0]
        - reverse_axis_unit[0] * region_4_backward_length_m,
        shared_context.station_point[1]
        - reverse_axis_unit[1] * region_4_backward_length_m,
    )
    region_4_back_left_point = (
        region_4_back_center_point[0] + region_4_normal_unit[0] * region_4_side_offset_m,
        region_4_back_center_point[1] + region_4_normal_unit[1] * region_4_side_offset_m,
    )
    region_4_back_right_point = (
        region_4_back_center_point[0] - region_4_normal_unit[0] * region_4_side_offset_m,
        region_4_back_center_point[1] - region_4_normal_unit[1] * region_4_side_offset_m,
    )
    region_4_front_center_point = (
        shared_context.station_point[0]
        + reverse_axis_unit[0] * shared_context.station_to_apex_distance_meters,
        shared_context.station_point[1]
        + reverse_axis_unit[1] * shared_context.station_to_apex_distance_meters,
    )
    region_4_front_left_point = (
        region_4_front_center_point[0]
        + region_4_normal_unit[0] * region_4_side_offset_m,
        region_4_front_center_point[1]
        + region_4_normal_unit[1] * region_4_side_offset_m,
    )
    region_4_front_right_point = (
        region_4_front_center_point[0]
        - region_4_normal_unit[0] * region_4_side_offset_m,
        region_4_front_center_point[1]
        - region_4_normal_unit[1] * region_4_side_offset_m,
    )
    return LocBuildingRestrictionZoneRegion4Geometry(
        local_geometry=ensure_multipolygon(
            Polygon(
                [
                    region_4_front_left_point,
                    region_4_back_left_point,
                    region_4_back_right_point,
                    region_4_front_right_point,
                    region_4_front_left_point,
                ]
            )
        ),
        front_left_point=region_4_front_left_point,
        front_right_point=region_4_front_right_point,
        back_left_point=region_4_back_left_point,
        back_right_point=region_4_back_right_point,
    )

# 计算区域 3 的最不利允许高度。
def calculate_region_3_worst_allowed_height_meters(
    *,
    zone_geometry: LocBuildingRestrictionZoneRegion3AnalysisGeometry,
    obstacle_geometry: MultiPolygon,
    station_altitude_meters: float,
) -> float | None:
    intersection = obstacle_geometry.intersection(zone_geometry.local_geometry)
    if intersection.is_empty:
        return None

    apex_point = zone_geometry.apex_point
    candidate_points: list[tuple[float, float]] = []
    candidate_points.extend(_collect_geometry_candidate_points(intersection, apex_point))

    allowed_heights = [
        station_altitude_meters
        + zone_geometry.arc_height_offset_meters
        * min(
            math.hypot(point[0] - apex_point[0], point[1] - apex_point[1])
            / max(
                math.hypot(
                    arc_point[0] - apex_point[0],
                    arc_point[1] - apex_point[1],
                )
                for arc_point in zone_geometry.arc_points
            ),
            1.0,
        )
        for point in candidate_points
    ]
    if not allowed_heights:
        return None
    return min(allowed_heights)


def _collect_geometry_candidate_points(
    geometry: BaseGeometry,
    apex_point: tuple[float, float],
) -> list[tuple[float, float]]:
    if geometry.is_empty:
        return []
    if isinstance(geometry, Polygon):
        return _collect_polygon_candidate_points(geometry, apex_point)
    if isinstance(geometry, MultiPolygon):
        candidate_points: list[tuple[float, float]] = []
        for polygon in geometry.geoms:
            candidate_points.extend(_collect_polygon_candidate_points(polygon, apex_point))
        return candidate_points
    if isinstance(geometry, LineString):
        return _collect_line_candidate_points(geometry, apex_point)
    if isinstance(geometry, MultiLineString):
        candidate_points = []
        for line in geometry.geoms:
            candidate_points.extend(_collect_line_candidate_points(line, apex_point))
        return candidate_points
    if isinstance(geometry, Point):
        return [(float(geometry.x), float(geometry.y))]
    if isinstance(geometry, MultiPoint):
        return [(float(point.x), float(point.y)) for point in geometry.geoms]
    if isinstance(geometry, GeometryCollection):
        candidate_points = []
        for part in geometry.geoms:
            candidate_points.extend(_collect_geometry_candidate_points(part, apex_point))
        return candidate_points
    return []


def _collect_polygon_candidate_points(
    polygon: Polygon,
    apex_point: tuple[float, float],
) -> list[tuple[float, float]]:
    candidate_points: list[tuple[float, float]] = []
    candidate_points.extend(_collect_ring_candidate_points(polygon.exterior, apex_point))
    for ring in polygon.interiors:
        candidate_points.extend(_collect_ring_candidate_points(ring, apex_point))
    return candidate_points


def _collect_line_candidate_points(
    line: LineString,
    apex_point: tuple[float, float],
) -> list[tuple[float, float]]:
    coordinates = [(float(x), float(y)) for x, y in line.coords]
    return _collect_segment_projection_candidate_points(
        coordinates=coordinates,
        apex_point=apex_point,
        closed=False,
    )


def _collect_ring_candidate_points(
    ring: LineString,
    apex_point: tuple[float, float],
) -> list[tuple[float, float]]:
    coordinates = [(float(x), float(y)) for x, y in ring.coords[:-1]]
    return _collect_segment_projection_candidate_points(
        coordinates=coordinates,
        apex_point=apex_point,
        closed=True,
    )


def _collect_segment_projection_candidate_points(
    *,
    coordinates: list[tuple[float, float]],
    apex_point: tuple[float, float],
    closed: bool,
) -> list[tuple[float, float]]:
    candidate_points = list(coordinates)
    if len(coordinates) < 2:
        return candidate_points

    apex = Point(apex_point)
    end_coordinates = coordinates[1:] + coordinates[:1] if closed else coordinates[1:]
    for start_point, end_point in zip(coordinates, end_coordinates):
        segment = LineString([start_point, end_point])
        projected_distance = segment.project(apex)
        projected_point = segment.interpolate(projected_distance)
        if projected_point.intersects(segment):
            candidate_points.append(
                (float(projected_point.x), float(projected_point.y))
            )
    return candidate_points


def _resolve_alpha_degrees(
    *,
    station_to_apex_distance_meters: float,
    root_half_width_m: float,
) -> float:
    base_angle_radians = math.radians(
        float(LOC_BUILDING_RESTRICTION_ZONE["base_angle_degrees"])
    )
    arc_radius_meters = (
        station_to_apex_distance_meters
        + float(LOC_BUILDING_RESTRICTION_ZONE["arc_radius_offset_m"])
    )
    ratio = (
        station_to_apex_distance_meters * math.sin(base_angle_radians)
        - root_half_width_m * math.cos(base_angle_radians)
    ) / arc_radius_meters
    ratio = max(-1.0, min(1.0, ratio))
    return math.degrees(base_angle_radians - math.asin(ratio))


def _build_arc_points(
    *,
    station_point: tuple[float, float],
    axis_unit: tuple[float, float],
    radius_meters: float,
    alpha_degrees: float,
) -> list[tuple[float, float]]:
    step_degrees = float(PROTECTION_ZONE_BUILDER_DISCRETIZATION["sector_step_degrees"])
    axis_angle = math.atan2(axis_unit[1], axis_unit[0])
    start_angle = axis_angle + math.radians(alpha_degrees)
    end_angle = axis_angle - math.radians(alpha_degrees)
    points: list[tuple[float, float]] = []
    degrees = alpha_degrees
    while degrees > -alpha_degrees:
        angle = axis_angle + math.radians(degrees)
        points.append(
            (
                station_point[0] + math.cos(angle) * radius_meters,
                station_point[1] + math.sin(angle) * radius_meters,
            )
        )
        degrees -= step_degrees
    end_point = (
        station_point[0] + math.cos(end_angle) * radius_meters,
        station_point[1] + math.sin(end_angle) * radius_meters,
    )
    if not points or points[-1] != end_point:
        points.append(end_point)
    if points[0] != (
        station_point[0] + math.cos(start_angle) * radius_meters,
        station_point[1] + math.sin(start_angle) * radius_meters,
    ):
        points.insert(
            0,
            (
                station_point[0] + math.cos(start_angle) * radius_meters,
                station_point[1] + math.sin(start_angle) * radius_meters,
            ),
        )
    return points


def _build_region_1_2_trapezoid_points(
    *,
    shared_context: LocBuildingRestrictionZoneSharedContext,
    side_sign: float,
) -> list[tuple[float, float]]:
    forward_axis_unit = shared_context.runway_axis_unit
    reverse_axis_unit = (-forward_axis_unit[0], -forward_axis_unit[1])
    outward_normal_unit = (
        shared_context.normal_unit[0] * side_sign,
        shared_context.normal_unit[1] * side_sign,
    )
    forward_length_m = float(
        LOC_BUILDING_RESTRICTION_ZONE["region_1_2_forward_length_m"]
    )
    outer_offset_m = float(LOC_BUILDING_RESTRICTION_ZONE["region_1_2_outer_offset_m"])
    side_angle_degrees = float(
        LOC_BUILDING_RESTRICTION_ZONE["region_1_2_side_angle_degrees"]
    )

    root_point = (
        shared_context.root_left_point
        if side_sign > 0.0
        else shared_context.root_right_point
    )
    forward_end_point = _offset_point(
        shared_context.station_point,
        along_vector=forward_axis_unit,
        along_distance_m=forward_length_m,
    )
    point_2 = _offset_point(
        forward_end_point,
        along_vector=outward_normal_unit,
        along_distance_m=float(LOC_BUILDING_RESTRICTION_ZONE["root_half_width_m"]),
    )
    point_3 = _offset_point(
        forward_end_point,
        along_vector=outward_normal_unit,
        along_distance_m=outer_offset_m,
    )
    lateral_delta_m = outer_offset_m - float(
        LOC_BUILDING_RESTRICTION_ZONE["root_half_width_m"]
    )
    reverse_distance_m = lateral_delta_m / math.tan(math.radians(side_angle_degrees))
    point_4 = _offset_point(
        _offset_point(
            root_point,
            along_vector=outward_normal_unit,
            along_distance_m=lateral_delta_m,
        ),
        along_vector=reverse_axis_unit,
        along_distance_m=reverse_distance_m,
    )
    return [root_point, point_2, point_3, point_4]


def _offset_point(
    point: tuple[float, float],
    *,
    along_vector: tuple[float, float],
    along_distance_m: float,
) -> tuple[float, float]:
    return (
        point[0] + along_vector[0] * along_distance_m,
        point[1] + along_vector[1] * along_distance_m,
    )


def _normalize_vector(vector: tuple[float, float]) -> tuple[float, float]:
    magnitude = math.hypot(vector[0], vector[1])
    if magnitude == 0.0:
        raise ValueError("cannot normalize zero-length vector")
    return (vector[0] / magnitude, vector[1] / magnitude)
