from app.analysis.rule_result import AnalysisRuleResult


def test_analysis_rule_result_stores_common_rule_fields() -> None:
    result = AnalysisRuleResult(
        station_id=1,
        station_type="NDB",
        obstacle_id=2,
        obstacle_name="Obstacle A",
        raw_obstacle_type="建筑物/构建物",
        global_obstacle_category="building_general",
        rule_code="ndb_minimum_distance_50m",
        rule_name="ndb_minimum_distance_50m",
        zone_code="ndb_minimum_distance_50m",
        zone_name="NDB 50m minimum distance zone",
        region_code="default",
        region_name="default",
        is_applicable=True,
        is_compliant=False,
        message="位于NDB 50米最小间距区域内",
        metrics={"actualDistanceMeters": 30.0, "minimumDistanceMeters": 50.0},
        standards_rule_code="ndb_minimum_distance_50m",
    )

    assert result.rule_code == "ndb_minimum_distance_50m"
    assert result.rule_name == "ndb_minimum_distance_50m"
    assert result.zone_code == "ndb_minimum_distance_50m"
    assert result.region_code == "default"
    assert result.standards_rule_code == "ndb_minimum_distance_50m"
    assert result.metrics["minimumDistanceMeters"] == 50.0
