MB_SITE_PROTECTION = {
    "zone_code": "mb_site_protection",
    "radius_m": 30.0,
    "regions": (
        {
            "region_code": "I",
            "region_name": "I",
            "rule_code": "mb_site_protection_region_i_iii",
            "rule_name": "mb_site_protection_region_i_iii",
            "start_offset_deg": 30.0,
            "end_offset_deg": 150.0,
            "limit_angle_deg": 20.0,
        },
        {
            "region_code": "II",
            "region_name": "II",
            "rule_code": "mb_site_protection_region_ii_iv",
            "rule_name": "mb_site_protection_region_ii_iv",
            "start_offset_deg": -30.0,
            "end_offset_deg": 30.0,
            "limit_angle_deg": 45.0,
        },
        {
            "region_code": "III",
            "region_name": "III",
            "rule_code": "mb_site_protection_region_i_iii",
            "rule_name": "mb_site_protection_region_i_iii",
            "start_offset_deg": 210.0,
            "end_offset_deg": 330.0,
            "limit_angle_deg": 20.0,
        },
        {
            "region_code": "IV",
            "region_name": "IV",
            "rule_code": "mb_site_protection_region_ii_iv",
            "rule_name": "mb_site_protection_region_ii_iv",
            "start_offset_deg": 150.0,
            "end_offset_deg": 210.0,
            "limit_angle_deg": 45.0,
        },
    ),
}


__all__ = ["MB_SITE_PROTECTION"]
