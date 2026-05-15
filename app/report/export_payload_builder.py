from typing import Any

from app.analysis.result_helpers import ceil2, floor2
from app.analysis.rules.runway.config import ZONE_CODE as EM_ZONE_CODE
from app.models.analysis_task import AnalysisTask
from app.analysis.rules.radar.cumulative_analysis import compute_cumulative_horizontal_mask_angles


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
        if min_h <= max_h:
            avg = (min_h + max_h) / 2
        else:
            avg = (min_h + max_h + 360) / 2
            if avg >= 360:
                avg -= 360
        azimuth_str = f"{avg:.2f}°"
    else:
        single = max_h if max_h is not None else min_h
        azimuth_str = f"{single:.2f}°" if single is not None else ""

    distance = metrics.get("actualDistanceMeters")
    distance_str = f"{distance:.2f}" if distance is not None else ""

    top_elevation = metrics.get("topElevationMeters")
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
    obstacle_overheights: dict[str, list[float]] = {}

    for r in rule_results:
        # Priority 1: isFilterIntersect skip
        if r.get("isFilterIntersect"):
            continue
        if not r.get("isApplicable", True) and not (r.get("isMid") or r.get("isFilterLimit")):
            continue
        if r.get("zoneCode") == EM_ZONE_CODE:
            continue

        obstacle_name = r.get("obstacleName", "")
        station_name = r.get("stationName", "")
        obstacle_type = r.get("rawObstacleType", "")
        metrics = r.get("metrics") or {}
        details = r.get("message") or r.get("details") or ""
        relative_position = _build_relative_position(metrics, r)

        # Priority 4: isMid or isFilterLimit → special display
        is_special_no_judge = bool(r.get("isMid") or r.get("isFilterLimit"))
        is_compliant: bool = bool(r.get("isCompliant", True))

        # Priority 5: LOC building restriction zone special message
        is_loc_brz_special = (
            r.get("zoneCode") == "loc_building_restriction_zone"
            and metrics.get("enteredProtectionZone") is True
        )

        # Priority 6: Radar 16KM special message
        is_radar_16km_special = (
            r.get("ruleCode") == "radar_rotating_reflector_16km"
            and metrics.get("enteredProtectionZone") is True
        )

        skip_overheight_tracking = is_special_no_judge

        if is_special_no_judge:
            compliance_status = "不判断"
            height_limit_display = "/"
            over_height_display = "/"
        elif is_loc_brz_special:
            compliance_status = (
                "建议结合MH4003.1-2021《民用航空通信导航监视台(站)设置场地规范 "
                "第1部分:导航》标准要求确定是否开展计算机仿真工作"
            )
            height_val = _float_or_none(metrics.get("allowedHeightMeters"))
            height_limit_display = floor2(height_val or 0)
            over = _float_or_none(metrics.get("overHeightMeters"))
            over_height_display = ceil2(over or 0)
        elif is_radar_16km_special:
            compliance_status = (
                "位于台站16km范围内，根据MHT4003.2-2014《民用航空通信导航监视台(站)"
                "设置场地规范 第2部分:监视》要求，需论证是否影响雷达正常工作"
            )
            height_val = _float_or_none(metrics.get("allowedHeightMeters"))
            height_limit_display = floor2(height_val or 0)
            over = _float_or_none(metrics.get("overHeightMeters"))
            over_height_display = ceil2(over or 0)
        else:
            compliance_status = "满足" if is_compliant else "不满足"
            height_val = _float_or_none(metrics.get("allowedHeightMeters"))
            height_limit_display = floor2(height_val or 0)
            over = _float_or_none(metrics.get("overHeightMeters"))
            over_height_display = ceil2(over or 0)

        gb_list = _normalize_standards(r.get("standards", {}).get("gb"))
        mh_list = _normalize_standards(r.get("standards", {}).get("mh"))

        if not gb_list and not mh_list:
            row = {
                "obstacleName": obstacle_name,
                "obstacleType": obstacle_type,
                "stationName": station_name,
                "relativePosition": relative_position,
                "standardName": "/",
                "standardClause": "/",
                "analysisDetail": details,
                "heightLimit": height_limit_display,
                "isCompliant": is_compliant,
                "complianceStatus": compliance_status,
                "overHeight": over_height_display,
            }
            rows.append(row)
            if not skip_overheight_tracking and not is_compliant:
                key = obstacle_name
                track_over = _float_or_none(metrics.get("overHeightMeters"))
                obstacle_overheights.setdefault(key, []).append(ceil2(track_over or 0))
        else:
            for std_key in ("gb", "mh"):
                for s in (gb_list if std_key == "gb" else mh_list):
                    row = {
                        "obstacleName": obstacle_name,
                        "obstacleType": obstacle_type,
                        "stationName": station_name,
                        "relativePosition": relative_position,
                        "standardName": f"《{_extract_standard_name(s.get('code', ''))}》",
                        "standardClause": s.get("text", ""),
                        "analysisDetail": details,
                        "heightLimit": height_limit_display,
                        "isCompliant": is_compliant,
                        "complianceStatus": compliance_status,
                        "overHeight": over_height_display,
                    }
                    rows.append(row)
                    if not skip_overheight_tracking and not is_compliant:
                        key = obstacle_name
                        track_over = _float_or_none(metrics.get("overHeightMeters"))
                        obstacle_overheights.setdefault(key, []).append(ceil2(track_over or 0))

    for row in rows:
        key = row["obstacleName"]
        dists = obstacle_overheights.get(key, [0])
        row["finalOverHeight"] = ceil2(max(dists))

    return rows


