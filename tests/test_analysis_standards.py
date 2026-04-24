from app.analysis.standards import (
    _STANDARD_KEYS_BY_STATION_TYPE,
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


def test_standard_mappings_are_registered_by_station_type() -> None:
    assert "NDB" in _STANDARD_KEYS_BY_STATION_TYPE
    assert "LOC" in _STANDARD_KEYS_BY_STATION_TYPE
    assert (
        _STANDARD_KEYS_BY_STATION_TYPE["NDB"]["ndb_minimum_distance_50m"][0]
        == "GB_NDB_50m最小间距区域_50"
    )
    assert (
        _STANDARD_KEYS_BY_STATION_TYPE["LOC"]["loc_site_protection"][0]
        == "GB_ILSLOC_场地保护区"
    )
    assert (
        _STANDARD_KEYS_BY_STATION_TYPE["LOC"]["loc_forward_sector_3000m_15m"][0]
        == "GB_ILSLOC_前向正负10°，3000米区域"
    )
