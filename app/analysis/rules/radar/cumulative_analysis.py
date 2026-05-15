import math
from dataclasses import dataclass


@dataclass
class ObstacleAngleSpan:
    obstacle_id: int
    obstacle_name: str
    min_azimuth: float
    max_azimuth: float


@dataclass
class AngleSnapshot:
    start: float
    end: float
    cumulative: float




# 最大间隙法展开跨 360° 的障碍物序列
def _unwrap_angles(spans: list[ObstacleAngleSpan]) -> list[ObstacleAngleSpan]:
    if len(spans) <= 1:
        return spans

    sorted_spans = sorted(spans, key=lambda s: s.min_azimuth)
    gaps: list[tuple[float, int]] = []
    for i in range(len(sorted_spans) - 1):
        gap = sorted_spans[i + 1].min_azimuth - sorted_spans[i].max_azimuth
        gaps.append((gap, i))
    wrap_gap = (sorted_spans[0].min_azimuth + 360.0) - sorted_spans[-1].max_azimuth
    gaps.append((wrap_gap, len(sorted_spans) - 1))

    max_gap, max_gap_idx = max(gaps, key=lambda g: g[0])

    if max_gap_idx == len(sorted_spans) - 1:
        return sorted_spans

    unwrapped: list[ObstacleAngleSpan] = []
    for i, span in enumerate(sorted_spans):
        if i <= max_gap_idx:
            unwrapped.append(ObstacleAngleSpan(
                obstacle_id=span.obstacle_id,
                obstacle_name=span.obstacle_name,
                min_azimuth=span.min_azimuth + 360.0,
                max_azimuth=span.max_azimuth + 360.0,
            ))
        else:
            unwrapped.append(span)
    unwrapped.sort(key=lambda s: s.min_azimuth)
    return unwrapped


# 顺序合并重叠区间并返回累计角
def _merge_overlapping(spans: list[ObstacleAngleSpan]) -> tuple[float, float, list[AngleSnapshot]]:
    if not spans:
        return 0.0, 0.0, []

    start = spans[0].min_azimuth
    end = spans[0].max_azimuth
    cumulative = end - start
    snapshots: list[AngleSnapshot] = [AngleSnapshot(start=start, end=end, cumulative=cumulative)]

    for span in spans[1:]:
        if span.min_azimuth < end:
            if span.max_azimuth > end:
                cumulative += span.max_azimuth - end
                end = span.max_azimuth
                snapshots.append(AngleSnapshot(start=start, end=end, cumulative=cumulative))
        else:
            cumulative += span.max_azimuth - span.min_azimuth
            start = span.min_azimuth
            end = span.max_azimuth
            snapshots.append(AngleSnapshot(start=start, end=end, cumulative=cumulative))

    total_span = snapshots[-1].end - snapshots[0].start
    return total_span, cumulative, snapshots


# 扫描任意 sector_width 扇区内的最大累计水平遮蔽角
def _scan_sector(
    snapshots: list[AngleSnapshot],
    sector_width: float,
) -> float:
    max_acc = 0.0
    for i, base in enumerate(snapshots):
        window_start = base.start
        window_end = window_start + sector_width
        acc = 0.0
        for j in range(i, len(snapshots)):
            snap = snapshots[j]
            if snap.start >= window_end:
                break
            overlap_start = max(snap.start, window_start)
            overlap_end = min(snap.end, window_end)
            if overlap_end > overlap_start:
                acc += overlap_end - overlap_start
        max_acc = max(max_acc, acc)
    return max_acc


# 三级阈值判定
# 返回 (is_compliant, max_15_display, max_45_display)
def _evaluate_threshold(
    total_span: float,
    cumulative: float,
    snapshots: list[AngleSnapshot],
) -> tuple[bool, float, float]:
    max_15 = 0.0
    max_45 = 0.0

    if total_span < 15.0:
        ok = cumulative <= 1.5
        display = cumulative if total_span > 0 else 0.0
        return ok, display, display

    if cumulative <= 1.5:
        return True, cumulative, cumulative

    max_15 = _scan_sector(snapshots, 15.0)

    if max_15 <= 1.5:
        if total_span >= 45.0:
            max_45 = _scan_sector(snapshots, 45.0)
            return True, max_15, max_45
        else:
            return True, max_15, cumulative

    if total_span < 45.0:
        ok = cumulative <= 3.0
        return ok, max_15, cumulative

    max_45 = _scan_sector(snapshots, 45.0)
    ok = max_45 <= 3.0
    return ok, max_15, max_45


