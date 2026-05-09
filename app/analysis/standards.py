from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree


@dataclass(frozen=True, slots=True)
class AnalysisStandardReference:
    code: str
    text: str
    is_compliant: bool | None = None


@dataclass(frozen=True, slots=True)
class AnalysisStandardSet:
    gb: list[AnalysisStandardReference]
    mh: list[AnalysisStandardReference]


_STANDARD_CONFIG_PATH = Path(__file__).resolve().parents[2] / "Standard.config"

_NDB_STANDARD_KEYS: dict[str, tuple[list[str], list[str]]] = {
    "ndb_minimum_distance_50m": (
        ["GB_NDB_50m最小间距区域_50"],
        ["MH_NDB_50m最小间距区域_50"],
    ),
    "ndb_minimum_distance_150m": (
        ["GB_NDB_150m最小间距区域_150"],
        ["MH_NDB_150m最小间距区域_150"],
    ),
    "ndb_minimum_distance_300m": (
        ["GB_NDB_300m最小间距区域_300"],
        ["MH_NDB_300m最小间距区域_300"],
    ),
    "ndb_minimum_distance_500m": (
        ["GB_NDB_500m最小间距区域_500"],
        ["MH_NDB_500m最小间距区域_500"],
    ),
    "ndb_conical_clearance_3deg": (
        ["GB_NDB_50米以外仰角区域"],
        ["MH_NDB_50米以外仰角区域"],
    ),
}

_LOC_STANDARD_KEYS: dict[str, tuple[list[str], list[str]]] = {
    "loc_site_protection": (
        ["GB_ILSLOC_场地保护区"],
        ["MH_ILSLOC_场地保护区"],
    ),
    "loc_forward_sector_3000m_15m": (
        ["GB_ILSLOC_前向正负10°，3000米区域"],
        ["MH_ILSLOC_前向正负10°，3000米区域"],
    ),
    "loc_site_protection_cable": (
        ["GB_ILSLOC_场地保护区_线缆"],
        ["MH_ILSLOC_场地保护区_线缆"],
    ),
    "loc_building_restriction_zone": (
        [],
        ["MH_ILSLOC_建筑物限制区_Ⅲ"],
    ),
    "loc_run_area_protection_critical": (
        [],
        ["MH_ILSLOC_运行保护区_临界区"],
    ),
    "loc_run_area_protection_sensitive": (
        [],
        ["MH_ILSLOC_运行保护区_敏感区"],
    ),
}

_MB_STANDARD_KEYS: dict[str, tuple[list[str], list[str]]] = {
    "mb_site_protection_region_i_iii": (
        ["GB_MB_指点信标保护区_Ⅰ_Ⅲ"],
        ["MH_MB_指点信标保护区_Ⅰ_Ⅲ"],
    ),
    "mb_site_protection_region_ii_iv": (
        ["GB_MB_指点信标保护区_Ⅱ_Ⅳ"],
        ["MH_MB_指点信标保护区_Ⅱ_Ⅳ"],
    ),
}

_HF_STANDARD_KEYS: dict[str, tuple[list[str], list[str]]] = {
    "hf_minimum_distance_0_8km_electrified_railway": (
        ["AP_HF_0.8km平面防护间距要求_电气化铁路"],
        [],
    ),
    "hf_minimum_distance_1km_110kv_power_line": (
        ["AP_HF_1km平面防护间距要求_110kV高压架空输电线路"],
        [],
    ),
    "hf_minimum_distance_1km_road": (
        ["AP_HF_1km平面防护间距要求_道路/公路"],
        [],
    ),
    "hf_minimum_distance_1_3km_220_330kv_power_line": (
        ["AP_HF_1.3km平面防护间距要求_220到330kV高压架空输电线路"],
        [],
    ),
    "hf_minimum_distance_1_8km_500kv_power_line": (
        ["AP_HF_1.8km平面防护间距要求_500kV高压架空输电线路"],
        [],
    ),
    "hf_minimum_distance_2km_short_wave_outside_quarter_0_5_to_5kw": (
        ["AP_HF_2km平面防护间距要求_0.5到5kW短波发射台（通信方向1/4功率角外）"],
        [],
    ),
    "hf_minimum_distance_2km_short_wave_outside_quarter_5_to_25kw": (
        ["AP_HF_2km平面防护间距要求_5到25kW短波发射台（通信方向1/4功率角外）"],
        [],
    ),
    "hf_minimum_distance_4km_short_wave_quarter_0_5_to_5kw": (
        ["AP_HF_4km平面防护间距要求_0.5到5kW短波发射台（通信方向1/4功率角）"],
        [],
    ),
    "hf_minimum_distance_4km_short_wave_quarter_5_to_25kw": (
        ["AP_HF_4km平面防护间距要求_5到25kW短波发射台（通信方向1/4功率角）"],
        [],
    ),
    "hf_minimum_distance_5km_short_wave_outside_quarter_25_to_120kw": (
        ["AP_HF_5km平面防护间距要求_25到120kW短波发射台（通信方向1/4功率角外）"],
        [],
    ),
    "hf_minimum_distance_5km_rf_equipment": (
        ["AP_HF_5km平面防护间距要求_工、科、医射频设备"],
        [],
    ),
    "hf_minimum_distance_10km_medium_long_wave_50kw_below": (
        ["AP_HF_10km平面防护间距要求_50kW以下中波和长波发射台"],
        [],
    ),
    "hf_minimum_distance_10km_short_wave_quarter_25_to_120kw": (
        ["AP_HF_10km平面防护间距要求_25到120kW短波发射台（通信方向1/4功率角）"],
        [],
    ),
    "hf_minimum_distance_10km_short_wave_outside_quarter_above_120kw": (
        ["AP_HF_10km平面防护间距要求_120kW以上短波发射台（通信方向1/4功率角外）"],
        [],
    ),
    "hf_minimum_distance_15km_medium_long_wave_100_to_150kw": (
        ["AP_HF_15km平面防护间距要求_100到150kW中波和长波发射台"],
        [],
    ),
    "hf_minimum_distance_20km_medium_long_wave_above_200kw": (
        ["AP_HF_20km平面防护间距要求_200kW以上中波和长波发射台"],
        [],
    ),
    "hf_minimum_distance_20km_short_wave_quarter_above_120kw": (
        ["AP_HF_20km平面防护间距要求_120kW以上短波发射台（通信方向1/4功率角）"],
        [],
    ),
}

