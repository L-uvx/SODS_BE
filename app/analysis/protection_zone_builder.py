import math

from app.analysis.config import PROTECTION_ZONE_BUILDER_DISCRETIZATION
from app.analysis.local_coordinate import AirportLocalProjector



# 构建保护区平面几何输出。
def build_protection_zone_geometry(
    *,
    projector: AirportLocalProjector,
    center_point: tuple[float, float],
    zone_definition: dict[str, object],
) -> dict[str, object] | None:
    shape = zone_definition.get("shape")

    if shape == "circle":
        radius_meters = zone_definition.get("radius_m")
        if radius_meters is None:
            return None
        return {
            "shapeType": "multipolygon",
            "coordinates": [
                [
                    _build_ring(
                        projector=projector,
                        center_point=center_point,
                        radius_meters=float(radius_meters),
                    )
                ]
            ],
        }

    if shape == "radial_band":
        min_radius_meters = zone_definition.get("min_radius_m")
        max_radius_meters = zone_definition.get("max_radius_m")
        if min_radius_meters is None or max_radius_meters is None:
            return None
        return {
            "shapeType": "multipolygon",
            "coordinates": [
                [
                    _build_ring(
                        projector=projector,
                        center_point=center_point,
                        radius_meters=float(max_radius_meters),
                    ),
                    _build_ring(
                        projector=projector,
                        center_point=center_point,
                        radius_meters=float(min_radius_meters),
                        reverse=True,
                    ),
                ]
            ],
        }

    if shape == "sector":
        min_radius_meters = zone_definition.get("min_radius_m")
        max_radius_meters = zone_definition.get("max_radius_m")
        start_azimuth_degrees = zone_definition.get("start_azimuth_deg")
        end_azimuth_degrees = zone_definition.get("end_azimuth_deg")
        if (
            min_radius_meters is None
            or max_radius_meters is None
            or start_azimuth_degrees is None
            or end_azimuth_degrees is None
        ):
            return None
        return {
            "shapeType": "multipolygon",
            "coordinates": [
                [
                    _build_annular_sector_ring(
                        projector=projector,
                        center_point=center_point,
                        inner_radius_meters=float(min_radius_meters),
                        outer_radius_meters=float(max_radius_meters),
                        start_azimuth_degrees=float(start_azimuth_degrees),
                        end_azimuth_degrees=float(end_azimuth_degrees),
                    )
                ]
            ],
        }

    if shape == "multipolygon":
        coordinates = zone_definition.get("coordinates")
        if coordinates is None:
            return None
        return {
            "shapeType": "multipolygon",
            "coordinates": _unproject_multipolygon_coordinates(
                projector=projector,
                coordinates=coordinates,
            ),
        }

    return None


# 构建保护区垂向输出。
def build_protection_zone_vertical(
    *,
    shape: str | None,
    zone_definition: dict[str, object],
    distance_source_point: tuple[float, float] | None = None,
    base_height_meters: float,
    elevation_angle_degrees: float | None = None,
) -> dict[str, object] | None:
    if shape == "radial_band":
        min_radius_meters = zone_definition.get("min_radius_m")
        max_radius_meters = zone_definition.get("max_radius_m")
        if (
            min_radius_meters is None
            or max_radius_meters is None
            or elevation_angle_degrees is None
            or distance_source_point is None
        ):
            return None
        return {
            "mode": "analytic_surface",
            "baseReference": "station",
            "baseHeightMeters": float(base_height_meters),
            "surface": {
                "type": "distance_parameterized",
                "distanceSource": {
                    "kind": "point",
                    "point": [
                        float(distance_source_point[0]),
                        float(distance_source_point[1]),
                    ],
                },
                "distanceMetric": "radial",
                "clampRange": {
                    "startMeters": float(min_radius_meters),
                    "endMeters": float(max_radius_meters),
                },
                "heightModel": {
                    "type": "angle_linear_rise",
                    "angleDegrees": float(elevation_angle_degrees),
                    "distanceOffsetMeters": float(min_radius_meters),
                },
            },
        }

    if shape in {"circle", "multipolygon"}:
        return {
            "mode": "flat",
            "baseReference": "station",
            "baseHeightMeters": float(base_height_meters),
        }

    return None


