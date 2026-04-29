from dataclasses import dataclass
from typing import Callable

from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPoint, Point, Polygon
from shapely.geometry.base import BaseGeometry


@dataclass(slots=True)
class GeometryMetricEvaluation:
    entered_geometry: BaseGeometry
    min_metric: float | None


# 计算障碍物进入保护区后的最小点位指标值。
def evaluate_geometry_metric(
    *,
    obstacle_geometry: BaseGeometry | None = None,
    protection_zone_geometry: BaseGeometry | None = None,
    geometry: BaseGeometry | None = None,
    point_metric: Callable[[Point], float],
    collect_point_candidates: bool = True,
) -> GeometryMetricEvaluation:
    if geometry is not None:
        entered_geometry = geometry
    elif obstacle_geometry is not None and protection_zone_geometry is not None:
        entered_geometry = obstacle_geometry.intersection(protection_zone_geometry)
    else:
        raise ValueError(
            "either geometry or obstacle_geometry/protection_zone_geometry must be provided"
        )
    if entered_geometry.is_empty:
        return GeometryMetricEvaluation(
            entered_geometry=entered_geometry,
            min_metric=None,
        )

    metric_candidates: list[float] = []
    if collect_point_candidates:
        metric_candidates.extend(
            point_metric(point_candidate)
            for point_candidate in _iter_point_candidates(entered_geometry)
        )
    metric_candidates.extend(
        _calculate_segment_min_metric(segment, point_metric=point_metric)
        for segment in _iter_line_segments(entered_geometry)
    )

    return GeometryMetricEvaluation(
        entered_geometry=entered_geometry,
        min_metric=min(metric_candidates) if metric_candidates else None,
    )


def _iter_line_segments(geometry: BaseGeometry) -> list[LineString]:
    if isinstance(geometry, Polygon):
        return _iter_line_segments(geometry.boundary)
    if isinstance(geometry, LineString):
        return _build_line_segments(geometry)
    if isinstance(geometry, MultiLineString):
        segments: list[LineString] = []
        for line in geometry.geoms:
            segments.extend(_build_line_segments(line))
        return segments
    if hasattr(geometry, "geoms"):
        segments: list[LineString] = []
        for child_geometry in geometry.geoms:
            segments.extend(_iter_line_segments(child_geometry))
        return segments
    return []


def _iter_point_candidates(geometry: BaseGeometry) -> list[Point]:
    if isinstance(geometry, Point):
        return [geometry]
    if isinstance(geometry, MultiPoint):
        return [point for point in geometry.geoms]
    if isinstance(geometry, (LineString, MultiLineString, Polygon)):
        return []
    if isinstance(geometry, GeometryCollection):
        points: list[Point] = []
        for child_geometry in geometry.geoms:
            points.extend(_iter_point_candidates(child_geometry))
        return points
    if hasattr(geometry, "geoms"):
        points: list[Point] = []
        for child_geometry in geometry.geoms:
            points.extend(_iter_point_candidates(child_geometry))
        return points
    return []


def _build_line_segments(line: LineString) -> list[LineString]:
    coordinates = list(line.coords)
    return [
        LineString([coordinates[index], coordinates[index + 1]])
        for index in range(len(coordinates) - 1)
    ]


def _calculate_segment_min_metric(
    segment: LineString,
    *,
    point_metric: Callable[[Point], float],
) -> float:
    start_x, start_y = segment.coords[0]
    end_x, end_y = segment.coords[-1]

    def _metric_at(t: float) -> float:
        return point_metric(
            Point(
                start_x + (end_x - start_x) * t,
                start_y + (end_y - start_y) * t,
            )
        )

    left = 0.0
    right = 1.0
    for _ in range(80):
        left_third = left + (right - left) / 3.0
        right_third = right - (right - left) / 3.0
        if _metric_at(left_third) <= _metric_at(right_third):
            right = right_third
        else:
            left = left_third

    return min(
        _metric_at(0.0),
        _metric_at(1.0),
        _metric_at((left + right) / 2.0),
    )


__all__ = ["GeometryMetricEvaluation", "evaluate_geometry_metric"]
