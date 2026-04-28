import math
from dataclasses import dataclass

from shapely.geometry import MultiPolygon, Polygon

from app.analysis.rules.geometry_helpers import ensure_multipolygon
from app.analysis.rules.gp.config import (
    GP_SITE_PROTECTION_COMMON,
    GP_SITE_PROTECTION_STANDARD_CONFIG,
)


@dataclass(slots=True)
class GpSiteProtectionParameters:
    standard_version: str
    zone_code: str
    zone_name: str
    region_b_split_y_meters: float
    region_b_forward_length_meters: float
    region_c_split_y_meters: float
    region_c_forward_length_meters: float


@dataclass(slots=True)
class GpSiteProtectionSharedContext:
    station_point: tuple[float, float]
    axis_unit: tuple[float, float]
    normal_unit: tuple[float, float]
    side_sign: float
    edge_offset_v_meters: float
    parameters: GpSiteProtectionParameters


@dataclass(slots=True)
class GpSiteProtectionRegionGeometry:
    local_geometry: MultiPolygon


# 解析 GP 天线类型；当前缺省按 M 型处理。
def resolve_gp_antenna_type(station: object) -> str:
    # GP antenna_type 当前不落库；若 station 对象未携带该属性，则默认按 M 型处理。
    raw_value = getattr(station, "antenna_type", None)
    if raw_value in {"M", "O", "B"}:
        return str(raw_value)
    return "M"


# 解析 GP 有效天线高度。
def resolve_gp_effective_antenna_height_meters(station: object) -> float | None:
    antenna_height = getattr(station, "antenna_height", None)
    antenna_hag = getattr(station, "antenna_hag", None)
    values = [float(value) for value in (antenna_height, antenna_hag) if value is not None]
    if not values:
        return None
    return max(values)


# 解析 GP 场地保护区参数。
def resolve_gp_site_protection_parameters(
    *,
    standard_version: str,
) -> GpSiteProtectionParameters:
    config = GP_SITE_PROTECTION_STANDARD_CONFIG[standard_version]

    if standard_version == "GB":
        region_b_forward_length_meters = 900.0
        region_c_forward_length_meters = 900.0
    else:
        region_b_forward_length_meters = 600.0
        region_c_forward_length_meters = 600.0

    return GpSiteProtectionParameters(
        standard_version=standard_version,
        zone_code=str(config["zone_code"]),
        zone_name=str(config["zone_name"]),
        region_b_split_y_meters=360.0,
        region_b_forward_length_meters=region_b_forward_length_meters,
        region_c_split_y_meters=360.0,
        region_c_forward_length_meters=region_c_forward_length_meters,
    )


# 构建 GP 场地保护区共享上下文。
def build_gp_site_protection_shared_context(
    *,
    station: object,
    station_point: tuple[float, float],
    runway_context: dict[str, object],
    standard_version: str,
) -> GpSiteProtectionSharedContext:
    direction_degrees = float(runway_context["directionDegrees"])
    reverse_direction_radians = math.radians(direction_degrees + 180.0)
    axis_unit = (
        _normalize_axis_component(math.sin(reverse_direction_radians)),
        _normalize_axis_component(math.cos(reverse_direction_radians)),
    )
    normal_unit = (-axis_unit[1], axis_unit[0])

    distance_v_to_runway = float(getattr(station, "distance_v_to_runway", 0.0) or 0.0)
    runway_width_meters = float(runway_context["widthMeters"])
    side_sign = 1.0 if distance_v_to_runway >= 0.0 else -1.0
    edge_offset_v_meters = abs(distance_v_to_runway) - (runway_width_meters / 2.0)
    parameters = resolve_gp_site_protection_parameters(
        standard_version=standard_version,
    )

    return GpSiteProtectionSharedContext(
        station_point=station_point,
        axis_unit=axis_unit,
        normal_unit=normal_unit,
        side_sign=side_sign,
        edge_offset_v_meters=edge_offset_v_meters,
        parameters=parameters,
    )


