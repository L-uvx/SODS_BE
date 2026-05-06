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
    gb: AnalysisStandardReference | None
    mh: AnalysisStandardReference | None


_STANDARD_CONFIG_PATH = Path(__file__).resolve().parents[2] / "Standard.config"

_NDB_STANDARD_KEYS: dict[str, tuple[str | None, str | None]] = {
    "ndb_minimum_distance_50m": (
        "GB_NDB_50m最小间距区域_50",
        "MH_NDB_50m最小间距区域_50",
    ),
    "ndb_minimum_distance_150m": (
        "GB_NDB_150m最小间距区域_150",
        "MH_NDB_150m最小间距区域_150",
    ),
    "ndb_minimum_distance_300m": (
        "GB_NDB_300m最小间距区域_300",
        "MH_NDB_300m最小间距区域_300",
    ),
    "ndb_minimum_distance_500m": (
        "GB_NDB_500m最小间距区域_500",
        "MH_NDB_500m最小间距区域_500",
    ),
    "ndb_conical_clearance_3deg": (
        "GB_NDB_50米以外仰角区域",
        "MH_NDB_50米以外仰角区域",
    ),
}

_LOC_STANDARD_KEYS: dict[str, tuple[str | None, str | None]] = {
    "loc_site_protection": (
        "GB_ILSLOC_场地保护区",
        "MH_ILSLOC_场地保护区",
    ),
    "loc_forward_sector_3000m_15m": (
        "GB_ILSLOC_前向正负10°，3000米区域",
        "MH_ILSLOC_前向正负10°，3000米区域",
    ),
    "loc_site_protection_cable": (
        "GB_ILSLOC_场地保护区_线缆",
        "MH_ILSLOC_场地保护区_线缆",
    ),
    "loc_building_restriction_zone": (
        None,
        "MH_ILSLOC_建筑物限制区_Ⅲ",
    ),
    "loc_run_area_protection_critical": (
        None,
        "MH_ILSLOC_运行保护区_临界区",
    ),
    "loc_run_area_protection_sensitive": (
        None,
        "MH_ILSLOC_运行保护区_敏感区",
    ),
}

_GP_STANDARD_KEYS: dict[str, tuple[str | None, str | None]] = {
    "gp_site_protection_gb_region_a_cable": (
        "GB_ILSGP_GB场地保护区_A线缆",
        None,
    ),
    "gp_site_protection_gb_region_a": (
        "GB_ILSGP_GB场地保护区_A",
        None,
    ),
    "gp_site_protection_gb_region_b": (
        "GB_ILSGP_GB场地保护区_B",
        None,
    ),
    "gp_site_protection_gb_region_c": (
        "GB_ILSGP_GB场地保护区_C",
        None,
    ),
    "gp_site_protection_mh_region_a_cable": (
        None,
        "MH_ILSGP_场地保护区_A线缆",
    ),
    "gp_site_protection_mh_region_a": (
        None,
        "MH_ILSGP_场地保护区_A",
    ),
    "gp_site_protection_mh_region_b_i": (
        None,
        "MH_ILSGP_场地保护区_B_Ⅰ",
    ),
    "gp_site_protection_mh_region_b_ii": (
        None,
        "MH_ILSGP_场地保护区_B_Ⅱ",
    ),
    "gp_site_protection_mh_region_b_iii": (
        None,
        "MH_ILSGP_场地保护区_B_Ⅲ",
    ),
    "gp_site_protection_mh_region_c": (
        None,
        "MH_ILSGP_场地保护区_C",
    ),
    "gp_elevation_restriction_1deg": (
        None,
        "MH_ILSGP_1°仰角限制区域",
    ),
    "gp_run_area_protection_critical": (
        None,
        "MH_ILSGP_运行保护区_临界",
    ),
    "gp_run_area_protection_sensitive": (
        None,
        "MH_ILSGP_运行保护区_敏感",
    ),
}

_VOR_STANDARD_KEYS: dict[str, tuple[str | None, str | None]] = {
    "vor_reflector_mask_area": (
        None,
        "MH_VORDME_100米内阴影区",
    ),
    "vor_100m_datum_plane": (
        "GB_VORDME_100米基准面",
        "MH_VORDME_100米基准面",
    ),
    "vor_100_200_1_5_deg": (
        "GB_VORDME_100米至200米1.5°仰角",
        "MH_VORDME_100米至200米1.5°仰角",
    ),
    "vor_200m_datum_plane": (
        "GB_VORDME_200米基准面",
        "MH_VORDME_200米基准面",
    ),
    "vor_200_300_1_5_deg": (
        "GB_VORDME_200米至300米1.5°仰角",
        "MH_VORDME_200米至300米1.5°仰角",
    ),
    "vor_200m_datum_plane_high_voltage": (
        "GB_VORDME_200米基准面",
        "MH_VORDME_200米基准面_高压线",
    ),
    "vor_300m_datum_plane": (
        "GB_VORDME_300米基准面",
        "MH_VORDME_300米基准面",
    ),
    "vor_300_outside_2_5_deg": (
        "GB_VORDME_300米外2.5°仰角",
        "MH_VORDME_300米外2.5°仰角",
    ),
    "vor_500m_datum_plane": (
        "GB_VORDME_500米基准面",
        "MH_VORDME_500米基准面",
    ),
}

_STANDARD_KEYS_BY_STATION_TYPE: dict[
    str, dict[str, tuple[str | None, str | None]]
] = {
    "NDB": _NDB_STANDARD_KEYS,
    "LOC": _LOC_STANDARD_KEYS,
    "GP": _GP_STANDARD_KEYS,
    "VOR": _VOR_STANDARD_KEYS,
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
def _build_standard_reference(
    entries: dict[str, str],
    code: str | None,
) -> AnalysisStandardReference | None:
    if code is None:
        return None
    text = entries.get(code)
    if text is None:
        return None
    return AnalysisStandardReference(code=code, text=text)


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
    gb_code, mh_code = mapping.get(rule_name, (None, None))

    return AnalysisStandardSet(
        gb=_build_standard_reference(entries, gb_code),
        mh=_build_standard_reference(entries, mh_code),
    )