def _get_metrics_height(metrics: dict) -> float | None:
    val = metrics.get("allowedHeightMeters")
    if val is not None:
        try:
            return float(val)
        except (TypeError, ValueError):
            pass
    return None


def _collect_radar_unmet_obstacles(cumulative_results: list[dict]) -> set[str]:
    names: set[str] = set()
    for cr in cumulative_results:
        if cr.get("isCompliant") == "不满足":
            for name in cr.get("obstacleNames", []):
                names.add(str(name))
    return names


def _build_summary(rule_results: list[dict], obstacle_count: int, radar_unmet_obstacle_names: set[str]) -> str:
    non_compliant_obstacles: dict[str, float | None] = {}
    for r in rule_results:
        if not r.get("isApplicable", True):
            continue
        if r.get("zoneCode") == EM_ZONE_CODE:
            continue
        metrics = r.get("metrics") or {}
        if r.get("isMid") or r.get("isFilterLimit") or r.get("isFilterIntersect"):
            continue
        if r.get("zoneCode") == "loc_building_restriction_zone" and metrics.get("enteredProtectionZone") is True:
            continue
        if r.get("ruleCode") == "radar_rotating_reflector_16km" and metrics.get("enteredProtectionZone") is True:
            continue

        if not r.get("isCompliant", True):
            name = r.get("obstacleName", "")
            if not name:
                continue
            height = _get_metrics_height(metrics)
            if height is None:
                continue
            prev = non_compliant_obstacles.get(name)
            non_compliant_obstacles[name] = min(prev, height) if prev is not None else height

    if not non_compliant_obstacles:
        base = f"共分析障碍物{obstacle_count}个，均满足标准限高要求。"
    else:
        names = sorted(non_compliant_obstacles)
        heights = [
            f"{floor2(non_compliant_obstacles[n]):.2f}"
            for n in names
        ]
        base = (
            f"共分析障碍物{obstacle_count}个，其中{','.join(names)}"
            f"不满足标准限高要求，限制顶部高程为 {'、'.join(heights)}米。"
        )

    all_unmet = set(non_compliant_obstacles.keys()) | radar_unmet_obstacle_names

    if radar_unmet_obstacle_names:
        radar_names_str = "、".join(sorted(radar_unmet_obstacle_names))
        if len(all_unmet) == obstacle_count:
            suffix = f"，{radar_names_str}不满足雷达累计水平遮蔽角的要求，建议根据具体情况分析顶部限高"
        elif obstacle_count == 1:
            suffix = f"，{radar_names_str}不满足雷达累计水平遮蔽角的要求，建议根据具体情况分析顶部限高"
        else:
            suffix = f"，{radar_names_str}不满足雷达累计水平遮蔽角的要求，建议根据具体情况分析顶部限高，其余障碍物均满足标准要求，可按报批高度进行审批"
    else:
        if not non_compliant_obstacles:
            if obstacle_count == 1:
                suffix = "，满足标准要求，可按报批高度进行审批"
            else:
                suffix = "，均满足标准要求，可按报批高度进行审批"
        else:
            if len(non_compliant_obstacles) < obstacle_count:
                suffix = "，其余障碍物均满足标准要求，可按报批高度进行审批"
            else:
                suffix = ""

    return base + suffix


