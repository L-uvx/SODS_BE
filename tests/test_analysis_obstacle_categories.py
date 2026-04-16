from app.analysis.obstacle_categories import normalize_obstacle_type


def test_normalize_obstacle_type_maps_known_global_types() -> None:
    assert normalize_obstacle_type("建筑物/构建物") == "building_general"
    assert (
        normalize_obstacle_type("高压架空输电线路")
        == "power_line_high_voltage_overhead"
    )
    assert normalize_obstacle_type("气象雷达站") == "weather_radar_station"


def test_normalize_obstacle_type_returns_unclassified_for_unknown_type() -> None:
    assert normalize_obstacle_type("未知障碍物") == "unclassified"
