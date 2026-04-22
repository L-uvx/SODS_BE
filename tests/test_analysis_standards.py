from app.analysis.standards import (
    AnalysisStandardReference,
    AnalysisStandardSet,
    build_rule_standards,
    load_standard_config_entries,
)


def test_load_standard_config_entries_reads_known_ndb_keys() -> None:
    entries = load_standard_config_entries()

    assert entries["GB_NDB_50m最小间距区域_50"].startswith(
        "无方向信标天线与地形地物之间的最小间距"
    )
    assert entries["MH_NDB_50米以外仰角区域"].startswith(
        "在无方向信标天线50m以外"
    )


def test_build_rule_standards_returns_gb_and_mh_for_ndb_rule() -> None:
    standards = build_rule_standards(
        station_type="NDB",
        rule_name="ndb_minimum_distance_50m",
        region_code="default",
    )

    assert standards == AnalysisStandardSet(
        gb=AnalysisStandardReference(
            code="GB_NDB_50m最小间距区域_50",
            text=(
                "无方向信标天线与地形地物之间的最小间距：高于3m的树木、建筑物"
                "（机房除外）以及公路与台站最小允许间距50m。"
            ),
        ),
        mh=AnalysisStandardReference(
            code="MH_NDB_50m最小间距区域_50",
            text=(
                "无方向信标天线与地形地物之间的最小间距：建筑物（机房除外）、"
                "公路以及高于3m的树木与台站最小允许间距50m。"
            ),
        ),
    )


def test_build_rule_standards_returns_none_for_missing_mapping() -> None:
    standards = build_rule_standards(
        station_type="NDB",
        rule_name="missing_rule",
        region_code="default",
    )

    assert standards.gb is None
    assert standards.mh is None