_VHF_STANDARD_KEYS: dict[str, tuple[list[str], list[str]]] = {
    "vhf_minimum_distance_0_2km_110kv_power_line": (
        ["AP_VHF_0.2km平面防护间距要求_110kV高压架空输电线路"],
        [],
    ),
    "vhf_minimum_distance_0_25km_220_330kv_power_line": (
        ["AP_VHF_0.25km平面防护间距要求_220到330kV高压架空输电线路"],
        [],
    ),
    "vhf_minimum_distance_0_3km_electrified_railway": (
        ["AP_VHF_0.3km平面防护间距要求_电气化铁路"],
        [],
    ),
    "vhf_minimum_distance_0_3km_trunk_road": (
        ["AP_VHF_0.3km平面防护间距要求_干线公路"],
        [],
    ),
    "vhf_minimum_distance_0_3km_500kv_power_line": (
        ["AP_VHF_0.3km平面防护间距要求_500kV高压架空输电线路"],
        [],
    ),
    "vhf_minimum_distance_0_8km_rf_equipment": (
        ["AP_VHF_0.8km平面防护间距要求_工、科、医射频设备"],
        [],
    ),
    "vhf_minimum_distance_1km_fm_broadcast_1kw_below": (
        ["AP_VHF_1km平面防护间距要求_1kW（含）以下调频广播"],
        [],
    ),
    "vhf_minimum_distance_6km_fm_broadcast_above_1kw": (
        ["AP_VHF_6km平面防护间距要求_1kW以上调频广播"],
        [],
    ),
}

_ADS_B_STANDARD_KEYS: dict[str, tuple[list[str], list[str]]] = {
    "adsb_minimum_distance_0_5km_non_electrified_railway": (
        ["AP_ADS_B_0.5km平面防护间距要求_非电气化铁路"],
        [],
    ),
    "adsb_minimum_distance_0_5km_high_frequency_furnace": (
        ["AP_ADS_B_0.5km平面防护间距要求_高频炉"],
        [],
    ),
    "adsb_minimum_distance_0_5km_industrial_electric_welding": (
        ["AP_ADS_B_0.5km平面防护间距要求_工业电焊"],
        [],
    ),
    "adsb_minimum_distance_0_5km_agricultural_power_equipment": (
        ["AP_ADS_B_0.5km平面防护间距要求_农用电力设备"],
        [],
    ),
    "adsb_minimum_distance_0_7km_110kv_power_line": (
        ["AP_ADS_B_0.7km平面防护间距要求_110kV高压架空输电线路"],
        [],
    ),
    "adsb_minimum_distance_0_7km_110kv_substation": (
        ["AP_ADS_B_0.7km平面防护间距要求_110到220kV高压变电站"],
        [],
    ),
    "adsb_minimum_distance_0_7km_electrified_railway": (
        ["AP_ADS_B_0.7km平面防护间距要求_电气化铁路"],
        [],
    ),
    "adsb_minimum_distance_0_7km_road": (
        ["AP_ADS_B_0.7km平面防护间距要求_公路"],
        [],
    ),
    "adsb_minimum_distance_0_8km_220_330kv_power_line": (
        ["AP_ADS_B_0.8km平面防护间距要求_220到330kV高压架空输电线路"],
        [],
    ),
    "adsb_minimum_distance_0_8km_220_330kv_substation": (
        ["AP_ADS_B_0.8km平面防护间距要求_220到330kV高压变电站"],
        [],
    ),
    "adsb_minimum_distance_1km_500kv_power_line": (
        ["AP_ADS_B_1km平面防护间距要求_500kV高压架空输电线路"],
        [],
    ),
    "adsb_minimum_distance_1km_uhf_therapy_equipment": (
        ["AP_ADS_B_1km平面防护间距要求_超高频理疗机"],
        [],
    ),
    "adsb_minimum_distance_1_2km_500kv_substation": (
        ["AP_ADS_B_1.2km平面防护间距要求_500kV高压变电站"],
        [],
    ),
    "adsb_minimum_distance_1_2km_high_frequency_welding_machine": (
        ["AP_ADS_B_1.2km平面防护间距要求_高频热合机"],
        [],
    ),
}

