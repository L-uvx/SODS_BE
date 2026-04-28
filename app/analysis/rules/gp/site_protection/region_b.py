from app.analysis.rules.base import ObstacleRule
from app.analysis.rules.gp.site_protection.helpers import (
    GpSiteProtectionSharedContext,
    build_gp_site_protection_region_b_geometry,
)
from app.analysis.rules.gp.site_protection.region_a import BoundGpSiteProtectionRegionRule
from app.analysis.rules.protection_zone_helpers import build_protection_zone_spec


class _GpSiteProtectionRegionBRuleBase(ObstacleRule):
    region_code = "B"
    region_name = "B"

    # 绑定 GP 场地保护区 B 区。
    def bind(
        self,
        *,
        station: object,
        shared_context: GpSiteProtectionSharedContext,
    ) -> BoundGpSiteProtectionRegionRule:
        region_geometry = build_gp_site_protection_region_b_geometry(shared_context)
        return BoundGpSiteProtectionRegionRule(
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