def project_gp_template_point(
    shared_context: GpSiteProtectionSharedContext,
    x_meters: float,
    y_meters: float,
) -> tuple[float, float]:
    return (
        shared_context.station_point[0]
        + x_meters * shared_context.axis_unit[0]
        + y_meters * shared_context.side_sign * shared_context.normal_unit[0],
        shared_context.station_point[1]
        + x_meters * shared_context.axis_unit[1]
        + y_meters * shared_context.side_sign * shared_context.normal_unit[1],
    )


def build_gp_site_protection_region_a_geometry(
    shared_context: GpSiteProtectionSharedContext,
) -> GpSiteProtectionRegionGeometry:
    width_w = float(GP_SITE_PROTECTION_COMMON["region_a_w_m"])
    width_u = float(GP_SITE_PROTECTION_COMMON["region_a_u_m"])
    split_y = 360.0
    edge_offset_v = shared_context.edge_offset_v_meters
    points = [
        project_gp_template_point(shared_context, 0.0, width_w),
        project_gp_template_point(shared_context, split_y, width_u),
        project_gp_template_point(shared_context, split_y, -edge_offset_v),
        project_gp_template_point(shared_context, 0.0, -edge_offset_v),
    ]
    return GpSiteProtectionRegionGeometry(
        local_geometry=ensure_multipolygon(Polygon([*points, points[0]]))
    )


def build_gp_site_protection_region_b_geometry(
    shared_context: GpSiteProtectionSharedContext,
) -> GpSiteProtectionRegionGeometry:
    width_u = float(GP_SITE_PROTECTION_COMMON["region_a_u_m"])
    split_y = shared_context.parameters.region_b_split_y_meters
    forward_length = shared_context.parameters.region_b_forward_length_meters
    edge_offset_v = shared_context.edge_offset_v_meters
    points = [
        project_gp_template_point(shared_context, split_y, width_u),
        project_gp_template_point(shared_context, forward_length, width_u),
        project_gp_template_point(shared_context, forward_length, -edge_offset_v),
        project_gp_template_point(shared_context, split_y, -edge_offset_v),
    ]
    return GpSiteProtectionRegionGeometry(
        local_geometry=ensure_multipolygon(Polygon([*points, points[0]]))
    )


def build_gp_site_protection_region_c_geometry(
    shared_context: GpSiteProtectionSharedContext,
) -> GpSiteProtectionRegionGeometry:
    width_w = float(GP_SITE_PROTECTION_COMMON["region_a_w_m"])
    width_u = float(GP_SITE_PROTECTION_COMMON["region_a_u_m"])
    width_x = float(GP_SITE_PROTECTION_COMMON["region_c_x_m"])
    split_y = shared_context.parameters.region_c_split_y_meters
    forward_length = shared_context.parameters.region_c_forward_length_meters
    points = [
        project_gp_template_point(shared_context, 0.0, width_x),
        project_gp_template_point(shared_context, forward_length, width_x),
        project_gp_template_point(shared_context, forward_length, width_u),
        project_gp_template_point(shared_context, split_y, width_u),
        project_gp_template_point(shared_context, 0.0, width_w),
    ]
    return GpSiteProtectionRegionGeometry(
        local_geometry=ensure_multipolygon(Polygon([*points, points[0]]))
    )


def _normalize_axis_component(value: float) -> float:
    if abs(value) < 1e-12:
        return 0.0
    return value


__all__ = [
    "GpSiteProtectionParameters",
    "GpSiteProtectionRegionGeometry",
    "GpSiteProtectionSharedContext",
    "build_gp_site_protection_region_a_geometry",
    "build_gp_site_protection_region_b_geometry",
    "build_gp_site_protection_region_c_geometry",
    "build_gp_site_protection_shared_context",
    "project_gp_template_point",
    "resolve_gp_antenna_type",
    "resolve_gp_effective_antenna_height_meters",
    "resolve_gp_site_protection_parameters",
]
