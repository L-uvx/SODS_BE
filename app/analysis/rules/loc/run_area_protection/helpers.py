import math
from dataclasses import dataclass

from shapely.geometry import MultiPolygon, Polygon

from app.analysis.rules.geometry_helpers import ensure_multipolygon
from app.analysis.rules.loc.run_area_protection.loc_run_area_table import (
    Aircraft,
    LocRunAreaTable,
    LocRunAreaTableItem,
)


@dataclass(slots=True)
class LocRunAreaProtectionSharedContext:
    station_point: tuple[float, float]
    runway_end_point: tuple[float, float]
    station_sub_type: str
    aircraft: Aircraft
    unit_number: int
    l_meters: float
    table_item: LocRunAreaTableItem
    runway_context: dict[str, object]
    runway_axis_unit: tuple[float, float]
    normal_unit: tuple[float, float]


@dataclass(slots=True)
class LocRunAreaProtectionRegionGeometry:
    local_geometry: MultiPolygon


# 构建 LOC 运行保护区共享上下文。
def build_loc_run_area_shared_context(
    *,
    station: object,
    station_point: tuple[float, float],
    runway_context: dict[str, object],
) -> LocRunAreaProtectionSharedContext | None:
    station_sub_type = getattr(station, "station_sub_type", None)
    if station_sub_type not in {"I", "II", "III"}:
        return None

    unit_number_text = getattr(station, "unit_number", None)
    if unit_number_text is None or not str(unit_number_text).isdigit():
        return None
    unit_number = int(str(unit_number_text))

    maximum_airworthiness = runway_context.get("maximumAirworthiness")
    resolved_maximum_airworthiness = _resolve_maximum_airworthiness(
        maximum_airworthiness
    )
    if resolved_maximum_airworthiness is None:
        return None
    aircraft = LocRunAreaTable.resolve_aircraft(resolved_maximum_airworthiness)
    if aircraft is None:
        return None

    center_x, center_y = runway_context["localCenterPoint"]
    direction_degrees = float(runway_context["directionDegrees"])
    runway_length_meters = float(runway_context["lengthMeters"])
    radians = math.radians(direction_degrees)
    runway_axis_unit = (math.sin(radians), math.cos(radians))
    runway_end_point = (
        center_x + runway_axis_unit[0] * (runway_length_meters / 2.0),
        center_y + runway_axis_unit[1] * (runway_length_meters / 2.0),
    )
    l_meters = (
        math.hypot(
            runway_end_point[0] - station_point[0],
            runway_end_point[1] - station_point[1],
        )
        + runway_length_meters
    )
    table = LocRunAreaTable(l_meters=l_meters)
    table_item = table.get_item(
        station_sub_type=station_sub_type,
        aircraft=aircraft,
        unit_number=unit_number,
    )
    if table_item is None:
        return None

    return LocRunAreaProtectionSharedContext(
        station_point=station_point,
        runway_end_point=runway_end_point,
        station_sub_type=station_sub_type,
        aircraft=aircraft,
        unit_number=unit_number,
        l_meters=l_meters,
        table_item=table_item,
        runway_context=runway_context,
        runway_axis_unit=runway_axis_unit,
        normal_unit=(-runway_axis_unit[1], runway_axis_unit[0]),
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


# 构建 LOC 运行保护区第 A 区几何。
def build_loc_run_area_region_a_geometry(
    shared_context: LocRunAreaProtectionSharedContext,
) -> LocRunAreaProtectionRegionGeometry:
    item = shared_context.table_item
    if item.zs1_meters is None or item.zs2_meters is None:
        raise ValueError("region A requires zs1/zs2 parameters")
    return _build_region_geometry(
        shared_context=shared_context,
        local_points=[
            (-item.zs2_meters, 60.0),
            (-item.zs1_meters, 60.0),
            (-item.zs1_meters, -60.0),
            (-item.zs2_meters, -60.0),
        ],
    )


# 构建 LOC 运行保护区第 B 区几何。
def build_loc_run_area_region_b_geometry(
    shared_context: LocRunAreaProtectionSharedContext,
) -> LocRunAreaProtectionRegionGeometry:
    item = shared_context.table_item
    if item.zs1_meters is None:
        raise ValueError("region B requires zs1 parameter")
    return _build_region_geometry(
        shared_context=shared_context,
        local_points=[
            (-item.zs1_meters, item.yc_meters),
            (-item.zc_meters, item.yc_meters),
            (-item.zc_meters, -item.yc_meters),
            (-item.zs1_meters, -item.yc_meters),
        ],
    )


# 构建 LOC 运行保护区第 C 区几何。
def build_loc_run_area_region_c_geometry(
    shared_context: LocRunAreaProtectionSharedContext,
) -> LocRunAreaProtectionRegionGeometry:
    item = shared_context.table_item
    return _build_region_geometry(
        shared_context=shared_context,
        local_points=[
            (-item.zc_meters, item.yc_meters),
            (item.xc_meters, item.yc_meters),
            (item.xc_meters, -item.yc_meters),
            (-item.zc_meters, -item.yc_meters),
        ],
    )


# 构建 LOC 运行保护区第 D 区几何。
def build_loc_run_area_region_d_geometry(
    shared_context: LocRunAreaProtectionSharedContext,
) -> LocRunAreaProtectionRegionGeometry:
    item = shared_context.table_item
    if item.xs_meters is None or item.y1_meters is None or item.y2_meters is None:
        raise ValueError("region D requires xs/y1/y2 parameters")

    if item.xs_meters <= 1500.0:
        local_points = [
            (-item.zc_meters, item.yc_meters),
            (item.xs_meters, item.y1_meters),
            (item.xs_meters, -item.y1_meters),
            (-item.zc_meters, -item.yc_meters),
        ]
    elif item.xs_meters <= 1800.0:
        local_points = [
            (-item.zc_meters, item.yc_meters),
            (1500.0, item.y1_meters),
            (item.xs_meters, item.y2_meters),
            (item.xs_meters, -item.y2_meters),
            (1500.0, -item.y1_meters),
            (-item.zc_meters, -item.yc_meters),
        ]
    else:
        local_points = [
            (-item.zc_meters, item.yc_meters),
            (1500.0, item.y1_meters),
            (item.xs_meters - 300.0, item.y2_meters),
            (item.xs_meters, item.y2_meters),
            (item.xs_meters, -item.y2_meters),
            (item.xs_meters - 300.0, -item.y2_meters),
            (1500.0, -item.y1_meters),
            (-item.zc_meters, -item.yc_meters),
        ]

    return _build_region_geometry(
        shared_context=shared_context,
        local_points=local_points,
    )


def _build_region_geometry(
    *,
    shared_context: LocRunAreaProtectionSharedContext,
    local_points: list[tuple[float, float]],
) -> LocRunAreaProtectionRegionGeometry:
    world_points = [
        _project_local_point(
            shared_context=shared_context,
            local_x=local_x,
            local_y=local_y,
        )
        for local_x, local_y in local_points
    ]
    return LocRunAreaProtectionRegionGeometry(
        local_geometry=ensure_multipolygon(Polygon([*world_points, world_points[0]]))
    )


def _project_local_point(
    *,
    shared_context: LocRunAreaProtectionSharedContext,
    local_x: float,
    local_y: float,
) -> tuple[float, float]:
    axis_x, axis_y = shared_context.runway_axis_unit
    normal_x, normal_y = shared_context.normal_unit
    origin_x, origin_y = shared_context.station_point
    return (
        origin_x - axis_x * local_x + normal_x * local_y,
        origin_y - axis_y * local_x + normal_y * local_y,
    )
