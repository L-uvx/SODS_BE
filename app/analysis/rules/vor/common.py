# app/analysis/rules/vor/common.py
from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import build_circle_polygon, ensure_multipolygon
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


class VorRule(ObstacleRule):
    # 绑定单个 VOR 台站上下文。
    def bind(self, *args, **kwargs) -> BoundObstacleRule:  # pragma: no cover
        raise NotImplementedError


# 构建 VOR 环带保护区规格。
def build_vor_ring_protection_zone(
    *,
    station_id: int,
    station_type: str,
    rule_code: str,
    rule_name: str,
    zone_code: str,
    zone_name: str,
    region_code: str,
    region_name: str,
    station_point: tuple[float, float],
    inner_radius_m: float,
    outer_radius_m: float,
    base_height_meters: float,
    slope_meters_per_meter: float,
    start_distance_meters: float,
    longitude: float | None,
    latitude: float | None,
) -> ProtectionZoneSpec:
    outer_zone = build_circle_polygon(
        center_point=station_point, radius_meters=outer_radius_m
    )
    inner_zone = build_circle_polygon(
        center_point=station_point, radius_meters=inner_radius_m
    )
    ring_zone = ensure_multipolygon(outer_zone.difference(inner_zone))
    return build_protection_zone_spec(
        station_id=station_id,
        station_type=station_type,
        rule_code=rule_code,
        rule_name=rule_name,
        zone_code=zone_code,
        zone_name=zone_name,
        region_code=region_code,
        region_name=region_name,
        local_geometry=ring_zone,
        vertical_definition={
            "mode": "analytic_surface",
            "baseReference": "station",
            "baseHeightMeters": float(base_height_meters),
            "surface": {
                "distanceSource": {
                    "kind": "point",
                    "point": [float(longitude), float(latitude)]
                    if longitude is not None and latitude is not None
                    else None,
                },
                "distanceMetric": "radial",
                "clampRange": {
                    "startMeters": float(inner_radius_m),
                    "endMeters": float(outer_radius_m),
                },
                "heightModel": {
                    "type": "linear_ramp",
                    "baseHeightMeters": float(base_height_meters),
                    "slopeMetersPerMeter": float(slope_meters_per_meter),
                    "startDistanceMeters": float(start_distance_meters),
                },
            },
        },
    )
