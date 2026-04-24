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
}

_STANDARD_KEYS_BY_STATION_TYPE: dict[
    str, dict[str, tuple[str | None, str | None]]
] = {
    "NDB": _NDB_STANDARD_KEYS,
    "LOC": _LOC_STANDARD_KEYS,
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
