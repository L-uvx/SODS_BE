from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rules.base import BoundObstacleRule, ObstacleRule
from app.analysis.rules.geometry_helpers import build_circle_polygon, ensure_multipolygon
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


class WindRadarRule(ObstacleRule):
    # 绑定单个 WindRadar 台站上下文。
    def bind(self, *args, **kwargs) -> BoundObstacleRule:  # pragma: no cover
        raise NotImplementedError
def build_wind_radar_circle_protection_zone(
    *,
    station: object,
    rule_code: str,
    rule_name: str,
    zone_code: str,
    zone_name: str,
    station_point: tuple[float, float],
    radius_meters: float,
    vertical_definition: dict[str, object],
) -> ProtectionZoneSpec:
    local_geometry = ensure_multipolygon(
        build_circle_polygon(center_point=station_point, radius_meters=radius_meters)
    )
    return build_protection_zone_spec(
        station_id=int(station.id),
        station_type=str(station.station_type),
        rule_code=rule_code,
        rule_name=rule_name,
        zone_code=zone_code,
        zone_name=zone_name,
        region_code="default",
        region_name="default",
        local_geometry=local_geometry,
        vertical_definition=vertical_definition,
    )
