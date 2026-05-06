# app/analysis/rules/vor/datum_plane/_base.py
from dataclasses import dataclass

from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import BoundObstacleRule
from app.analysis.rules.geometry_helpers import build_circle_polygon, ensure_multipolygon, resolve_obstacle_shape
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec
from app.analysis.rules.vor.common import _float_or_none


# 校验基准面规则所需的台站海拔与反射网离地高度参数。
def _ensure_datum_plane_params(station: object) -> tuple[float, float] | None:
    altitude = _float_or_none(station.altitude)
    h1 = _float_or_none(station.reflection_net_hag)
    if altitude is None or h1 is None:
        return None
    return (altitude, h1)


# 构建 VOR 整圆 + flat 垂向的保护区规格。
def build_vor_circle_protection_zone(
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
    radius_meters: float,
    base_height_meters: float,
) -> ProtectionZoneSpec:
    protection_zone = ensure_multipolygon(
        build_circle_polygon(
            center_point=station_point,
            radius_meters=radius_meters,
        )
    )
    return build_protection_zone_spec(
        station_id=station_id,
        station_type=station_type,
        rule_code=rule_code,
        rule_name=rule_name,
        zone_code=zone_code,
        zone_name=zone_name,
        region_code=region_code,
        region_name=region_name,
        local_geometry=protection_zone,
        vertical_definition={
            "mode": "flat",
            "baseReference": "station",
            "baseHeightMeters": float(base_height_meters),
        },
    )


@dataclass(slots=True)
class BoundVorDatumPlaneRule(BoundObstacleRule):
    station_point: tuple[float, float]
    benchmark_height: float
    radius_meters: float

    # 执行已绑定的 VOR 基准面高度判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        shape = resolve_obstacle_shape(obstacle)
        entered = shape.intersects(self.protection_zone.local_geometry)

        raw_top = obstacle.get("topElevation")
        top_elevation = float(raw_top if raw_top is not None else 0.0)

        is_compliant = top_elevation <= self.benchmark_height or not entered
        if not entered:
            message = "obstacle outside datum plane zone"
        elif is_compliant:
            message = "obstacle within datum plane height limit"
        else:
            message = "obstacle exceeds datum plane height limit"

        return AnalysisRuleResult(
            station_id=self.protection_zone.station_id,
            station_type=self.protection_zone.station_type,
            obstacle_id=int(obstacle["obstacleId"]),
            obstacle_name=str(obstacle["name"]),
            raw_obstacle_type=obstacle["rawObstacleType"],
            global_obstacle_category=str(obstacle["globalObstacleCategory"]),
            rule_code=self.protection_zone.rule_code,
            rule_name=self.protection_zone.rule_name,
            zone_code=self.protection_zone.zone_code,
            zone_name=self.protection_zone.zone_name,
            region_code=self.protection_zone.region_code,
            region_name=self.protection_zone.region_name,
            is_applicable=True,
            is_compliant=is_compliant,
            message=message,
            metrics={
                "enteredProtectionZone": entered,
                "benchmarkHeightMeters": self.benchmark_height,
                "topElevationMeters": top_elevation,
            },
            standards_rule_code=self.protection_zone.rule_code,
        )
