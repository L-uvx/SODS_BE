from typing import Any

from app.models.analysis_task import AnalysisTask

_STANDARD_NAME_BY_PREFIX: list[tuple[str, str]] = [
    ("MH_PSRSSR_", "MH/T 4003.2-2014"),
    ("MH_ILSGP_", "MH/T 4003.1-2021"),
    ("MH_ILSLOC_", "MH/T 4003.1-2021"),
    ("MH_NDB_", "MH/T 4003.1-2021"),
    ("MH_MB_", "MH/T 4003.1-2021"),
    ("MH_VORDME_", "MH/T 4003.1-2021"),
    ("MH_GP_", "MH/T 4003.1-2021"),
    ("MH_", "MH/T 4003.1-2021"),
    ("GB_", "GB6364-2013"),
    ("AP_", "AP-118-TM-2013-01"),
    ("AC_", "AC-118-TM-2011-01"),
    ("QX_", "民用航空气象探测设施及探测环境管理办法"),
]


def _format_standard_for_list(name: str) -> str:
    """标准名称列表段落用：编号型标准不加书名号，中文名称加书名号。"""
    if not name:
        return ""
    if any(ord(c) > 127 for c in name):
        return f"《{name}》"
    return name


def _extract_standard_name(code: str) -> str:
    if not code:
        return ""
    for prefix, name in _STANDARD_NAME_BY_PREFIX:
        if code.startswith(prefix):
            return name
    return code


def _build_relative_position(metrics: dict | None, rule: dict | None = None) -> str:
    if not metrics:
        return ""
    min_h = metrics.get("min_horizontal_angle_degrees")
    if min_h is None and rule:
        min_h = rule.get("minHorizontalAngleDegrees")
    max_h = metrics.get("max_horizontal_angle_degrees")
    if max_h is None and rule:
        max_h = rule.get("maxHorizontalAngleDegrees")

    if min_h is not None and max_h is not None:
        avg = (min_h + max_h) / 2
        azimuth_str = f"{avg:.2f}°"
    else:
        single = max_h if max_h is not None else min_h
        azimuth_str = f"{single:.2f}°" if single is not None else ""

    distance = metrics.get("actualDistanceMeters") or metrics.get("actualDistance")
    distance_str = f"{distance:.2f}" if distance is not None else ""

    top_elevation = metrics.get("topElevationMeters") or metrics.get("topElevation")
    elevation_str = f"{top_elevation:.2f}" if top_elevation is not None else ""

    parts = []
    if azimuth_str:
        parts.append(f"相对区域方位角{azimuth_str}")
    if distance_str:
        parts.append(f"最近距离{distance_str}米")
    if elevation_str:
        parts.append(f"顶部高程{elevation_str}米")

    return "，".join(parts)


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_standards(value: object) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def _flatten_rule_results(rule_results: list[dict]) -> list[dict]:
    rows: list[dict] = []
    obstacle_station_overheights: dict[tuple[str, str], list[float]] = {}

    for r in rule_results:
        if not r.get("isApplicable", True):
            continue

        obstacle_name = r.get("obstacleName", "")
        station_name = r.get("stationName", "")
        obstacle_type = r.get("rawObstacleType", "")
        is_compliant = r.get("isCompliant", True)
        compliant_text = "满足" if is_compliant else "不满足"
        metrics = r.get("metrics") or {}
        details = r.get("message") or r.get("details") or ""
        relative_position = _build_relative_position(metrics, r)

        for std_key in ("gb", "mh"):
            for s in _normalize_standards(r.get("standards", {}).get(std_key)):
                over_val = r.get("overDistanceMeters")
                if over_val is None:
                    over_val = metrics.get("overDistanceMeters")
                if over_val is None:
                    over_val = metrics.get("overDistance")
                over = _float_or_none(over_val)

                height_val = (
                    metrics.get("allowedHeightMeters")
                    or metrics.get("limitHeightMeters")
                    or metrics.get("heightLimitMeters")
                    or metrics.get("allowedHeight")
                )

                row = {
                    "obstacleName": obstacle_name,
                    "obstacleType": obstacle_type,
                    "stationName": station_name,
                    "relativePosition": relative_position,
                    "standardName": f"《{_extract_standard_name(s.get('code', ''))}》",
                    "standardClause": s.get("text", ""),
                    "analysisDetail": details,
                    "heightLimit": _float_or_none(height_val) or 0,
                    "isCompliant": compliant_text,
                    "overHeight": over or 0,
                }
                rows.append(row)
                key = (obstacle_name, station_name)
                obstacle_station_overheights.setdefault(key, []).append(over or 0)

    for row in rows:
        key = (row["obstacleName"], row["stationName"])
        dists = obstacle_station_overheights.get(key, [0])
        row["finalOverHeight"] = max(dists)

    return rows