# 将电磁环境保护区结果解析为摘要字符串。
def _build_em_zone_summary(em_zone_result: dict | None) -> str:
    if not em_zone_result or em_zone_result.get("totalRunways", 0) == 0:
        return "未发现机场电磁环境保护区。"
    total = em_zone_result.get("totalObstacles", 0)
    total_inside = em_zone_result.get("totalInside", 0)
    total_outside = em_zone_result.get("totalOutside", 0)
    if total_outside == 0:
        return "所有障碍物均在机场电磁环境保护区内。"
    if total_inside == 0:
        return "所有障碍物均不在机场电磁环境保护区内。"
    runway_parts: list[str] = []
    for rw in em_zone_result.get("runways", []):
        runway_parts.append(
            f"{rw['runwayName']}（区内{rw['insideCount']}个、"
            f"区外{rw['outsideCount']}个）"
        )
    runways_text = "；".join(runway_parts)
    return (
        f"共{total}个障碍物，{total_inside}个在机场电磁环境保护区内，"
        f"{total_outside}个不在。{runways_text}。"
    )


def build_export_payload(analysis_task: AnalysisTask) -> dict[str, Any]:
    result_payload = analysis_task.result_payload or {}
    rule_results = result_payload.get("ruleResults", [])

    station_names_set: set[str] = set()
    standard_codes: set[str] = set()
    for r in rule_results:
        if r.get("zoneCode") == EM_ZONE_CODE:
            continue
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
    project_name = analysis_task.import_batch.project.name if analysis_task.import_batch and analysis_task.import_batch.project else ""

    if not table_rows:
        return {
            "projectName": project_name,
            "airportName": airport_name,
            "standardsUsed": standards_used,
            "stationNames": "、".join(sorted(station_names_set)),
            "cumulativeMaskAngleResults": [],
            "electromagneticZoneResult": "",
            "isEmpty": True,
            "emptyMessage": f"该项目不位于{airport_name}通信、导航、监视台站场地保护区内。",
            "obstacleCount": obstacle_count,
            "summary": "",
            "tableRows": [],
            "nonCompliantRows": [],
            "compliantRows": [],
        }

    cumulative_mask_angle_results = compute_cumulative_horizontal_mask_angles(rule_results)
    radar_unmet_names = _collect_radar_unmet_obstacles(cumulative_mask_angle_results)
    summary = _build_summary(rule_results, obstacle_count, radar_unmet_names)

    non_compliant_rows = [row for row in table_rows if not row["isCompliant"]]
    compliant_rows = [row for row in table_rows if row["isCompliant"]]

    em_zone_results = [
        r for r in rule_results
        if r.get("zoneCode") == EM_ZONE_CODE
    ]
    em_by_runway: dict[str, dict[str, list]] = {}
    for r in em_zone_results:
        rw_name = r.get("stationName", "未知跑道")
        if rw_name not in em_by_runway:
            em_by_runway[rw_name] = {"inside": [], "outside": []}
        is_in_zone = r.get("isInZone", False)
        target = em_by_runway[rw_name]["inside" if is_in_zone else "outside"]
        target.append(r)

    total_inside = sum(
        len(groups["inside"]) for groups in em_by_runway.values()
    )
    total_outside = sum(
        len(groups["outside"]) for groups in em_by_runway.values()
    )

    def _build_obstacle_entry(item: dict) -> dict:
        return {
            "obstacleName": item.get("obstacleName", ""),
            "obstacleId": item.get("obstacleId"),
            "isInZone": item.get("isInZone", False),
        }

    electromagnetic_zone_result = {
        "totalRunways": len(em_by_runway),
        "totalObstacles": len(em_zone_results),
        "totalInside": total_inside,
        "totalOutside": total_outside,
        "runways": sorted(
            [
                {
                    "runwayName": rw_name,
                    "obstacleCount": len(groups["inside"]) + len(groups["outside"]),
                    "insideCount": len(groups["inside"]),
                    "outsideCount": len(groups["outside"]),
                    "obstaclesInside": [
                        _build_obstacle_entry(item)
                        for item in groups["inside"]
                    ],
                    "obstaclesOutside": [
                        _build_obstacle_entry(item)
                        for item in groups["outside"]
                    ],
                }
                for rw_name, groups in em_by_runway.items()
            ],
            key=lambda x: x["runwayName"],
        ),
    }

    em_zone_summary = _build_em_zone_summary(electromagnetic_zone_result)

    return {
        "projectName": project_name,
        "airportName": airport_name,
        "standardsUsed": standards_used,
        "stationNames": "、".join(sorted(station_names_set)),
        "cumulativeMaskAngleResults": cumulative_mask_angle_results,
        "electromagneticZoneResult": em_zone_summary,
        "obstacleCount": obstacle_count,
        "summary": summary,
        "tableRows": table_rows,
        "nonCompliantRows": non_compliant_rows,
        "compliantRows": compliant_rows,
    }
