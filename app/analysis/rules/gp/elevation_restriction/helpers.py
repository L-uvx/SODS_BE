import math
from dataclasses import dataclass

from shapely.geometry import MultiPolygon, Polygon

from app.analysis.config import PROTECTION_ZONE_BUILDER_DISCRETIZATION
from app.analysis.rules.geometry_helpers import ensure_multipolygon


@dataclass(slots=True)
class Gp1DegSharedContext:
    station_point: tuple[float, float]
    axis_unit: tuple[float, float]
    normal_unit: tuple[float, float]
    side_sign: float
    runway_context: dict[str, object]
    reference_height_meters: float
    front_offset_meters: float
    half_angle_degrees: float
    arc_half_angle_degrees: float
    radius_meters: float
    front_left_point: tuple[float, float]
    front_center_point: tuple[float, float]
    front_right_point: tuple[float, float]


@dataclass(slots=True)
class Gp1DegZoneGeometry:
    local_geometry: MultiPolygon


# 解析 GP 1 度仰角限制区的基准高程。
def resolve_gp_1deg_reference_height_meters(station: object) -> float:
    raw_value = getattr(station, "gp360_altitude", None)
    if raw_value is None:
        raw_value = getattr(station, "GP360Altitude", None)
    if raw_value is not None:
        value = float(raw_value)
        if math.isfinite(value) and value > 0.0:
            return value
    return float(getattr(station, "altitude", 0.0) or 0.0)


# 构建 GP 1 度仰角限制区共享上下文。
def build_gp_1deg_shared_context(
    *,
    station: object,
    station_point: tuple[float, float],
    runway_context: dict[str, object],
) -> Gp1DegSharedContext:
    direction_degrees = float(runway_context["directionDegrees"])
    reverse_direction_radians = math.radians(direction_degrees + 180.0)
    axis_unit = (
        _normalize_axis_component(math.sin(reverse_direction_radians)),
        _normalize_axis_component(math.cos(reverse_direction_radians)),
    )
    normal_unit = (-axis_unit[1], axis_unit[0])
    side_sign = 1.0 if float(getattr(station, "distance_v_to_runway", 0.0) or 0.0) >= 0 else -1.0

    front_offset_meters = 360.0
    half_angle_degrees = 8.0
    radius_meters = 18520.0
    arc_half_angle_degrees = math.degrees(
        math.atan(
            (radius_meters * math.sin(math.radians(half_angle_degrees)))
            / (
                radius_meters * math.cos(math.radians(half_angle_degrees))
                - front_offset_meters
            )
        )
    )
    front_half_width_meters = math.tan(math.radians(half_angle_degrees)) * front_offset_meters

    front_center_point = _project_local_point(
        station_point=station_point,
        axis_unit=axis_unit,
        normal_unit=normal_unit,
        side_sign=side_sign,
        x_meters=front_offset_meters,
        y_meters=0.0,
    )
    front_left_point = _project_local_point(
        station_point=station_point,
        axis_unit=axis_unit,
        normal_unit=normal_unit,
        side_sign=side_sign,
        x_meters=front_offset_meters,
        y_meters=front_half_width_meters,
    )
    front_right_point = _project_local_point(
        station_point=station_point,
        axis_unit=axis_unit,
        normal_unit=normal_unit,
        side_sign=side_sign,
        x_meters=front_offset_meters,
        y_meters=-front_half_width_meters,
    )

    return Gp1DegSharedContext(
        station_point=station_point,
        axis_unit=axis_unit,
        normal_unit=normal_unit,
        side_sign=side_sign,
        runway_context=runway_context,
        reference_height_meters=resolve_gp_1deg_reference_height_meters(station),
        front_offset_meters=front_offset_meters,
        half_angle_degrees=half_angle_degrees,
        arc_half_angle_degrees=arc_half_angle_degrees,
        radius_meters=radius_meters,
        front_left_point=front_left_point,
        front_center_point=front_center_point,
        front_right_point=front_right_point,
    )


# 构建 GP 1 度仰角限制区 D 区平面几何。
def build_gp_1deg_zone_geometry(
    shared_context: Gp1DegSharedContext,
) -> Gp1DegZoneGeometry:
    outer_arc_points = [
        _project_arc_point(shared_context, angle_degrees)
        for angle_degrees in _build_arc_angles(shared_context.arc_half_angle_degrees)
    ]
    ring = [
        shared_context.front_left_point,
        *outer_arc_points,
        shared_context.front_right_point,
        shared_context.front_left_point,
    ]
    return Gp1DegZoneGeometry(
        local_geometry=ensure_multipolygon(Polygon(ring))
    )


def _build_arc_angles(half_angle_degrees: float) -> list[float]:
    step_degrees = _get_sector_step_degrees()
    angle_degrees = half_angle_degrees
    angles = [angle_degrees]
    while angle_degrees - step_degrees > -half_angle_degrees:
        angle_degrees -= step_degrees
        angles.append(angle_degrees)
    if angles[-1] != -half_angle_degrees:
        angles.append(-half_angle_degrees)
    return angles


def _get_sector_step_degrees() -> float:
    return _get_positive_step_degrees(
        PROTECTION_ZONE_BUILDER_DISCRETIZATION["sector_step_degrees"]
    )


def _get_positive_step_degrees(value: object) -> float:
    step_degrees = float(value)
    minimum_step_degrees = float(
        PROTECTION_ZONE_BUILDER_DISCRETIZATION["minimum_step_degrees"]
    )
    maximum_step_degrees = float(
        PROTECTION_ZONE_BUILDER_DISCRETIZATION["maximum_step_degrees"]
    )
    if not minimum_step_degrees < maximum_step_degrees:
        raise ValueError("protection zone discretization bounds are invalid")
    if (
        step_degrees < minimum_step_degrees
        or step_degrees >= maximum_step_degrees
    ):
        raise ValueError(
            "protection zone discretization step must be between "
            f"{minimum_step_degrees} and {maximum_step_degrees} degrees"
        )
    return step_degrees


def _project_arc_point(
    shared_context: Gp1DegSharedContext,
    angle_degrees: float,
) -> tuple[float, float]:
    angle_radians = math.radians(angle_degrees)
    axis_component = math.cos(angle_radians) * shared_context.radius_meters
    normal_component = math.sin(angle_radians) * shared_context.radius_meters
    return _project_local_point(
        station_point=shared_context.station_point,
        axis_unit=shared_context.axis_unit,
        normal_unit=shared_context.normal_unit,
        side_sign=shared_context.side_sign,
        x_meters=axis_component,
        y_meters=normal_component,
    )


def _project_local_point(
    *,
    station_point: tuple[float, float],
    axis_unit: tuple[float, float],
    normal_unit: tuple[float, float],
    side_sign: float,
    x_meters: float,
    y_meters: float,
) -> tuple[float, float]:
    return (
        station_point[0] + x_meters * axis_unit[0] + y_meters * side_sign * normal_unit[0],
        station_point[1] + x_meters * axis_unit[1] + y_meters * side_sign * normal_unit[1],
    )


def _normalize_axis_component(value: float) -> float:
    if abs(value) < 1e-12:
        return 0.0
    return value


__all__ = [
    "Gp1DegSharedContext",
    "Gp1DegZoneGeometry",
    "build_gp_1deg_shared_context",
    "build_gp_1deg_zone_geometry",
    "resolve_gp_1deg_reference_height_meters",
]
