import math
import re
from typing import Any


_DMS_DELIMITER_RE = re.compile(
    r"[度分秒°′″'’\"\\\":EN＇＂〞º\u00b4ʹ\u02da]"
)

_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")

_KM_RE = re.compile(r"[kK][mM]|千米|公里")
_NM_RE = re.compile(r"[nN][mM]|海里")

_RUNWAY_NO_RE = re.compile(r"(\d{2}[LRC]?)")


def _parse_degree(value: Any) -> float | None:
    """
    解析经纬度值，兼容十进制度与度分秒格式。
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    parts = _DMS_DELIMITER_RE.split(value)
    if len(parts) == 1:
        return float(parts[0].strip())

    d = float(parts[0].strip())
    m = float(parts[1].strip()) if len(parts) > 1 else 0.0
    s = float(parts[2].strip()) if len(parts) > 2 else 0.0

    if m < 0 or m >= 60:
        raise ValueError(f"minutes out of range: {m}")
    if s < 0 or s >= 60:
        raise ValueError(f"seconds out of range: {s}")

    return d + m / 60.0 + s / 3600.0


def _get_number_from_string(value: Any) -> float | None:
    """
    从字符串中提取数值，支持 km/nm 单位转换。
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    cleaned = value.replace(" ", "")
    match = _NUMBER_RE.search(cleaned)
    if match is None:
        raise ValueError(f"no number found in: {value!r}")

    num = float(match.group())

    suffix = cleaned[: match.start()] + cleaned[match.end() :]
    if _KM_RE.search(suffix):
        return num * 1000.0
    if _NM_RE.search(suffix):
        return num * 1852.0

    return num


def _extract_runway_info(name: Any) -> str | None:
    """
    从台站名称中提取跑道编号。
    """
    if name is None:
        return None

    match = _RUNWAY_NO_RE.search(name)
    if match:
        return match.group()

    return name.split()[-1]


def _int_floor(value: float) -> float:
    """
    保留两位小数，向下取整。
    """
    return float(math.floor(value * 100) / 100)
