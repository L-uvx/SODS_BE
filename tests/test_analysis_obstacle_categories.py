from app.analysis.obstacle_categories import normalize_obstacle_type


def test_normalize_obstacle_type_maps_known_global_types() -> None:
    assert normalize_obstacle_type("建筑物/构建物") == "building_general"
    assert normalize_obstacle_type("气象雷达站") == "weather_radar_station"


def test_normalize_obstacle_type_returns_unclassified_for_unknown_type() -> None:
    assert normalize_obstacle_type("未知障碍物") == "unclassified"


def test_normalize_radar_substation_categories() -> None:
    assert normalize_obstacle_type("高压变电站（110kV）") == "high_voltage_substation_110kv"
    assert normalize_obstacle_type("高压变电站（220-330kV）") == "high_voltage_substation_220kv_or_330kv"
    assert normalize_obstacle_type("高压变电站（500kV及以上）") == "high_voltage_substation_500kv_and_above"
    assert normalize_obstacle_type("高压变电站（其他）") == "high_voltage_substation_other"


def test_normalize_radar_equipment_power_bands() -> None:
    assert normalize_obstacle_type("高频炉（100kW及以下）") == "high_frequency_furnace_100kw_below"
    assert normalize_obstacle_type("高频炉（100kW以上）") == "high_frequency_furnace_above_100kw"
    assert normalize_obstacle_type("工业电焊（10kW及以下）") == "industrial_electric_welding_10kw_below"
    assert normalize_obstacle_type("工业电焊（10kW以上）") == "industrial_electric_welding_above_10kw"
    assert normalize_obstacle_type("超高频理疗机（1kW及以下）") == "uhf_therapy_equipment_1kw_below"
    assert normalize_obstacle_type("超高频理疗机（1kW以上）") == "uhf_therapy_equipment_above_1kw"
    assert normalize_obstacle_type("农用电力设备（1kW及以下）") == "agricultural_power_equipment_1kw_below"
    assert normalize_obstacle_type("农用电力设备（1kW以上）") == "agricultural_power_equipment_above_1kw"


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
    assert normalize_obstacle_type(raw_type) == expected
