# app/analysis/rules/vor/config.py
from app.analysis.protection_zone_style import resolve_protection_zone_name

VOR_REFLECTOR_MASK_AREA = {
    "zone_code": "vor_reflector_mask_area",
    "zone_name": resolve_protection_zone_name(zone_code="vor_reflector_mask_area"),
    "rule_code": "vor_reflector_mask_area",
    "rule_name": "vor_reflector_mask_area",
    "region_code": "default",
    "region_name": "default",
    "max_outer_radius_m": 100.0,
}