_GP_STANDARD_KEYS: dict[str, tuple[list[str], list[str]]] = {
    "gp_site_protection_gb_region_a_cable": (
        ["GB_ILSGP_GB场地保护区_A线缆"],
        [],
    ),
    "gp_site_protection_gb_region_a": (
        ["GB_ILSGP_GB场地保护区_A"],
        [],
    ),
    "gp_site_protection_gb_region_b": (
        ["GB_ILSGP_GB场地保护区_B"],
        [],
    ),
    "gp_site_protection_gb_region_c": (
        ["GB_ILSGP_GB场地保护区_C"],
        [],
    ),
    "gp_site_protection_mh_region_a_cable": (
        [],
        ["MH_ILSGP_场地保护区_A线缆"],
    ),
    "gp_site_protection_mh_region_a": (
        [],
        ["MH_ILSGP_场地保护区_A"],
    ),
    "gp_site_protection_mh_region_b_i": (
        [],
        ["MH_ILSGP_场地保护区_B_Ⅰ"],
    ),
    "gp_site_protection_mh_region_b_ii": (
        [],
        ["MH_ILSGP_场地保护区_B_Ⅱ"],
    ),
    "gp_site_protection_mh_region_b_iii": (
        [],
        ["MH_ILSGP_场地保护区_B_Ⅲ"],
    ),
    "gp_site_protection_mh_region_c": (
        [],
        ["MH_ILSGP_场地保护区_C"],
    ),
    "gp_elevation_restriction_1deg": (
        [],
        ["MH_ILSGP_1°仰角限制区域"],
    ),
    "gp_run_area_protection_critical": (
        [],
        ["MH_ILSGP_运行保护区_临界"],
    ),
    "gp_run_area_protection_sensitive": (
        [],
        ["MH_ILSGP_运行保护区_敏感"],
    ),
}

_VOR_STANDARD_KEYS: dict[str, tuple[list[str], list[str]]] = {
    "vor_reflector_mask_area": (
        [],
        ["MH_VORDME_100米内阴影区"],
    ),
    "vor_100m_datum_plane": (
        ["GB_VORDME_100米基准面"],
        ["MH_VORDME_100米基准面"],
    ),
    "vor_100_200_1_5_deg": (
        ["GB_VORDME_100米至200米1.5°仰角"],
        ["MH_VORDME_100米至200米1.5°仰角"],
    ),
    "vor_200m_datum_plane": (
        ["GB_VORDME_200米基准面"],
        ["MH_VORDME_200米基准面"],
    ),
    "vor_200_300_1_5_deg": (
        ["GB_VORDME_200米至300米1.5°仰角"],
        ["MH_VORDME_200米至300米1.5°仰角"],
    ),
    "vor_200m_datum_plane_high_voltage": (
        ["GB_VORDME_200米基准面"],
        ["MH_VORDME_200米基准面_高压线"],
    ),
    "vor_300m_datum_plane": (
        ["GB_VORDME_300米基准面"],
        ["MH_VORDME_300米基准面"],
    ),
    "vor_300_outside_2_5_deg": (
        ["GB_VORDME_300米外2.5°仰角"],
        ["MH_VORDME_300米外2.5°仰角"],
    ),
    "vor_500m_datum_plane": (
        ["GB_VORDME_500米基准面"],
        ["MH_VORDME_500米基准面"],
    ),
}

