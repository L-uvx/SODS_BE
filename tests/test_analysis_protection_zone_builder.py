import math
from unittest.mock import patch

import pytest

from app.analysis.config import PROTECTION_ZONE_BUILDER_DISCRETIZATION
from app.analysis.local_coordinate import AirportLocalProjector
from app.analysis.protection_zone_builder import (
    build_protection_zone_geometry,
    build_protection_zone_vertical,
)


def test_build_protection_zone_geometry_builds_circle_as_multipolygon() -> None:
    projector = AirportLocalProjector(
        reference_longitude=104.123456,
        reference_latitude=30.123456,
    )

    geometry = build_protection_zone_geometry(
        projector=projector,
        center_point=(0.0, 0.0),
        zone_definition={"shape": "circle", "radius_m": 50.0},
    )

    assert geometry["shapeType"] == "multipolygon"
    assert len(geometry["coordinates"]) == 1
    assert len(geometry["coordinates"][0]) == 1
    assert len(geometry["coordinates"][0][0]) > 8
    first_point = geometry["coordinates"][0][0][0]
    assert abs(first_point[0] - 104.123456) > 0.0
    assert abs(first_point[1] - 30.123456) < 0.001


def test_build_protection_zone_geometry_builds_circle_using_configured_angle_step() -> None:
    projector = AirportLocalProjector(
        reference_longitude=104.123456,
        reference_latitude=30.123456,
    )

    with patch.dict(
        PROTECTION_ZONE_BUILDER_DISCRETIZATION,
        {"circle_step_degrees": 10.0},
        clear=False,
    ):
        geometry = build_protection_zone_geometry(
            projector=projector,
            center_point=(0.0, 0.0),
            zone_definition={"shape": "circle", "radius_m": 50.0},
        )

    assert len(geometry["coordinates"][0][0]) == 37


def test_build_protection_zone_geometry_builds_circle_using_non_divisor_angle_step() -> None:
    projector = AirportLocalProjector(
        reference_longitude=104.123456,
        reference_latitude=30.123456,
    )

    with patch.dict(
        PROTECTION_ZONE_BUILDER_DISCRETIZATION,
        {"circle_step_degrees": 7.0},
        clear=False,
    ):
        geometry = build_protection_zone_geometry(
            projector=projector,
            center_point=(0.0, 0.0),
            zone_definition={"shape": "circle", "radius_m": 50.0},
        )

    assert len(geometry["coordinates"][0][0]) == 53


def test_build_protection_zone_geometry_builds_radial_band_as_multipolygon_with_hole() -> None:
    projector = AirportLocalProjector(
        reference_longitude=104.123456,
        reference_latitude=30.123456,
    )

    geometry = build_protection_zone_geometry(
        projector=projector,
        center_point=(0.0, 0.0),
        zone_definition={
            "shape": "radial_band",
            "min_radius_m": 50.0,
            "max_radius_m": 37040.0,
        },
    )

    assert geometry["shapeType"] == "multipolygon"
    assert len(geometry["coordinates"]) == 1
    assert len(geometry["coordinates"][0]) == 2
    assert len(geometry["coordinates"][0][0]) > 8
    assert len(geometry["coordinates"][0][1]) > 8


def test_build_protection_zone_geometry_builds_radial_band_using_configured_circle_step() -> None:
    projector = AirportLocalProjector(
        reference_longitude=104.123456,
        reference_latitude=30.123456,
    )

    with patch.dict(
        PROTECTION_ZONE_BUILDER_DISCRETIZATION,
        {"circle_step_degrees": 10.0},
        clear=False,
    ):
        geometry = build_protection_zone_geometry(
            projector=projector,
            center_point=(0.0, 0.0),
            zone_definition={
                "shape": "radial_band",
                "min_radius_m": 50.0,
                "max_radius_m": 37040.0,
            },
        )

    assert len(geometry["coordinates"][0][0]) == 37
    assert len(geometry["coordinates"][0][1]) == 37


def test_build_protection_zone_vertical_builds_radial_band_analytic_surface() -> None:
    vertical = build_protection_zone_vertical(
        shape="radial_band",
        zone_definition={
            "min_radius_m": 50.0,
            "max_radius_m": 37040.0,
        },
        distance_source_point=(104.123, 30.456),
        base_height_meters=500.0,
        elevation_angle_degrees=3.0,
    )

    assert vertical == {
        "mode": "analytic_surface",
        "baseReference": "station",
        "baseHeightMeters": 500.0,
        "surface": {
            "type": "distance_parameterized",
            "distanceSource": {
                "kind": "point",
                "point": [104.123, 30.456],
            },
            "distanceMetric": "radial",
            "clampRange": {
                "startMeters": 50.0,
                "endMeters": 37040.0,
            },
            "heightModel": {
                "type": "angle_linear_rise",
                "angleDegrees": 3.0,
                "distanceOffsetMeters": 50.0,
            },
        },
    }


def test_build_protection_zone_vertical_builds_sector_analytic_surface() -> None:
    vertical = build_protection_zone_vertical(
        shape="sector",
        zone_definition={
            "min_radius_m": 50.0,
            "max_radius_m": 300.0,
        },
        base_height_meters=500.0,
        elevation_angle_degrees=3.0,
    )

    assert vertical == {
        "mode": "analytic_surface",
        "baseReference": "station",
        "baseHeightMeters": 500.0,
        "heightFunction": {
            "type": "elevation_angle",
            "elevationAngleDegrees": 3.0,
            "distanceMetric": "radial",
            "startDistanceMeters": 50.0,
            "endDistanceMeters": 300.0,
        },
    }


