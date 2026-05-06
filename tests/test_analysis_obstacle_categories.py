from app.analysis.obstacle_categories import normalize_obstacle_type


def test_normalize_obstacle_type_maps_known_global_types() -> None:
    assert normalize_obstacle_type("建筑物/构建物") == "building_general"
    pass
    assert normalize_obstacle_type("气象雷达站") == "weather_radar_station"


def test_normalize_obstacle_type_returns_unclassified_for_unknown_type() -> None:
    assert normalize_obstacle_type("未知障碍物") == "unclassified"


import pytest


@pytest.mark.parametrize("raw_type, expected", [
    ("高压架空输电线路（35kV以下）", "power_line_high_voltage_35kv_below"),
    ("高压架空输电线路（35kV）", "power_line_high_voltage_35kv"),
    ("高压架空输电线路（110kV）", "power_line_high_voltage_110kv"),
    ("高压架空输电线路（220kV）", "power_line_high_voltage_220kv"),
    ("高压架空输电线路（330kV）", "power_line_high_voltage_330kv"),
    ("高压架空输电线路（500kV及以上）", "power_line_high_voltage_500kv_and_above"),
])
def test_normalize_high_voltage_subtypes(raw_type, expected):
    from app.analysis.obstacle_categories import normalize_obstacle_type
    assert normalize_obstacle_type(raw_type) == expected