_RADAR_STANDARD_KEYS: dict[str, tuple[list[str], list[str]]] = {
    "radar_site_protection": (
        [],
        ["MH_PSRSSR_场地保护区"],
    ),
    "radar_minimum_distance_460m_standard": (
        [],
        ["MH_PSRSSR_0.46km平面防护间距要求_金属围栏、构建物、高塔、航站楼"],
    ),
    "radar_minimum_distance_500m_standard": (
        ["AP_PSRSSR_0.5km平面防护间距要求_非电气化铁路"],
        ["MH_PSRSSR_0.5km平面防护间距要求_非电气化铁路"],
    ),
    "radar_minimum_distance_700m_standard": (
        ["AP_PSRSSR_0.7km平面防护间距要求_110kV高压变电站"],
        ["MH_PSRSSR_0.7km平面防护间距要求_110到220kV高压变电站"],
    ),
    "radar_minimum_distance_800m_standard": (
        ["AP_PSRSSR_0.8km平面防护间距要求_广播电台"],
        ["MH_PSRSSR_0.8km平面防护间距要求_广播电台"],
    ),
    "radar_minimum_distance_930m_standard": (
        [],
        ["MH_PSRSSR_0.93km平面防护间距要求_气象雷达站"],
    ),
    "radar_minimum_distance_1000m_standard": (
        ["AP_PSRSSR_1km平面防护间距要求_500kV高压架空输电线路"],
        ["MH_PSRSSR_1km平面防护间距要求_500kV高压架空输电线路"],
    ),
    "radar_minimum_distance_1200m_standard": (
        ["AP_PSRSSR_1.2km平面防护间距要求_500kV高压变电站"],
        ["MH_PSRSSR_1.2km平面防护间距要求_500kV高压变电站"],
    ),
    "radar_minimum_distance_1610m_standard": (
        [],
        ["MH_PSRSSR_1.61km平面防护间距要求_机库等大型金属构建物"],
    ),
    "radar_rotating_reflector_16km_standard": (
        [],
        ["MH_PSRSSR_16KM保护区"],
    ),
}

_WEATHER_RADAR_STANDARD_KEYS: dict[str, tuple[list[str], list[str]]] = {
    "weather_radar_minimum_distance_450m": (
        [],
        ["QX_2016_WeatherRadar_450_防护间距"],
    ),
    "weather_radar_minimum_distance_800m": (
        [],
        ["QX_2016_WeatherRadar_800_防护间距"],
    ),
    "weather_radar_elevation_angle_1deg": (
        [],
        ["QX_2016_WeatherRadar_雷达探测⽅向1°仰角"],
    ),
}

_WIND_RADAR_STANDARD_KEYS: dict[str, tuple[list[str], list[str]]] = {
    "wind_radar_elevation_angle_15deg": (
        [],
        ["QX_2016_WindRadar_探测系统天线15°仰角"],
    ),
}

_STANDARD_KEYS_BY_STATION_TYPE: dict[
    str, dict[str, tuple[list[str], list[str]]]
] = {
    "NDB": _NDB_STANDARD_KEYS,
    "LOC": _LOC_STANDARD_KEYS,
    "MB": _MB_STANDARD_KEYS,
    "HF": _HF_STANDARD_KEYS,
    "VHF": _VHF_STANDARD_KEYS,
    "ADS_B": _ADS_B_STANDARD_KEYS,
    "GP": _GP_STANDARD_KEYS,
    "VOR": _VOR_STANDARD_KEYS,
    "RADAR": _RADAR_STANDARD_KEYS,
    "WeatherRadar": _WEATHER_RADAR_STANDARD_KEYS,
    "WindRadar": _WIND_RADAR_STANDARD_KEYS,
}


# 读取 Standard.config 中的标准条文键值对。
@lru_cache(maxsize=1)
def load_standard_config_entries() -> dict[str, str]:
    root = ElementTree.parse(_STANDARD_CONFIG_PATH).getroot()
    entries: dict[str, str] = {}
    for item in root.findall("./appSettings/add"):
        key = item.attrib.get("key")
        value = item.attrib.get("value")
        if key and value is not None:
            entries[key] = value
    return entries


# 按标准键构建单条标准条文对象。
def _build_standard_references(
    entries: dict[str, str],
    codes: list[str],
) -> list[AnalysisStandardReference]:
    result: list[AnalysisStandardReference] = []
    for code in codes:
        text = entries.get(code)
        if text is not None:
            result.append(AnalysisStandardReference(code=code, text=text))
    return result


# 根据规则结果定位对应的国标与行标条文。
def build_rule_standards(
    *,
    station_type: str,
    rule_name: str,
    region_code: str,
) -> AnalysisStandardSet:
    del region_code
    entries = load_standard_config_entries()
    mapping = _STANDARD_KEYS_BY_STATION_TYPE.get(station_type, {})
    gb_codes, mh_codes = mapping.get(rule_name, ([], []))

    return AnalysisStandardSet(
        gb=_build_standard_references(entries, gb_codes),
        mh=_build_standard_references(entries, mh_codes),
    )
