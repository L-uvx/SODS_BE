from app.analysis.rule_result import AnalysisRuleResult


def test_analysis_rule_result_stores_common_rule_fields() -> None:
    result = AnalysisRuleResult(
        station_id=1,
        station_type="NDB",
        obstacle_id=2,
        obstacle_name="Obstacle A",
        raw_obstacle_type="建筑物/构建物",
        global_obstacle_category="building_general",
        rule_name="ndb_minimum_distance_50m",
        zone_code="ndb_minimum_distance_50m",
        zone_name="NDB 50m minimum distance zone",
        region_code="default",
        region_name="default",
        zone_definition={"shape": "circle", "radius_m": 50.0},
        is_applicable=True,
        is_compliant=False,
        message="distance below required threshold",
        metrics={"actualDistanceMeters": 30.0, "requiredDistanceMeters": 50.0},
    )

    assert result.rule_name == "ndb_minimum_distance_50m"
    assert result.zone_code == "ndb_minimum_distance_50m"
    assert result.region_code == "default"
    assert result.zone_definition["shape"] == "circle"
    assert result.metrics["requiredDistanceMeters"] == 50.0
