import math
import pytest

from app.analysis.rules.radar.cumulative_analysis import (
    ObstacleAngleSpan,
    AngleSnapshot,
    _unwrap_angles,
    _merge_overlapping,
    _scan_sector,
    _evaluate_threshold,
    _build_conclusion,
    compute_cumulative_horizontal_mask_angles,
)


def _make_result(**overrides) -> dict[str, object]:
    defaults = {
        "stationId": 1,
        "stationName": "TEST_RADAR",
        "stationType": "RADAR",
        "ruleCode": "radar_site_protection",
        "isApplicable": True,
        "obstacleId": 1,
        "obstacleName": "obs1",
        "minHorizontalAngleDegrees": 0.0,
        "maxHorizontalAngleDegrees": 5.0,
        "metrics": {"verticalMaskAngleDegrees": 0.5},
    }
    result = dict(defaults)
    result.update(overrides)
    return result


class TestUnwrapAngles:
    def test_single_span_unchanged(self):
        spans = [ObstacleAngleSpan(1, "a", 10.0, 20.0)]
        assert _unwrap_angles(spans) == spans

    def test_empty_returns_empty(self):
        assert _unwrap_angles([]) == []

    def test_non_wrapping_no_change(self):
        spans = [
            ObstacleAngleSpan(1, "a", 10.0, 30.0),
            ObstacleAngleSpan(2, "b", 50.0, 70.0),
        ]
        result = _unwrap_angles(spans)
        assert len(result) == 2
        assert result[0].min_azimuth == 10.0
        assert result[1].min_azimuth == 50.0

    def test_wrap_near_zero(self):
        spans = [
            ObstacleAngleSpan(1, "a", 350.0, 355.0),
            ObstacleAngleSpan(2, "b", 5.0, 10.0),
        ]
        result = _unwrap_angles(spans)
        assert len(result) == 2
        assert result[0].max_azimuth < result[1].min_azimuth
        assert result[0].min_azimuth < 360.0
        assert result[1].min_azimuth > 360.0

    def test_wrap_three_clusters(self):
        spans = [
            ObstacleAngleSpan(1, "a", 10.0, 20.0),
            ObstacleAngleSpan(2, "b", 100.0, 110.0),
            ObstacleAngleSpan(3, "c", 340.0, 350.0),
        ]
        result = _unwrap_angles(spans)
        assert len(result) == 3
        assert all(r.min_azimuth >= result[0].min_azimuth for r in result[1:])


class TestMergeOverlapping:
    def test_empty(self):
        span, cumulative, snaps = _merge_overlapping([])
        assert span == 0.0
        assert cumulative == 0.0
        assert snaps == []

    def test_single(self):
        spans = [ObstacleAngleSpan(1, "a", 10.0, 30.0)]
        span, cumulative, snaps = _merge_overlapping(spans)
        assert span == pytest.approx(20.0)
        assert cumulative == pytest.approx(20.0)
        assert len(snaps) == 1

    def test_non_overlapping(self):
        spans = [
            ObstacleAngleSpan(1, "a", 10.0, 20.0),
            ObstacleAngleSpan(2, "b", 30.0, 45.0),
        ]
        span, cumulative, snaps = _merge_overlapping(spans)
        assert span == pytest.approx(35.0)
        assert cumulative == pytest.approx(25.0)

    def test_overlapping_extend(self):
        spans = [
            ObstacleAngleSpan(1, "a", 10.0, 25.0),
            ObstacleAngleSpan(2, "b", 20.0, 35.0),
        ]
        span, cumulative, snaps = _merge_overlapping(spans)
        assert span == pytest.approx(25.0)
        assert cumulative == pytest.approx(25.0)

    def test_contained(self):
        spans = [
            ObstacleAngleSpan(1, "a", 10.0, 50.0),
            ObstacleAngleSpan(2, "b", 20.0, 30.0),
        ]
        span, cumulative, snaps = _merge_overlapping(spans)
        assert span == pytest.approx(40.0)
        assert cumulative == pytest.approx(40.0)

    def test_contained_not_double_counted(self):
        spans = [
            ObstacleAngleSpan(1, "a", 10.0, 50.0),
            ObstacleAngleSpan(2, "b", 20.0, 30.0),
        ]
        _, _, snaps = _merge_overlapping(spans)
        assert len(snaps) == 1
        assert snaps[0].cumulative == pytest.approx(40.0)

    def test_three_with_partial_overlap(self):
        spans = [
            ObstacleAngleSpan(1, "a", 10.0, 20.0),
            ObstacleAngleSpan(2, "b", 15.0, 30.0),
            ObstacleAngleSpan(3, "c", 40.0, 50.0),
        ]
        span, cumulative, snaps = _merge_overlapping(spans)
        assert span == pytest.approx(40.0)
        assert cumulative == pytest.approx(30.0)


