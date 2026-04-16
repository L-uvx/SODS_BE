GLOBAL_OBSTACLE_CATEGORY_MAPPING = {
    "建筑物/构建物": "building_general",
    "高压架空输电线路": "power_line_high_voltage_overhead",
    "风力涡轮发电机等大型旋转反射物体": "large_rotating_reflector",
    "机库": "building_hangar",
    "航站楼": "building_terminal",
    "电气化铁路": "railway_electrified",
    "非电气化铁路": "railway_non_electrified",
    "道路/公路": "road",
    "山丘": "hill",
    "堤坝": "embankment",
    "铁塔/高塔": "tower",
    "树木/树林": "tree_or_forest",
    "金属围栏/金属栅栏": "metal_fence",
    "电力线缆和通信线缆": "power_or_communication_cable",
    "车辆/航空器/机械": "vehicle_or_aircraft_or_machine",
    "架空低压电力线": "power_line_low_voltage_overhead",
    "机场专用环场路": "airport_ring_road",
    "中波和长波发射台": "radio_emitter_medium_long_wave",
    "短波发射台": "radio_emitter_short_wave",
    "工、科、医射频设备": "industrial_scientific_medical_rf_equipment",
    "调频广播": "fm_broadcast",
    "高压变电站": "high_voltage_substation",
    "高频热合机": "high_frequency_welding_machine",
    "高频炉": "high_frequency_furnace",
    "工业电焊": "industrial_electric_welding",
    "超高频理疗机": "uhf_therapy_equipment",
    "农用电力设备": "agricultural_power_equipment",
    "有无线电辐射的工业设施": "industrial_radio_radiation_facility",
    "气象雷达站": "weather_radar_station",
}


def normalize_obstacle_type(raw_type: str | None) -> str:
    if raw_type is None:
        return "unclassified"

    return GLOBAL_OBSTACLE_CATEGORY_MAPPING.get(raw_type, "unclassified")
