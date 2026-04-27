PROTECTION_ZONE_COLOR_PALETTE = {
    "default_blue": {
        "colorKey": "default_blue",
        "fill": "rgba(64, 158, 255, 0.25)",
        "stroke": "rgba(64, 158, 255, 0.9)",
    },
    "sky_blue": {
        "colorKey": "sky_blue",
        "fill": "rgba(96, 165, 250, 0.25)",
        "stroke": "rgba(96, 165, 250, 0.9)",
    },
    "teal_green": {
        "colorKey": "teal_green",
        "fill": "rgba(45, 212, 191, 0.25)",
        "stroke": "rgba(45, 212, 191, 0.9)",
    },
    "amber_orange": {
        "colorKey": "amber_orange",
        "fill": "rgba(251, 191, 36, 0.25)",
        "stroke": "rgba(251, 191, 36, 0.9)",
    },
    "violet_purple": {
        "colorKey": "violet_purple",
        "fill": "rgba(167, 139, 250, 0.25)",
        "stroke": "rgba(167, 139, 250, 0.9)",
    },
    "danger_red": {
        "colorKey": "danger_red",
        "fill": "rgba(245, 108, 108, 0.25)",
        "stroke": "rgba(245, 108, 108, 0.9)",
    },
    "lime_green": {
        "colorKey": "lime_green",
        "fill": "rgba(163, 230, 53, 0.25)",
        "stroke": "rgba(163, 230, 53, 0.9)",
    },
    "cyan_blue": {
        "colorKey": "cyan_blue",
        "fill": "rgba(34, 211, 238, 0.25)",
        "stroke": "rgba(34, 211, 238, 0.9)",
    },
    "slate_gray": {
        "colorKey": "slate_gray",
        "fill": "rgba(148, 163, 184, 0.25)",
        "stroke": "rgba(148, 163, 184, 0.9)",
    },
    "emerald_green": {
        "colorKey": "emerald_green",
        "fill": "rgba(16, 185, 129, 0.25)",
        "stroke": "rgba(16, 185, 129, 0.9)",
    },
    "pink_rose": {
        "colorKey": "pink_rose",
        "fill": "rgba(244, 114, 182, 0.25)",
        "stroke": "rgba(244, 114, 182, 0.9)",
    },
    "indigo_blue": {
        "colorKey": "indigo_blue",
        "fill": "rgba(99, 102, 241, 0.25)",
        "stroke": "rgba(99, 102, 241, 0.9)",
    },
}

DEFAULT_PROTECTION_ZONE_COLOR_KEY = "default_blue"

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
    ("loc_building_restriction_zone", "1"): "lime_green",
    ("loc_building_restriction_zone", "2"): "lime_green",
    ("loc_building_restriction_zone", "3"): "danger_red",
    ("loc_building_restriction_zone", "4"): "cyan_blue",
}


def resolve_protection_zone_style(*, zone_code: str, region_code: str) -> dict[str, str]:
    color_key = PROTECTION_ZONE_REGION_COLOR_MAPPING.get(
        (zone_code, region_code),
        DEFAULT_PROTECTION_ZONE_COLOR_KEY,
    )
    return dict(PROTECTION_ZONE_COLOR_PALETTE[color_key])