class TestScanSector:
    def test_single_snapshot(self):
        snaps = [AngleSnapshot(start=10.0, end=20.0, cumulative=10.0)]
        result = _scan_sector(snaps, 15.0)
        assert result == pytest.approx(10.0)

    def test_two_non_overlapping_in_window(self):
        snaps = [
            AngleSnapshot(start=10.0, end=18.0, cumulative=8.0),
            AngleSnapshot(start=20.0, end=25.0, cumulative=13.0),
        ]
        result = _scan_sector(snaps, 15.0)
        assert result == pytest.approx(13.0)

    def test_outside_window_not_counted(self):
        snaps = [
            AngleSnapshot(start=10.0, end=12.0, cumulative=2.0),
            AngleSnapshot(start=30.0, end=40.0, cumulative=12.0),
        ]
        result = _scan_sector(snaps, 15.0)
        assert result == pytest.approx(10.0)

    def test_partial_overlap(self):
        snaps = [
            AngleSnapshot(start=10.0, end=25.0, cumulative=15.0),
        ]
        result = _scan_sector(snaps, 12.0)
        assert result == pytest.approx(12.0)


class TestEvaluateThreshold:
    def test_small_span_compliant(self):
        ok, max_15_d, max_45_d = _evaluate_threshold(10.0, 1.0, [])
        assert ok is True
        assert max_15_d == 1.0
        assert max_45_d == 1.0

    def test_small_span_not_compliant(self):
        ok, max_15_d, max_45_d = _evaluate_threshold(10.0, 2.0, [])
        assert ok is False
        assert max_15_d == 2.0
        assert max_45_d == 2.0

    def test_large_span_low_cumulative(self):
        ok, max_15_d, max_45_d = _evaluate_threshold(20.0, 1.0, [])
        assert ok is True
        assert max_15_d == 1.0
        assert max_45_d == 1.0

    def test_large_span_high_cumulative_scan_15_passes(self):
        snaps = [
            AngleSnapshot(start=10.0, end=10.5, cumulative=0.5),
        ]
        ok, max_15_d, max_45_d = _evaluate_threshold(20.0, 3.0, snaps)
        assert ok is True
        assert max_15_d <= 1.5
        assert max_45_d == 3.0

    def test_large_span_scan_15_fails_span_under_45(self):
        snaps = [
            AngleSnapshot(start=10.0, end=22.0, cumulative=12.0),
            AngleSnapshot(start=22.0, end=34.0, cumulative=24.0),
        ]
        ok, max_15_d, max_45_d = _evaluate_threshold(30.0, 4.0, snaps)
        assert ok is False
        assert max_15_d > 1.5
        assert max_45_d == 4.0

    def test_large_span_scan_45(self):
        snaps = [
            AngleSnapshot(start=10.0, end=22.0, cumulative=12.0),
            AngleSnapshot(start=22.0, end=34.0, cumulative=24.0),
            AngleSnapshot(start=40.0, end=60.0, cumulative=44.0),
        ]
        ok, max_15_d, max_45_d = _evaluate_threshold(50.0, 4.0, snaps)
        assert ok is False
        assert max_15_d > 1.5
        assert max_45_d > 3.0


