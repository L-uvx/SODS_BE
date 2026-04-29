from app.analysis.protection_zone_style import resolve_protection_zone_name


GP_SITE_PROTECTION_STANDARD_CONFIG = {
    "GB": {
        "zone_code": "gp_site_protection_gb",
        "zone_name": resolve_protection_zone_name(zone_code="gp_site_protection_gb"),
    },
    "MH": {
        "zone_code": "gp_site_protection_mh",
        "zone_name": resolve_protection_zone_name(zone_code="gp_site_protection_mh"),
    },
}

GP_SITE_PROTECTION_COMMON = {
    "region_a_w_m": 30.0,
    "region_a_u_m": 60.0,
    "region_c_x_m": 120.0,
}
