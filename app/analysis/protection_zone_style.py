PROTECTION_ZONE_COLOR_PALETTE = {
    "default_blue": {
        "colorKey": "default_blue",
        "fill": "rgba(64, 158, 255, 0.5)",
        "stroke": "rgba(64, 158, 255, 0.9)",
    },
    "sky_blue": {
        "colorKey": "sky_blue",
        "fill": "rgba(96, 165, 250, 0.5)",
        "stroke": "rgba(96, 165, 250, 0.9)",
    },
    "teal_green": {
        "colorKey": "teal_green",
        "fill": "rgba(45, 212, 191, 0.5)",
        "stroke": "rgba(45, 212, 191, 0.9)",
    },
    "amber_orange": {
        "colorKey": "amber_orange",
        "fill": "rgba(251, 191, 36, 0.5)",
        "stroke": "rgba(251, 191, 36, 0.9)",
    },
    "violet_purple": {
        "colorKey": "violet_purple",
        "fill": "rgba(167, 139, 250, 0.5)",
        "stroke": "rgba(167, 139, 250, 0.9)",
    },
    "danger_red": {
        "colorKey": "danger_red",
        "fill": "rgba(245, 108, 108, 0.5)",
        "stroke": "rgba(245, 108, 108, 0.9)",
    },
    "lime_green": {
        "colorKey": "lime_green",
        "fill": "rgba(163, 230, 53, 0.5)",
        "stroke": "rgba(163, 230, 53, 0.9)",
    },
    "cyan_blue": {
        "colorKey": "cyan_blue",
        "fill": "rgba(34, 211, 238, 0.5)",
        "stroke": "rgba(34, 211, 238, 0.9)",
    },
    "slate_gray": {
        "colorKey": "slate_gray",
        "fill": "rgba(148, 163, 184, 0.5)",
        "stroke": "rgba(148, 163, 184, 0.9)",
    },
    "emerald_green": {
        "colorKey": "emerald_green",
        "fill": "rgba(16, 185, 129, 0.5)",
        "stroke": "rgba(16, 185, 129, 0.9)",
    },
    "pink_rose": {
        "colorKey": "pink_rose",
        "fill": "rgba(244, 114, 182, 0.5)",
        "stroke": "rgba(244, 114, 182, 0.9)",
    },
    "indigo_blue": {
        "colorKey": "indigo_blue",
        "fill": "rgba(99, 102, 241, 0.5)",
        "stroke": "rgba(99, 102, 241, 0.9)",
    },
}

DEFAULT_PROTECTION_ZONE_COLOR_KEY = "default_blue"

PROTECTION_ZONE_DISPLAY_NAME_MAPPING = {
    "ndb_minimum_distance_50m":         "NDB 50米最小间距",
    "ndb_minimum_distance_150m":        "NDB 150米最小间距",
    "ndb_minimum_distance_300m":        "NDB 300米最小间距",
    "ndb_minimum_distance_500m":        "NDB 500米最小间距",
    "ndb_conical_clearance_3deg":       "NDB 50 米外 3°区域",
    "loc_site_protection":              "LOC 场地保护区",
    "loc_forward_sector_3000m_15m":     "LOC 前方±10°3000m区域",
    "loc_run_area_protection":          "LOC 运行保护区",
    "loc_building_restriction_zone":    "LOC 建筑物限制区",
    "mb_site_protection":               "MB 场地保护区",
    "gp_site_protection_gb":            "GP 场地保护区（GB）",
    "gp_site_protection_mh":            "GP 场地保护区（MH）",
    "gp_run_area_protection":           "GP 运行保护区",
    "gp_elevation_restriction_1deg":    "GP 1°仰角限制区域",
    "radar_minimum_distance_zone_460m": "Radar 460米最小间距",
    "radar_minimum_distance_zone_500m": "Radar 500米最小间距",
    "radar_minimum_distance_zone_700m": "Radar 700米最小间距",
    "radar_minimum_distance_zone_800m": "Radar 800米最小间距",
    "radar_minimum_distance_zone_930m": "Radar 930米最小间距",
    "radar_minimum_distance_zone_1000m": "Radar 1000米最小间距",
    "radar_minimum_distance_zone_1200m": "Radar 1200米最小间距",
    "radar_minimum_distance_zone_1610m": "Radar 1610米最小间距",
    "radar_rotating_reflector_zone_16km": "Radar 16KM rotating reflector zone",
    "vor_reflector_mask_area":          "VOR 100米内阴影区",
    "vor_100m_datum_plane":             "VOR 100米基准面",
    "vor_100_200_1_5_deg":             "VOR 100米至200米1.5°仰角",
    "vor_200m_datum_plane":             "VOR 200米基准面",
    "vor_200_300_1_5_deg":             "VOR 200米至300米1.5°仰角",
    "vor_300m_datum_plane":             "VOR 300米基准面",
    "vor_300_outside_2_5_deg":         "VOR 300米外2.5°仰角",
    "vor_500m_datum_plane":             "VOR 500米基准面",
}

