import math
from dataclasses import dataclass, field


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


@dataclass
class StationCumulativeResult:
    station_id: int
    station_name: str
    station_type: str
    total_span_degrees: float
    cumulative_horizontal_angle_degrees: float
    max_cumulative_in_15_deg: float
    max_cumulative_in_45_deg: float
    is_compliant: bool
    conclusion: str
    clusters: list[dict[str, float]] = field(default_factory=list)


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
def _evaluate_threshold(
    total_span: float,
    cumulative: float,
    snapshots: list[AngleSnapshot],
) -> tuple[bool, str, float, float]:
    max_15 = 0.0
    max_45 = 0.0

    if total_span < 15.0:
        ok = cumulative <= 1.5
        conclusion = (
            f"障碍物群总夹角{total_span:.1f}°<15°，累计水平遮蔽角{cumulative:.1f}°"
            f"{'≤' if ok else '>'}1.5°，{'满足' if ok else '不满足'}标准限值要求。"
        )
        return ok, conclusion, cumulative if total_span > 0 else 0.0, 0.0

    if cumulative <= 1.5:
        conclusion = (
            f"障碍物群总夹角{total_span:.1f}°≥15°，累计水平遮蔽角{cumulative:.1f}°"
            f"≤1.5°，满足标准限值要求。"
        )
        return True, conclusion, 0.0, 0.0

    max_15 = _scan_sector(snapshots, 15.0)

    if max_15 <= 1.5:
        conclusion = (
            f"障碍物群总夹角{total_span:.1f}°≥15°，累计水平遮蔽角{cumulative:.1f}°>1.5°，"
            f"但在任意15°扇区内未超出1.5°，满足标准限值要求。"
        )
        return True, conclusion, max_15, 0.0

    if total_span < 45.0:
        ok = cumulative <= 3.0
        conclusion = (
            f"障碍物群总夹角{total_span:.1f}°<45°，在任意15°扇区内超出1.5°"
            f"（最大{max_15:.2f}°），累计水平遮蔽角{cumulative:.1f}°"
            f"{'≤' if ok else '>'}3°，{'满足' if ok else '不满足'}标准限值要求。"
        )
        return ok, conclusion, max_15, 0.0

    max_45 = _scan_sector(snapshots, 45.0)
    ok = max_45 <= 3.0
    conclusion = (
        f"障碍物群总夹角{total_span:.1f}°≥45°，在任意15°扇区内超出1.5°"
        f"（最大{max_15:.2f}°），在任意45°扇区内{'未超出' if ok else '超出'}3°"
        f"（最大{max_45:.2f}°），{'满足' if ok else '不满足'}标准限值要求。"
    )
    return ok, conclusion, max_15, max_45


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
        radar_station_spans[station_id]["spans"].append(
            ObstacleAngleSpan(
                obstacle_id=int(r["obstacleId"]),
                obstacle_name=str(r.get("obstacleName", "")),
                min_azimuth=float(r.get("minHorizontalAngleDegrees", 0) or 0),
                max_azimuth=float(r.get("maxHorizontalAngleDegrees", 0) or 0),
            )
        )

    results: list[dict[str, object]] = []
    for station_data in radar_station_spans.values():
        spans: list[ObstacleAngleSpan] = station_data["spans"]
        if not spans:
            continue

        unwrapped = _unwrap_angles(spans)
        total_span, cumulative, snapshots = _merge_overlapping(unwrapped)
        is_compliant, conclusion, max_15, max_45 = _evaluate_threshold(
            total_span, cumulative, snapshots,
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
            "maxCumulativeIn15Deg": round(max_15, 2),
            "maxCumulativeIn45Deg": round(max_45, 2),
            "isCompliant": is_compliant,
            "conclusion": conclusion,
            "clusters": clusters,
        })

    return results
