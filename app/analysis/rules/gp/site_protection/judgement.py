GP_CABLE_CATEGORIES = frozenset({"power_or_communication_cable"})
GP_AIRPORT_RING_ROAD_CATEGORIES = frozenset({"airport_ring_road"})
GP_ROAD_OR_RAIL_CATEGORIES = frozenset(
    {"road", "railway_electrified", "railway_non_electrified"}
)


# 判断是否为 GP 线缆类障碍物。
def is_gp_cable_category(category: str) -> bool:
    return category in GP_CABLE_CATEGORIES


# 判断是否为 GP 机场环场路障碍物。
def is_gp_airport_ring_road_category(category: str) -> bool:
    return category in GP_AIRPORT_RING_ROAD_CATEGORIES


# 判断是否为 GP 道路或铁路类障碍物。
def is_gp_road_or_rail_category(category: str) -> bool:
    return category in GP_ROAD_OR_RAIL_CATEGORIES


__all__ = [
    "is_gp_airport_ring_road_category",
    "is_gp_cable_category",
    "is_gp_road_or_rail_category",
]