class TestEndToEnd:
    def test_empty_results(self):
        results = compute_cumulative_horizontal_mask_angles([])
        assert results == []

    def test_no_radar_results(self):
        results = compute_cumulative_horizontal_mask_angles([
            _make_result(ruleCode="ndb_conical_clearance_3deg"),
        ])
        assert results == []

    def test_vertical_below_threshold_skipped(self):
        results = compute_cumulative_horizontal_mask_angles([
            _make_result(metrics={"verticalMaskAngleDegrees": 0.1}),
        ])
        assert results == []

    def test_not_applicable_skipped(self):
        results = compute_cumulative_horizontal_mask_angles([
            _make_result(isApplicable=False),
        ])
        assert results == []

    def test_single_obstacle_excluded(self):
        results = compute_cumulative_horizontal_mask_angles([
            _make_result(
                metrics={"verticalMaskAngleDegrees": 0.5},
                minHorizontalAngleDegrees=10.0,
                maxHorizontalAngleDegrees=11.0,
            ),
        ])
        assert results == []

    def test_two_unique_obstacles_included(self):
        results = compute_cumulative_horizontal_mask_angles([
            _make_result(
                obstacleId=1,
                obstacleName="obs1",
                metrics={"verticalMaskAngleDegrees": 0.5},
                minHorizontalAngleDegrees=10.0,
                maxHorizontalAngleDegrees=20.0,
            ),
            _make_result(
                obstacleId=2,
                obstacleName="obs2",
                minHorizontalAngleDegrees=30.0,
                maxHorizontalAngleDegrees=35.0,
            ),
        ])
        assert len(results) == 1
        assert sorted(results[0]["obstacleNames"]) == ["obs1", "obs2"]

    def test_single_obstacle_crossing_360_excluded(self):
        results = compute_cumulative_horizontal_mask_angles([
            _make_result(
                minHorizontalAngleDegrees=350.0,
                maxHorizontalAngleDegrees=10.0,
            ),
        ])
        assert results == []

    def test_mixed_stations_one_excluded_one_included(self):
        results = compute_cumulative_horizontal_mask_angles([
            _make_result(
                stationId=1,
                stationName="Radar_A",
                obstacleId=1,
                minHorizontalAngleDegrees=10.0,
                maxHorizontalAngleDegrees=20.0,
            ),
            _make_result(
                stationId=2,
                stationName="Radar_B",
                obstacleId=2,
                minHorizontalAngleDegrees=30.0,
                maxHorizontalAngleDegrees=35.0,
            ),
            _make_result(
                stationId=2,
                stationName="Radar_B",
                obstacleId=3,
                minHorizontalAngleDegrees=50.0,
                maxHorizontalAngleDegrees=55.0,
            ),
        ])
        assert len(results) == 1
        assert results[0]["stationName"] == "Radar_B"

    def test_wrap_merges_correctly(self):
        results = compute_cumulative_horizontal_mask_angles([
            _make_result(
                obstacleId=1,
                minHorizontalAngleDegrees=350.0,
                maxHorizontalAngleDegrees=355.0,
            ),
            _make_result(
                obstacleId=2,
                obstacleName="obs2",
                minHorizontalAngleDegrees=5.0,
                maxHorizontalAngleDegrees=10.0,
            ),
        ])
        assert len(results) == 1
        assert results[0]["cumulativeHorizontalAngleDegrees"] == pytest.approx(10.0)

    def test_missing_metrics_defaults_to_zero(self):
        results = compute_cumulative_horizontal_mask_angles([
            _make_result(metrics={}),
        ])
        assert results == []

    def test_missing_angles_defaults_to_zero(self):
        results = compute_cumulative_horizontal_mask_angles([
            _make_result(
                minHorizontalAngleDegrees=None,
                maxHorizontalAngleDegrees=None,
            ),
        ])
        assert results == []

    def test_field_monitor_radar_included(self):
        results = compute_cumulative_horizontal_mask_angles([
            _make_result(
                stationType="Surface_Detection_Radar",
                obstacleId=1,
                minHorizontalAngleDegrees=10.0,
                maxHorizontalAngleDegrees=20.0,
            ),
            _make_result(
                stationType="Surface_Detection_Radar",
                obstacleId=2,
                minHorizontalAngleDegrees=30.0,
                maxHorizontalAngleDegrees=35.0,
            ),
        ])
        assert len(results) == 1
        assert results[0]["stationType"] == "Surface_Detection_Radar"

    def test_obstacle_names_deduplicated(self):
        results = compute_cumulative_horizontal_mask_angles([
            _make_result(
                obstacleId=1,
                obstacleName="obs_a",
                minHorizontalAngleDegrees=10.0,
                maxHorizontalAngleDegrees=20.0,
            ),
            _make_result(
                obstacleId=1,
                obstacleName="obs_a",
                minHorizontalAngleDegrees=15.0,
                maxHorizontalAngleDegrees=25.0,
            ),
            _make_result(
                obstacleId=2,
                obstacleName="obs_b",
                minHorizontalAngleDegrees=40.0,
                maxHorizontalAngleDegrees=50.0,
            ),
        ])
        assert len(results) == 1
        assert "obstacleNames" in results[0]
        assert sorted(results[0]["obstacleNames"]) == ["obs_a", "obs_b"]

    def test_obstacle_names_empty_when_no_spans(self):
        results = compute_cumulative_horizontal_mask_angles([
            _make_result(
                minHorizontalAngleDegrees=None,
                maxHorizontalAngleDegrees=None,
                metrics={"verticalMaskAngleDegrees": 0.5},
            ),
        ])
        assert results == []


