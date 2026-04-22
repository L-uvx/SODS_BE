NDB_SUPPORTED_CATEGORIES = {
    "building_general",
    "building_hangar",
    "building_terminal",
    "road",
    "airport_ring_road",
    "tree_or_forest",
    "railway_electrified",
    "railway_non_electrified",
    "power_line_low_voltage_overhead",
    "power_or_communication_cable",
    "power_line_high_voltage_overhead",
    "hill",
    "embankment",
}

NDB_MINIMUM_SEPARATION_METERS = {
    "building_general": 50.0,
    "building_hangar": 50.0,
    "building_terminal": 50.0,
    "road": 50.0,
    "airport_ring_road": 50.0,
    "tree_or_forest": 50.0,
    "railway_electrified": 150.0,
    "railway_non_electrified": 150.0,
    "power_line_low_voltage_overhead": 150.0,
    "power_or_communication_cable": 150.0,
    "hill": 300.0,
    "embankment": 300.0,
    "power_line_high_voltage_overhead": 500.0,
}

NDB_CONICAL_CLEARANCE = {
    "inner_radius_m": 50.0,
    "outer_radius_m": 37040.0,
    "vertical_angle_deg": 3.0,
}


# 判断障碍物分类是否受 NDB 规则支持。
def is_ndb_supported_category(category: str) -> bool:
    return category in NDB_SUPPORTED_CATEGORIES
