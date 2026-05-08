HF_RULE_CODES_IN_BIND_ORDER = [
    "hf_minimum_distance_0_8km",
    "hf_minimum_distance_1km",
    "hf_minimum_distance_1_3km",
    "hf_minimum_distance_1_8km",
    "hf_minimum_distance_2km",
    "hf_minimum_distance_4km",
    "hf_minimum_distance_5km",
    "hf_minimum_distance_10km",
    "hf_minimum_distance_15km",
    "hf_minimum_distance_20km",
]

HF_RULE_CODE_BY_CATEGORY = {
    "railway_electrified":                                                  "hf_minimum_distance_0_8km",
    "power_line_high_voltage_110kv":                                        "hf_minimum_distance_1km",
    "road":                                                                 "hf_minimum_distance_1km",
    "power_line_high_voltage_220kv":                                        "hf_minimum_distance_1_3km",
    "power_line_high_voltage_330kv":                                        "hf_minimum_distance_1_3km",
    "power_line_high_voltage_500kv_and_above":                              "hf_minimum_distance_1_8km",
    "radio_emitter_short_wave_outside_quarter_power_angle_0_5_to_5kw":      "hf_minimum_distance_2km",
    "radio_emitter_short_wave_outside_quarter_power_angle_5_to_25kw":       "hf_minimum_distance_2km",
    "radio_emitter_short_wave_quarter_power_angle_0_5_to_5kw":              "hf_minimum_distance_4km",
    "radio_emitter_short_wave_quarter_power_angle_5_to_25kw":               "hf_minimum_distance_4km",
    "radio_emitter_short_wave_outside_quarter_power_angle_25_to_120kw":     "hf_minimum_distance_5km",
    "industrial_scientific_medical_rf_equipment":                           "hf_minimum_distance_5km",
    "radio_emitter_medium_long_wave_50kw_below":                            "hf_minimum_distance_10km",
    "radio_emitter_short_wave_quarter_power_angle_25_to_120kw":             "hf_minimum_distance_10km",
    "radio_emitter_short_wave_outside_quarter_power_angle_above_120kw":     "hf_minimum_distance_10km",
    "radio_emitter_medium_long_wave_100_to_150kw":                          "hf_minimum_distance_15km",
    "radio_emitter_medium_long_wave_above_200kw":                           "hf_minimum_distance_20km",
    "radio_emitter_short_wave_quarter_power_angle_above_120kw":             "hf_minimum_distance_20km",
}

HF_EXPLICITLY_UNSUPPORTED_CATEGORIES = {
    # C# 当前没有为“短波发射台（其他）”提供稳定平面防护间距档位，
    # Python 本轮保持显式不适用，而不是隐式漏判。
    "radio_emitter_short_wave_other",
}

HF_STANDARDS_RULE_CODE_BY_CATEGORY = {
    "railway_electrified":                                                  "hf_minimum_distance_0_8km_electrified_railway",
    "power_line_high_voltage_110kv":                                        "hf_minimum_distance_1km_110kv_power_line",
    "road":                                                                 "hf_minimum_distance_1km_road",
    "power_line_high_voltage_220kv":                                        "hf_minimum_distance_1_3km_220_330kv_power_line",
    "power_line_high_voltage_330kv":                                        "hf_minimum_distance_1_3km_220_330kv_power_line",
    "power_line_high_voltage_500kv_and_above":                              "hf_minimum_distance_1_8km_500kv_power_line",
    "radio_emitter_short_wave_outside_quarter_power_angle_0_5_to_5kw":      "hf_minimum_distance_2km_short_wave_outside_quarter_0_5_to_5kw",
    "radio_emitter_short_wave_outside_quarter_power_angle_5_to_25kw":       "hf_minimum_distance_2km_short_wave_outside_quarter_5_to_25kw",
    "radio_emitter_short_wave_quarter_power_angle_0_5_to_5kw":              "hf_minimum_distance_4km_short_wave_quarter_0_5_to_5kw",
    "radio_emitter_short_wave_quarter_power_angle_5_to_25kw":               "hf_minimum_distance_4km_short_wave_quarter_5_to_25kw",
    "radio_emitter_short_wave_outside_quarter_power_angle_25_to_120kw":     "hf_minimum_distance_5km_short_wave_outside_quarter_25_to_120kw",
    "industrial_scientific_medical_rf_equipment":                           "hf_minimum_distance_5km_rf_equipment",
    "radio_emitter_medium_long_wave_50kw_below":                            "hf_minimum_distance_10km_medium_long_wave_50kw_below",
    "radio_emitter_short_wave_quarter_power_angle_25_to_120kw":             "hf_minimum_distance_10km_short_wave_quarter_25_to_120kw",
    "radio_emitter_short_wave_outside_quarter_power_angle_above_120kw":     "hf_minimum_distance_10km_short_wave_outside_quarter_above_120kw",
    "radio_emitter_medium_long_wave_100_to_150kw":                          "hf_minimum_distance_15km_medium_long_wave_100_to_150kw",
    "radio_emitter_medium_long_wave_above_200kw":                           "hf_minimum_distance_20km_medium_long_wave_above_200kw",
    "radio_emitter_short_wave_quarter_power_angle_above_120kw":             "hf_minimum_distance_20km_short_wave_quarter_above_120kw",
}
