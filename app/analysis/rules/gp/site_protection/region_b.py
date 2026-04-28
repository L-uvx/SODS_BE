from dataclasses import dataclass

from app.analysis.rule_result import AnalysisRuleResult
from app.analysis.rules.base import ObstacleRule
from app.analysis.rules.geometry_helpers import resolve_obstacle_shape
from app.analysis.rules.gp.clearance import calculate_gp_clearance_limit_height_meters
from app.analysis.rules.gp.site_protection.common import BoundGpSiteProtectionRegionRule
from app.analysis.rules.gp.site_protection.helpers import (
    GpSiteProtectionSharedContext,
    build_gp_site_protection_region_b_geometry,
)
from app.analysis.rules.gp.site_protection.judgement import (
    calculate_gp_zone_intersection_min_forward_distance_meters,
    is_gp_airport_ring_road_category,
)
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


@dataclass(slots=True)
class BoundGpSiteProtectionRegionBRule(BoundGpSiteProtectionRegionRule):
    shared_context: GpSiteProtectionSharedContext

    # 执行 GP 场地保护区 B 区最小真实判定。
    def analyze(self, obstacle: dict[str, object]) -> AnalysisRuleResult:
        obstacle_shape = resolve_obstacle_shape(obstacle)
        entered_protection_zone = obstacle_shape.intersects(
            self.protection_zone.local_geometry
        )

        station_sub_type = (
            None if self.station_sub_type is None else self.station_sub_type.upper()
        )
        global_obstacle_category = str(obstacle["globalObstacleCategory"])
        is_airport_ring_road = is_gp_airport_ring_road_category(global_obstacle_category)
        forward_distance_meters = None
        requires_clearance_evaluation = False

        if not entered_protection_zone:
            is_compliant = True
            message = "obstacle outside GP site protection region B"
        else:
            forward_distance_meters = (
                calculate_gp_zone_intersection_min_forward_distance_meters(
                    obstacle_geometry=dict(obstacle_shape.__geo_interface__),
                    zone_geometry=self.protection_zone.local_geometry,
                    shared_context=self.shared_context,
                )
            )
            if forward_distance_meters is None:
                is_compliant = True
                message = "obstacle outside GP site protection region B"
            elif self.protection_zone.zone_code == "gp_site_protection_gb":
                if forward_distance_meters <= 600.0:
                    is_compliant = False
                    message = "obstacle within GP region B forward 600m"
                else:
                    requires_clearance_evaluation = True
                    clearance_limit_height_meters = (
                        calculate_gp_clearance_limit_height_meters(
                            runway_context=self.shared_context.runway_context,
                            obstacle=obstacle,
                        )
                    )
                    if clearance_limit_height_meters is None:
                        is_compliant = True
                        message = "gp clearance evaluation pending"
                    else:
                        over_height_meters = float(obstacle["topElevation"]) - float(
                            clearance_limit_height_meters
                        )
                        is_compliant = over_height_meters <= 0.0
                        message = (
                            "obstacle within GP clearance limit"
                            if is_compliant
                            else "obstacle exceeds GP clearance limit"
                        )
            elif station_sub_type == "I":
                is_compliant = False
                message = "obstacle enters GP MH region B subtype I"
            elif station_sub_type in {"II", "III"}:
                if is_airport_ring_road:
                    is_compliant = forward_distance_meters > 600.0
                    message = (
                        "airport ring road outside GP MH region B forward 600m"
                        if is_compliant
                        else "airport ring road within GP MH region B forward 600m"
                    )
                else:
                    is_compliant = False
                    message = "non-ring-road obstacle enters GP MH region B"
            else:
                is_compliant = False
                message = "obstacle enters GP site protection region B"

        return self.build_result(
            obstacle=obstacle,
            is_compliant=is_compliant,
            message=message,
            metrics={
                "enteredProtectionZone": entered_protection_zone,
                "forwardDistanceMeters": forward_distance_meters,
                "isAirportRingRoad": is_airport_ring_road,
                "requiresClearanceEvaluation": requires_clearance_evaluation,
                **(
                    {}
                    if self.protection_zone.zone_code != "gp_site_protection_gb"
                    or forward_distance_meters is None
                    or forward_distance_meters <= 600.0
                    else {
                        "clearanceLimitHeightMeters": clearance_limit_height_meters,
                        "overHeightMeters": (
                            None
                            if clearance_limit_height_meters is None
                            else float(obstacle["topElevation"])
                            - float(clearance_limit_height_meters)
                        ),
                    }
                ),
                "stationSubType": station_sub_type,
            },
        )


class _GpSiteProtectionRegionBRuleBase(ObstacleRule):
    region_code = "B"
    region_name = "B"

    # 绑定 GP 场地保护区 B 区。
    def bind(
        self,
        *,
        station: object,
        shared_context: GpSiteProtectionSharedContext,
    ) -> BoundGpSiteProtectionRegionBRule:
        region_geometry = build_gp_site_protection_region_b_geometry(shared_context)
        return BoundGpSiteProtectionRegionBRule(
            protection_zone=build_protection_zone_spec(
                station_id=int(station.id),
                station_type=str(station.station_type),
                rule_code=self.rule_code,
                rule_name=self.rule_name,
                zone_code=self.zone_code,
                zone_name=self.zone_name,
                region_code=self.region_code,
                region_name=self.region_name,
                local_geometry=region_geometry.local_geometry,
                vertical_definition={
                    "mode": "flat",
                    "baseReference": "station",
                    "baseHeightMeters": float(getattr(station, "altitude", 0.0) or 0.0),
                },
            ),
            station_sub_type=(
                None
                if getattr(station, "station_sub_type", None) is None
                else str(getattr(station, "station_sub_type"))
            ),
            standards_rule_code=self._resolve_standards_rule_code(station=station),
            shared_context=shared_context,
        )

    def _resolve_standards_rule_code(self, *, station: object) -> str:
        return self.rule_code


class GpSiteProtectionGbRegionBRule(_GpSiteProtectionRegionBRuleBase):
    rule_code = "gp_site_protection_gb_region_b"
    rule_name = "gp_site_protection_gb_region_b"
    zone_code = "gp_site_protection_gb"
    zone_name = "GP site protection (GB)"


class GpSiteProtectionMhRegionBRule(_GpSiteProtectionRegionBRuleBase):
    rule_code = "gp_site_protection_mh_region_b"
    rule_name = "gp_site_protection_mh_region_b"
    zone_code = "gp_site_protection_mh"
    zone_name = "GP site protection (MH)"

    def _resolve_standards_rule_code(self, *, station: object) -> str:
        station_sub_type = str(getattr(station, "station_sub_type", "") or "").upper()
        if station_sub_type in {"I", "II", "III"}:
            return f"{self.rule_code}_{station_sub_type.lower()}"
        return self.rule_code


__all__ = [
    "GpSiteProtectionGbRegionBRule",
    "GpSiteProtectionMhRegionBRule",
]
