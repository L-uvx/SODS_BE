import math

import shapely.affinity
from shapely.geometry import Polygon

from app.analysis.config import PROTECTION_ZONE_BUILDER_DISCRETIZATION
from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.rules.geometry_helpers import (
    build_circle_polygon,
    ensure_multipolygon,
    resolve_obstacle_shape,
)
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec
from app.analysis.rules.runway.config import (
    REGION_CODE,
    REGION_NAME,
    RULE_CODE,
    RULE_NAME,
    ZONE_CODE,
    ZONE_NAME,
    _CODE_B_CONFIG,
)
from app.analysis.rule_result import AnalysisRuleResult


# 构建沿跑道方向的体育场形（环形跑道形）多边形。
def build_stadium_polygon(
    center_x: float,
    center_y: float,
    runway_length_m: float,
    radius_m: float,
    direction_degrees: float,
    step_degrees: float,
) -> Polygon:
    half_l = runway_length_m / 2.0
    r = radius_m

    coords: list[tuple[float, float]] = []

    # 右帽圆弧：圆心 (+half_l, 0)，角度 -90° → +90°
    deg = -90.0
    while deg <= 90.0 + 1e-9:
        rad = math.radians(deg)
        coords.append((half_l + r * math.cos(rad), r * math.sin(rad)))
        deg += step_degrees

    # 左帽圆弧：圆心 (-half_l, 0)，角度 +90° → +270°
    deg = 90.0
    while deg <= 270.0 + 1e-9:
        rad = math.radians(deg)
        coords.append((-half_l + r * math.cos(rad), r * math.sin(rad)))
        deg += step_degrees

    coords.append(coords[0])

    polygon = Polygon(coords)
    # C#: RotationZ += 90 - runwayDirection，将导航方位角转为数学旋转角
    rotation_degrees = (90.0 - direction_degrees) % 360.0
    polygon = shapely.affinity.rotate(polygon, rotation_degrees, origin=(0, 0))
    polygon = shapely.affinity.translate(polygon, center_x, center_y)
    return polygon


# 为指定跑道构建电磁环境保护区。
def build_runway_em_protection_zone(
    projector: object,
    runway_context: dict[str, object],
) -> ProtectionZoneSpec | None:
    code_b = runway_context.get("runwayCodeB")
    if not code_b:
        return None

    config = _CODE_B_CONFIG.get(code_b)
    if config is None:
        return None

    radius_m, height_m, is_circle = config
    center_x, center_y = runway_context["localCenterPoint"]
    direction_deg = float(runway_context.get("directionDegrees", 0.0))
    length_m = float(runway_context.get("lengthMeters", 0.0))
    runway_id = runway_context.get("runwayId")
    runway_altitude = float(runway_context.get("altitude", 0.0))

    step_degrees = float(
        PROTECTION_ZONE_BUILDER_DISCRETIZATION["circle_step_degrees"]
    )

    if is_circle:
        polygon = build_circle_polygon(
            center_point=(float(center_x), float(center_y)),
            radius_meters=radius_m,
        )
    else:
        polygon = build_stadium_polygon(
            center_x=float(center_x),
            center_y=float(center_y),
            runway_length_m=length_m,
            radius_m=radius_m,
            direction_degrees=direction_deg,
            step_degrees=step_degrees,
        )

    local_geom = ensure_multipolygon(polygon)

    return build_protection_zone_spec(
        station_id=-(int(runway_id)) if runway_id is not None else 0,
        station_type="RUNWAY",
        rule_code=RULE_CODE,
        rule_name=RULE_NAME,
        zone_code=ZONE_CODE,
        zone_name=ZONE_NAME,
        region_code=REGION_CODE,
        region_name=REGION_NAME,
        local_geometry=local_geom,
        vertical_definition={
            "mode": "flat",
            "baseReference": "runway",
            "baseHeightMeters": runway_altitude + height_m,
        },
        runway_id=int(runway_id) if runway_id is not None else None,
    )


# 为障碍物构建电磁环境保护区规则结果。
def build_runway_em_rule_result(
    obstacle: dict[str, object],
    protection_zone: object,
) -> AnalysisRuleResult:
    obstacle_shape = resolve_obstacle_shape(obstacle)
    is_in_zone = obstacle_shape.intersects(protection_zone.local_geometry)
    return AnalysisRuleResult(
        station_id=protection_zone.station_id,
        station_type="RUNWAY",
        obstacle_id=int(obstacle.get("obstacleId", 0)),
        obstacle_name=str(obstacle.get("obstacleName", "")),
        raw_obstacle_type=str(obstacle.get("rawObstacleType") or ""),
        global_obstacle_category=str(obstacle.get("globalObstacleCategory", "")),
        rule_code=RULE_CODE,
        rule_name=RULE_NAME,
        zone_code=ZONE_CODE,
        zone_name=ZONE_NAME,
        region_code=REGION_CODE,
        region_name=REGION_NAME,
        is_applicable=True,
        is_compliant=True,
        is_mid=True,
        message="在机场电磁环境保护区内" if is_in_zone else "不在机场电磁环境保护区内",
        is_in_zone=is_in_zone,
        over_distance_meters=0.0,
        metrics={"enteredProtectionZone": is_in_zone},
        standards_rule_code=RULE_CODE,
    )