def _build_ring(
    *,
    projector: AirportLocalProjector,
    center_point: tuple[float, float],
    radius_meters: float,
    reverse: bool = False,
) -> list[list[float]]:
    center_x, center_y = center_point
    ring = []
    circle_step_degrees = _get_circle_step_degrees()
    segment_count = _build_circle_segment_count(circle_step_degrees)
    for index in range(segment_count):
        angle = math.radians(circle_step_degrees * index)
        local_x = center_x + radius_meters * math.cos(angle)
        local_y = center_y + radius_meters * math.sin(angle)
        longitude, latitude = projector.unproject_point(local_x, local_y)
        ring.append([float(longitude), float(latitude)])

    ring.append(ring[0])
    if reverse:
        return list(reversed(ring))
    return ring


def _build_annular_sector_ring(
    *,
    projector: AirportLocalProjector,
    center_point: tuple[float, float],
    inner_radius_meters: float,
    outer_radius_meters: float,
    start_azimuth_degrees: float,
    end_azimuth_degrees: float,
) -> list[list[float]]:
    outer_points = _build_sector_arc_points(
        projector=projector,
        center_point=center_point,
        radius_meters=outer_radius_meters,
        start_azimuth_degrees=start_azimuth_degrees,
        end_azimuth_degrees=end_azimuth_degrees,
    )
    inner_points = _build_sector_arc_points(
        projector=projector,
        center_point=center_point,
        radius_meters=inner_radius_meters,
        start_azimuth_degrees=start_azimuth_degrees,
        end_azimuth_degrees=end_azimuth_degrees,
    )
    ring = [*outer_points, *reversed(inner_points)]
    ring.append(ring[0])
    return ring


def _build_sector_arc_points(
    *,
    projector: AirportLocalProjector,
    center_point: tuple[float, float],
    radius_meters: float,
    start_azimuth_degrees: float,
    end_azimuth_degrees: float,
) -> list[list[float]]:
    center_x, center_y = center_point
    points = []
    for angle_radians in _build_sector_angles(
        start_azimuth_degrees=start_azimuth_degrees,
        end_azimuth_degrees=end_azimuth_degrees,
    ):
        local_x = center_x + radius_meters * math.sin(angle_radians)
        local_y = center_y + radius_meters * math.cos(angle_radians)
        longitude, latitude = projector.unproject_point(local_x, local_y)
        points.append([float(longitude), float(latitude)])
    return points


def _build_sector_angles(
    *, start_azimuth_degrees: float, end_azimuth_degrees: float
) -> list[float]:
    start_angle = math.radians(start_azimuth_degrees)
    end_angle = math.radians(end_azimuth_degrees)
    if end_angle < start_angle:
        end_angle += 2.0 * math.pi

    sector_step_radians = math.radians(_get_sector_step_degrees())
    angles = [start_angle]
    current_angle = start_angle
    while current_angle + sector_step_radians < end_angle:
        current_angle += sector_step_radians
        angles.append(current_angle)
    angles.append(end_angle)
    return angles


def _build_circle_segment_count(step_degrees: float) -> int:
    return max(3, math.ceil(360.0 / step_degrees))


def _get_circle_step_degrees() -> float:
    return _get_positive_step_degrees(
        PROTECTION_ZONE_BUILDER_DISCRETIZATION["circle_step_degrees"]
    )


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


def _unproject_multipolygon_coordinates(
    *,
    projector: AirportLocalProjector,
    coordinates: object,
) -> list[list[list[list[float]]]]:
    return [
        [
            [
                [float(longitude), float(latitude)]
                for longitude, latitude in (
                    projector.unproject_point(float(point[0]), float(point[1]))
                    for point in ring
                )
            ]
            for ring in polygon
        ]
        for polygon in coordinates
    ]