def test_build_protection_zone_vertical_builds_sector_flat_height_limit() -> None:
    vertical = build_protection_zone_vertical(
        shape="sector",
        zone_definition={
            "min_radius_m": 0.0,
            "max_radius_m": 3000.0,
            "vertical_mode": "flat",
            "flat_height_m": 515.0,
        },
        base_height_meters=500.0,
    )

    assert vertical == {
        "mode": "flat",
        "baseReference": "station",
        "baseHeightMeters": 515.0,
    }


def test_build_protection_zone_geometry_builds_sector_as_multipolygon_with_hole() -> None:
    projector = AirportLocalProjector(
        reference_longitude=104.123456,
        reference_latitude=30.123456,
    )

    geometry = build_protection_zone_geometry(
        projector=projector,
        center_point=(0.0, 0.0),
        zone_definition={
            "shape": "sector",
            "min_radius_m": 50.0,
            "max_radius_m": 300.0,
            "start_azimuth_deg": 30.0,
            "end_azimuth_deg": 120.0,
        },
    )

    assert geometry["shapeType"] == "multipolygon"
    assert len(geometry["coordinates"]) == 1
    assert len(geometry["coordinates"][0]) == 1

    ring = geometry["coordinates"][0][0]
    assert len(ring) > 8
    assert ring[0] == ring[-1]

    projected_ring = [projector.project_point(point[0], point[1]) for point in ring[:-1]]
    distances = [
        math.hypot(point[0], point[1])
        for point in projected_ring
    ]
    assert min(distances) < 60.0
    assert max(distances) > 290.0


def test_build_protection_zone_geometry_builds_sector_using_configured_angle_step() -> None:
    projector = AirportLocalProjector(
        reference_longitude=104.123456,
        reference_latitude=30.123456,
    )

    with patch.dict(
        PROTECTION_ZONE_BUILDER_DISCRETIZATION,
        {"sector_step_degrees": 10.0},
        clear=False,
    ):
        geometry = build_protection_zone_geometry(
            projector=projector,
            center_point=(0.0, 0.0),
            zone_definition={
                "shape": "sector",
                "min_radius_m": 50.0,
                "max_radius_m": 300.0,
                "start_azimuth_deg": 30.0,
                "end_azimuth_deg": 60.0,
            },
        )

    assert len(geometry["coordinates"][0][0]) == 9


def test_build_protection_zone_geometry_rejects_near_zero_circle_step() -> None:
    projector = AirportLocalProjector(
        reference_longitude=104.123456,
        reference_latitude=30.123456,
    )

    with patch.dict(
        PROTECTION_ZONE_BUILDER_DISCRETIZATION,
        {"circle_step_degrees": 1e-9},
        clear=False,
    ):
        with pytest.raises(ValueError, match="must be between"):
            build_protection_zone_geometry(
                projector=projector,
                center_point=(0.0, 0.0),
                zone_definition={"shape": "circle", "radius_m": 50.0},
            )


def test_build_protection_zone_geometry_rejects_too_large_circle_step() -> None:
    projector = AirportLocalProjector(
        reference_longitude=104.123456,
        reference_latitude=30.123456,
    )

    with patch.dict(
        PROTECTION_ZONE_BUILDER_DISCRETIZATION,
        {"circle_step_degrees": 181.0},
        clear=False,
    ):
        with pytest.raises(ValueError, match="must be between"):
            build_protection_zone_geometry(
                projector=projector,
                center_point=(0.0, 0.0),
                zone_definition={"shape": "circle", "radius_m": 50.0},
            )


def test_build_protection_zone_geometry_rejects_too_large_sector_step() -> None:
    projector = AirportLocalProjector(
        reference_longitude=104.123456,
        reference_latitude=30.123456,
    )

    with patch.dict(
        PROTECTION_ZONE_BUILDER_DISCRETIZATION,
        {"sector_step_degrees": 181.0},
        clear=False,
    ):
        with pytest.raises(ValueError, match="must be between"):
            build_protection_zone_geometry(
                projector=projector,
                center_point=(0.0, 0.0),
                zone_definition={
                    "shape": "sector",
                    "min_radius_m": 50.0,
                    "max_radius_m": 300.0,
                    "start_azimuth_deg": 30.0,
                    "end_azimuth_deg": 60.0,
                },
            )


def test_build_protection_zone_geometry_unprojects_multipolygon_coordinates() -> None:
    projector = AirportLocalProjector(
        reference_longitude=104.123456,
        reference_latitude=30.123456,
    )

    geometry = build_protection_zone_geometry(
        projector=projector,
        center_point=(0.0, 0.0),
        zone_definition={
            "shape": "multipolygon",
            "coordinates": [
                [
                    [
                        [0.0, 0.0],
                        [100.0, 0.0],
                        [100.0, 100.0],
                        [0.0, 100.0],
                        [0.0, 0.0],
                    ]
                ]
            ],
        },
    )

    assert geometry["shapeType"] == "multipolygon"
    assert len(geometry["coordinates"]) == 1
    assert len(geometry["coordinates"][0]) == 1
    first_point = geometry["coordinates"][0][0][0]
    last_point = geometry["coordinates"][0][0][-1]
    assert abs(first_point[0] - 104.123456) < 1e-9
    assert abs(first_point[1] - 30.123456) < 1e-9
    assert abs(last_point[0] - 104.123456) < 1e-9
    assert abs(last_point[1] - 30.123456) < 1e-9
    assert geometry["coordinates"][0][0][1][0] > 104.123456
    assert geometry["coordinates"][0][0][2][1] > 30.123456