# 构建雷达累计水平遮蔽角结论文案
def _build_conclusion(
    max_15_display: float,
    max_45_display: float,
    station_name: str,
    obstacle_names: list[str],
) -> str:
    names_str = "、".join(obstacle_names)
    status_15 = "满足" if max_15_display <= 1.5 else "不满足"
    status_45 = "满足" if max_45_display <= 3.0 else "不满足"
    return (
        f"障碍物{names_str}相对于{station_name}的垂直遮蔽角超出0.25°,"
        f"任意15°方位范围内的最大累计水平遮蔽角为{max_15_display:.2f}°，"
        f"{status_15}\"不大于1.5°\"的标准要求；"
        f"任意45°方位范围内的最大累计水平遮蔽角为{max_45_display:.2f}°，"
        f"{status_45}\"不大于3.0°\"的标准要求。"
    )


# 计算所有 RADAR/场监雷达台站的累计水平遮蔽角结论
def compute_cumulative_horizontal_mask_angles(
    rule_results: list[dict[str, object]],
) -> list[dict[str, object]]:
    radar_station_spans: dict[int, dict[str, object]] = {}

    for r in rule_results:
        if not r.get("isApplicable", True):
            continue
        if r.get("ruleCode") != "radar_site_protection":
            continue
        metrics = r.get("metrics") or {}
        try:
            vertical = float(metrics.get("verticalMaskAngleDegrees", 0) or 0)
        except (TypeError, ValueError):
            vertical = 0.0
        if vertical <= 0.25:
            continue

        station_id = int(r["stationId"])
        if station_id not in radar_station_spans:
            radar_station_spans[station_id] = {
                "stationId": station_id,
                "stationName": str(r.get("stationName", "")),
                "stationType": str(r.get("stationType", "")),
                "spans": [],
            }
        min_az = float(r.get("minHorizontalAngleDegrees", 0) or 0)
        max_az = float(r.get("maxHorizontalAngleDegrees", 0) or 0)
        if min_az == max_az:
            continue
        obstacle_id = int(r["obstacleId"])
        obstacle_name = str(r.get("obstacleName", ""))
        if min_az > max_az:
            radar_station_spans[station_id]["spans"].append(
                ObstacleAngleSpan(
                    obstacle_id=obstacle_id,
                    obstacle_name=obstacle_name,
                    min_azimuth=min_az,
                    max_azimuth=360.0,
                )
            )
            radar_station_spans[station_id]["spans"].append(
                ObstacleAngleSpan(
                    obstacle_id=obstacle_id,
                    obstacle_name=obstacle_name,
                    min_azimuth=0.0,
                    max_azimuth=max_az,
                )
            )
        else:
            radar_station_spans[station_id]["spans"].append(
                ObstacleAngleSpan(
                    obstacle_id=obstacle_id,
                    obstacle_name=obstacle_name,
                    min_azimuth=min_az,
                    max_azimuth=max_az,
                )
            )

    results: list[dict[str, object]] = []
    for station_data in radar_station_spans.values():
        spans: list[ObstacleAngleSpan] = station_data["spans"]
        if not spans:
            continue

        if len(set(s.obstacle_id for s in spans)) <= 1:
            continue

        unwrapped = _unwrap_angles(spans)
        total_span, cumulative, snapshots = _merge_overlapping(unwrapped)
        is_compliant, max_15_display, max_45_display = _evaluate_threshold(
            total_span, cumulative, snapshots,
        )

        obstacle_names: list[str] = []
        seen_names: set[str] = set()
        for s in spans:
            if s.obstacle_name and s.obstacle_name not in seen_names:
                seen_names.add(s.obstacle_name)
                obstacle_names.append(s.obstacle_name)

        conclusion = _build_conclusion(
            max_15_display, max_45_display,
            str(station_data["stationName"]), obstacle_names,
        )

        clusters: list[dict[str, float]] = []
        for snap in snapshots:
            clusters.append({
                "startDegrees": round(snap.start % 360, 4),
                "endDegrees": round(snap.end % 360, 4),
                "cumulativeDegrees": round(snap.cumulative, 4),
            })

        results.append({
            "stationId": station_data["stationId"],
            "stationName": station_data["stationName"],
            "stationType": station_data["stationType"],
            "totalSpanDegrees": round(total_span, 2),
            "cumulativeHorizontalAngleDegrees": round(cumulative, 2),
            "maxCumulativeIn15Deg": round(max_15_display, 2),
            "maxCumulativeIn45Deg": round(max_45_display, 2),
            "isCompliant": "满足" if is_compliant else "不满足",
            "conclusion": conclusion,
            "clusters": clusters,
            "obstacleNames": obstacle_names,
        })

    return results
