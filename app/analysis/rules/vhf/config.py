VHF_RULE_CODES_IN_BIND_ORDER = [
    "vhf_minimum_distance_0_2km",
    "vhf_minimum_distance_0_25km",
    "vhf_minimum_distance_0_3km",
    "vhf_minimum_distance_0_8km",
    "vhf_minimum_distance_1km",
    "vhf_minimum_distance_6km",
]

VHF_RULE_CODE_BY_CATEGORY = {
    "power_line_high_voltage_110kv":                "vhf_minimum_distance_0_2km",
    "power_line_high_voltage_220kv":                "vhf_minimum_distance_0_25km",
    "power_line_high_voltage_330kv":                "vhf_minimum_distance_0_25km",
    "railway_electrified":                          "vhf_minimum_distance_0_3km",
    "road":                                         "vhf_minimum_distance_0_3km",
    "power_line_high_voltage_500kv_and_above":      "vhf_minimum_distance_0_3km",
    "industrial_scientific_medical_rf_equipment":   "vhf_minimum_distance_0_8km",
    "fm_broadcast_1kw_below":                       "vhf_minimum_distance_1km",
    "fm_broadcast_above_1kw":                       "vhf_minimum_distance_6km",
}

VHF_STANDARDS_RULE_CODE_BY_CATEGORY = {
    "power_line_high_voltage_110kv":                "vhf_minimum_distance_0_2km_110kv_power_line",
    "power_line_high_voltage_220kv":                "vhf_minimum_distance_0_25km_220_330kv_power_line",
    "power_line_high_voltage_330kv":                "vhf_minimum_distance_0_25km_220_330kv_power_line",
    "railway_electrified":                          "vhf_minimum_distance_0_3km_electrified_railway",
    "road":                                         "vhf_minimum_distance_0_3km_trunk_road",
    "power_line_high_voltage_500kv_and_above":      "vhf_minimum_distance_0_3km_500kv_power_line",
    "industrial_scientific_medical_rf_equipment":   "vhf_minimum_distance_0_8km_rf_equipment",
    "fm_broadcast_1kw_below":                       "vhf_minimum_distance_1km_fm_broadcast_1kw_below",
    "fm_broadcast_above_1kw":                       "vhf_minimum_distance_6km_fm_broadcast_above_1kw",
}