PROTECTION_ZONE_REGION_COLOR_MAPPING = {
    ("ndb_minimum_distance_50m", "default"): "sky_blue",
    ("ndb_minimum_distance_150m", "default"): "teal_green",
    ("ndb_minimum_distance_300m", "default"): "amber_orange",
    ("ndb_minimum_distance_500m", "default"): "violet_purple",
    ("ndb_conical_clearance_3deg", "default"): "emerald_green",
    ("loc_site_protection", "default"): "pink_rose",
    ("loc_forward_sector_3000m_15m", "default"): "indigo_blue",
    ("loc_run_area_protection", "A"): "sky_blue",
    ("loc_run_area_protection", "B"): "teal_green",
    ("loc_run_area_protection", "C"): "danger_red",
    ("loc_run_area_protection", "D"): "amber_orange",
    ("mb_site_protection", "I"): "sky_blue",
    ("mb_site_protection", "II"): "teal_green",
    ("mb_site_protection", "III"): "sky_blue",
    ("mb_site_protection", "IV"): "teal_green",
    ("gp_site_protection_gb", "A"): "sky_blue",
    ("gp_site_protection_gb", "B"): "teal_green",
    ("gp_site_protection_gb", "C"): "danger_red",
    ("gp_site_protection_mh", "A"): "sky_blue",
    ("gp_site_protection_mh", "B"): "teal_green",
    ("gp_site_protection_mh", "C"): "danger_red",
    ("gp_run_area_protection", "A"): "danger_red",
    ("gp_run_area_protection", "B"): "teal_green",
    ("gp_elevation_restriction_1deg", "default"): "amber_orange",
    ("radar_minimum_distance_zone_460m", "default"): "sky_blue",
    ("radar_minimum_distance_zone_500m", "default"): "teal_green",
    ("radar_minimum_distance_zone_700m", "default"): "amber_orange",
    ("radar_minimum_distance_zone_800m", "default"): "emerald_green",
    ("radar_minimum_distance_zone_930m", "default"): "lime_green",
    ("radar_minimum_distance_zone_1000m", "default"): "cyan_blue",
    ("radar_minimum_distance_zone_1200m", "default"): "indigo_blue",
    ("radar_minimum_distance_zone_1610m", "default"): "slate_gray",
    ("radar_rotating_reflector_zone_16km", "default"): "danger_red",
    ("loc_building_restriction_zone", "1"): "lime_green",
    ("loc_building_restriction_zone", "2"): "lime_green",
    ("loc_building_restriction_zone", "3"): "danger_red",
    ("loc_building_restriction_zone", "4"): "cyan_blue",
    ("vor_reflector_mask_area", "default"): "danger_red",
    ("vor_100m_datum_plane", "default"): "sky_blue",
    ("vor_100_200_1_5_deg", "default"): "lime_green",
    ("vor_200m_datum_plane", "default"): "teal_green",
    ("vor_200_300_1_5_deg", "default"): "emerald_green",
    ("vor_300m_datum_plane", "default"): "amber_orange",
    ("vor_300_outside_2_5_deg", "default"): "sky_blue",
    ("vor_500m_datum_plane", "default"): "violet_purple",
}


def resolve_protection_zone_style(*, zone_code: str, region_code: str) -> dict[str, str]:
    color_key = PROTECTION_ZONE_REGION_COLOR_MAPPING.get(
        (zone_code, region_code),
        DEFAULT_PROTECTION_ZONE_COLOR_KEY,
    )
    return dict(PROTECTION_ZONE_COLOR_PALETTE[color_key])


def resolve_protection_zone_name(*, zone_code: str, fallback: str | None = None) -> str:
    if zone_code in PROTECTION_ZONE_DISPLAY_NAME_MAPPING:
        return PROTECTION_ZONE_DISPLAY_NAME_MAPPING[zone_code]
    if fallback is not None:
        return fallback
    return zone_code
