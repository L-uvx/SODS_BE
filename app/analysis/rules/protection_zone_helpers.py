from shapely.geometry import MultiPolygon, Polygon

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rules.geometry_helpers import (
    ensure_multipolygon,
    ensure_polygonal_geometry,
)


# 构建规则侧 multipolygon 几何定义。
def build_geometry_definition(geometry: Polygon | MultiPolygon) -> dict[str, object]:
    multipolygon = ensure_multipolygon(ensure_polygonal_geometry(geometry))
    return {
        "shapeType": "multipolygon",
        "coordinates": [
            [
                [[float(x), float(y)] for x, y in polygon.exterior.coords],
                *[
                    [[float(x), float(y)] for x, y in ring.coords]
                    for ring in polygon.interiors
                ],
            ]
            for polygon in multipolygon.geoms
        ],
    }


# 构建规则侧保护区规格对象。
def build_protection_zone_spec(
    *,
    station_id: int,
    station_type: str,
    rule_code: str,
    rule_name: str,
    zone_code: str,
    zone_name: str,
    region_code: str,
    region_name: str,
    local_geometry: Polygon | MultiPolygon,
    vertical_definition: dict[str, object],
    render_geometry: dict[str, object] | None = None,
) -> ProtectionZoneSpec:
    multipolygon = ensure_multipolygon(ensure_polygonal_geometry(local_geometry))
    return ProtectionZoneSpec(
        station_id=station_id,
        station_type=station_type,
        rule_code=rule_code,
        rule_name=rule_name,
        zone_code=zone_code,
        zone_name=zone_name,
        region_code=region_code,
        region_name=region_name,
        local_geometry=multipolygon,
        geometry_definition=build_geometry_definition(multipolygon),
        vertical_definition=vertical_definition,
        render_geometry=render_geometry,
    )