def _get_metrics_height(metrics: dict) -> float | None:
    for key in ("allowedHeightMeters", "limitHeightMeters", "heightLimitMeters", "allowedHeight"):
        val = metrics.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    return None


def _build_summary(rule_results: list[dict], obstacle_count: int) -> str:
    non_compliant_obstacles: dict[str, float | None] = {}
    for r in rule_results:
        if not r.get("isApplicable", True):
            continue
        if not r.get("isCompliant", True):
            name = r.get("obstacleName", "")
            if name and name not in non_compliant_obstacles:
                metrics = r.get("metrics") or {}
                non_compliant_obstacles[name] = _get_metrics_height(metrics)

    if not non_compliant_obstacles:
        return f"共分析障碍物{obstacle_count}个，均满足标准限高要求。"

    names = sorted(non_compliant_obstacles)
    heights = [
        f"{non_compliant_obstacles[n]:.2f}" if non_compliant_obstacles[n] is not None else ""
        for n in names
    ]
    return (
        f"共分析障碍物{obstacle_count}个，其中{','.join(names)}"
        f"不满足标准限高要求，限制顶部高程为 {'、'.join(heights)}米。"
    )


def build_export_payload(analysis_task: AnalysisTask) -> dict[str, Any]:
    result_payload = analysis_task.result_payload or {}
    rule_results = result_payload.get("ruleResults", [])

    station_names_set: set[str] = set()
    standard_codes: set[str] = set()
    for r in rule_results:
        sn = r.get("stationName")
        if sn:
            station_names_set.add(sn)
        for s in _normalize_standards(r.get("standards", {}).get("gb")):
            if s.get("code"):
                standard_codes.add(s["code"])
        for s in _normalize_standards(r.get("standards", {}).get("mh")):
            if s.get("code"):
                standard_codes.add(s["code"])

    selected_targets = result_payload.get("selectedTargets", [])
    airport_name = selected_targets[0].get("name", "") if selected_targets else ""

    standard_names_set: set[str] = set()
    for code in standard_codes:
        name = _format_standard_for_list(_extract_standard_name(code))
        if name:
            standard_names_set.add(name)
    standards_used = "、".join(sorted(standard_names_set)) if standard_names_set else ""

    obstacle_count = result_payload.get("obstacleCount", 0)
    table_rows = _flatten_rule_results(rule_results)
    summary = _build_summary(rule_results, obstacle_count)
    non_compliant_rows = [row for row in table_rows if row["isCompliant"] == "不满足"]
    compliant_rows = [row for row in table_rows if row["isCompliant"] == "满足"]

    return {
        "projectName": analysis_task.import_batch.project.name if analysis_task.import_batch and analysis_task.import_batch.project else "",
        "airportName": airport_name,
        "standardsUsed": standards_used,
        "stationNames": "、".join(sorted(station_names_set)),
        "electromagneticZoneResult": "待补充",
        "obstacleCount": obstacle_count,
        "summary": summary,
        "tableRows": table_rows,
        "nonCompliantRows": non_compliant_rows,
        "compliantRows": compliant_rows,
    }