class TestBuildConclusion:
    def test_compliant_all_within_limits(self):
        result = _build_conclusion(
            0.8, 1.2, "RADAR_01", ["obs1", "obs2"],
        )
        assert "RADAR_01" in result
        assert "obs1、obs2" in result
        assert "满足\"不大于1.5°\"" in result
        assert "满足\"不大于3.0°\"" in result
        assert "0.80°" in result
        assert "1.20°" in result

    def test_15deg_not_compliant(self):
        result = _build_conclusion(
            2.0, 1.0, "RADAR_01", ["obs_a"],
        )
        assert "不满足\"不大于1.5°\"" in result
        assert "满足\"不大于3.0°\"" in result

    def test_45deg_not_compliant(self):
        result = _build_conclusion(
            1.0, 4.5, "RADAR_01", ["obs_a"],
        )
        assert "满足\"不大于1.5°\"" in result
        assert "不满足\"不大于3.0°\"" in result

    def test_both_not_compliant(self):
        result = _build_conclusion(
            3.0, 5.0, "RADAR_01", ["obs_a"],
        )
        assert "不满足\"不大于1.5°\"" in result
        assert "不满足\"不大于3.0°\"" in result

    def test_always_both_dims_mentioned(self):
        result = _build_conclusion(
            0.5, 2.5, "STN", ["o1"],
        )
        assert "任意15°方位范围" in result
        assert "任意45°方位范围" in result
        assert "1.5°" in result
        assert "3.0°" in result

    def test_station_name_included(self):
        result = _build_conclusion(
            0.5, 0.5, "TEST_RADAR", ["obs1"],
        )
        assert "相对于TEST_RADAR的垂直遮蔽角" in result


class TestEndToEndFormat:
    def test_single_obstacle_conclusion_csharp_format(self):
        results = compute_cumulative_horizontal_mask_angles([
            _make_result(
                obstacleId=1,
                obstacleName="Alpha_Tower",
                stationName="RADAR_A",
                metrics={"verticalMaskAngleDegrees": 0.5},
                minHorizontalAngleDegrees=10.0,
                maxHorizontalAngleDegrees=11.0,
            ),
            _make_result(
                obstacleId=2,
                obstacleName="Beta_Tower",
                stationName="RADAR_A",
                metrics={"verticalMaskAngleDegrees": 0.5},
                minHorizontalAngleDegrees=15.0,
                maxHorizontalAngleDegrees=20.0,
            ),
        ])
        assert len(results) == 1
        conclusion = results[0]["conclusion"]
        assert "Alpha_Tower" in conclusion
        assert "Beta_Tower" in conclusion
        assert "RADAR_A" in conclusion
        assert "任意15°方位范围" in conclusion
        assert "任意45°方位范围" in conclusion
        assert "不大于1.5°" in conclusion
        assert "不大于3.0°" in conclusion

    def test_two_obstacles_conclusion_csharp_format(self):
        results = compute_cumulative_horizontal_mask_angles([
            _make_result(
                obstacleId=1,
                obstacleName="Tower_A",
                stationName="RADAR_X",
                minHorizontalAngleDegrees=10.0,
                maxHorizontalAngleDegrees=20.0,
            ),
            _make_result(
                obstacleId=2,
                obstacleName="Tower_B",
                stationName="RADAR_X",
                minHorizontalAngleDegrees=30.0,
                maxHorizontalAngleDegrees=35.0,
            ),
        ])
        assert len(results) == 1
        conclusion = results[0]["conclusion"]
        assert "Tower_A、Tower_B" in conclusion
        assert "相对于RADAR_X" in conclusion

    def test_conclusion_always_mentions_both_15_and_45(self):
        results = compute_cumulative_horizontal_mask_angles([
            _make_result(
                obstacleId=1,
                metrics={"verticalMaskAngleDegrees": 0.5},
                minHorizontalAngleDegrees=10.0,
                maxHorizontalAngleDegrees=25.0,
            ),
            _make_result(
                obstacleId=2,
                metrics={"verticalMaskAngleDegrees": 0.5},
                minHorizontalAngleDegrees=50.0,
                maxHorizontalAngleDegrees=55.0,
            ),
        ])
        assert len(results) == 1
        conclusion = results[0]["conclusion"]
        assert "任意15°方位范围" in conclusion
        assert "任意45°方位范围" in conclusion
