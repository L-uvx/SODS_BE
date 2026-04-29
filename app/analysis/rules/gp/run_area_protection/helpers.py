import math
from dataclasses import dataclass

from shapely.geometry import MultiPolygon, Polygon

from app.analysis.rules.geometry_helpers import ensure_multipolygon
from app.analysis.rules.gp.run_area_protection.gp_run_area_table import (
    Aircraft,
    GpRunAreaTable,
    GpRunAreaTableItem,
)


@dataclass(slots=True)
class GpRunAreaProtectionSharedContext:
    station_point: tuple[float, float]
    axis_unit: tuple[float, float]
    normal_unit: tuple[float, float]
    side_sign: float
    runway_width_meters: float
    distance_v_to_runway_abs_meters: float
    back_offset_meters: float
    table_item: GpRunAreaTableItem
    station_sub_type: str
    aircraft: Aircraft
    antenna_type: str
    runway_context: dict[str, object]


@dataclass(slots=True)
class GpRunAreaProtectionRegionGeometry:
    local_geometry: MultiPolygon


# 解析 GP 运行保护区天线类型；当前缺省按 M 型处理。
def resolve_gp_run_area_antenna_type(station: object) -> str:
    raw_value = getattr(station, "antenna_type", None)
    if raw_value in {"M", "O"}:
        return str(raw_value)
    return "M"


# 构建 GP 运行保护区共享上下文。
def build_gp_run_area_shared_context(
    *,
    station: object,
    station_point: tuple[float, float],
    runway_context: dict[str, object],
) -> GpRunAreaProtectionSharedContext | None:
    station_sub_type = getattr(station, "station_sub_type", None)
    if station_sub_type not in {"I", "II", "III"}:
        return None

    maximum_airworthiness = _resolve_maximum_airworthiness(
        runway_context.get("maximumAirworthiness")
    )
    if maximum_airworthiness is None:
        return None

    aircraft = GpRunAreaTable.resolve_aircraft(maximum_airworthiness)
    if aircraft is None:
        return None

    antenna_type = resolve_gp_run_area_antenna_type(station)
    table = GpRunAreaTable()
    table_item = table.get_item(
        station_sub_type=station_sub_type,
        aircraft=aircraft,
        antenna_type=antenna_type,
    )
    if table_item is None:
        return None

    direction_degrees = float(runway_context["directionDegrees"])
    reverse_direction_radians = math.radians(direction_degrees + 180.0)
    axis_unit = (
        _normalize_axis_component(math.sin(reverse_direction_radians)),
        _normalize_axis_component(math.cos(reverse_direction_radians)),
    )
    normal_unit = (-axis_unit[1], axis_unit[0])

    distance_v_to_runway = float(getattr(station, "distance_v_to_runway", 0.0) or 0.0)
    runway_width_meters = float(runway_context["widthMeters"])
    back_offset_meters = 50.0 if aircraft in {Aircraft.H20, Aircraft.H25} else 0.0

    return GpRunAreaProtectionSharedContext(
        station_point=station_point,
        axis_unit=axis_unit,
        normal_unit=normal_unit,
        side_sign=1.0 if distance_v_to_runway >= 0.0 else -1.0,
        runway_width_meters=runway_width_meters,
        distance_v_to_runway_abs_meters=abs(distance_v_to_runway),
        back_offset_meters=back_offset_meters,
        table_item=table_item,
        station_sub_type=str(station_sub_type),
        aircraft=aircraft,
        antenna_type=antenna_type,
        runway_context=runway_context,
    )


# 构建 GP 运行保护区第 A 区几何。
def build_gp_run_area_region_a_geometry(
    shared_context: GpRunAreaProtectionSharedContext,
) -> GpRunAreaProtectionRegionGeometry:
    item = shared_context.table_item
    runway_edge_y = -(
        shared_context.distance_v_to_runway_abs_meters
        - (shared_context.runway_width_meters / 2.0)
    )
    local_points = [
        (-shared_context.back_offset_meters, item.pc_y_meters),
        (item.pc_x_meters, item.pc_y_meters),
        (item.pc_x_meters, runway_edge_y),
        (-shared_context.back_offset_meters, runway_edge_y),
    ]
    return _build_region_geometry(
        shared_context=shared_context,
        local_points=local_points,
    )


# 构建 GP 运行保护区第 B 区几何。
def build_gp_run_area_region_b_geometry(
    shared_context: GpRunAreaProtectionSharedContext,
) -> GpRunAreaProtectionRegionGeometry:
    item = shared_context.table_item
    runway_outer_edge_y = -(
        shared_context.distance_v_to_runway_abs_meters
        + (shared_context.runway_width_meters / 2.0)
    )
    local_points = [
        (-shared_context.back_offset_meters, item.ps_y_meters),
        (item.ps_x_meters, item.ps_y_meters),
        (item.ps_x_meters, runway_outer_edge_y),
        (-shared_context.back_offset_meters, runway_outer_edge_y),
    ]
    return _build_region_geometry(
        shared_context=shared_context,
        local_points=local_points,
    )


def _resolve_maximum_airworthiness(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _build_region_geometry(
    *,
    shared_context: GpRunAreaProtectionSharedContext,
    local_points: list[tuple[float, float]],
) -> GpRunAreaProtectionRegionGeometry:
    world_points = [
        project_gp_run_area_template_point(
            shared_context=shared_context,
            x_meters=x_meters,
            y_meters=y_meters,
        )
        for x_meters, y_meters in local_points
    ]
    return GpRunAreaProtectionRegionGeometry(
        local_geometry=ensure_multipolygon(Polygon([*world_points, world_points[0]]))
    )


def project_gp_run_area_template_point(
    *,
    shared_context: GpRunAreaProtectionSharedContext,
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


def _normalize_axis_component(value: float) -> float:
    if abs(value) < 1e-12:
        return 0.0
    return value


__all__ = [
    "Aircraft",
    "GpRunAreaProtectionRegionGeometry",
    "GpRunAreaProtectionSharedContext",
    "GpRunAreaTable",
    "GpRunAreaTableItem",
    "build_gp_run_area_region_a_geometry",
    "build_gp_run_area_region_b_geometry",
    "build_gp_run_area_shared_context",
    "project_gp_run_area_template_point",
    "resolve_gp_run_area_antenna_type",
]
