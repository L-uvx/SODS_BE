from dataclasses import dataclass

from shapely.geometry import MultiPolygon


@dataclass(slots=True)
class ProtectionZoneSpec:
    station_id: int
    station_type: str
    rule_code: str
    rule_name: str
    zone_code: str
    zone_name: str
    region_code: str
    region_name: str
    local_geometry: MultiPolygon
    geometry_definition: dict[str, object]
    vertical_definition: dict[str, object]
    render_geometry: dict[str, object] | None = None
