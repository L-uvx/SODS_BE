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


def test_build_rule_standards_returns_shared_loc_building_restriction_mapping() -> None:
    standards = build_rule_standards(
        station_type="LOC",
        rule_name="loc_building_restriction_zone",
        region_code="3",
    )

    assert standards == AnalysisStandardSet(
        mh=AnalysisStandardReference(
            code="MH_ILSLOC_建筑物限制区_Ⅲ",
            text=(
                "航向信标台建筑物限制区：对于Ⅲ类运行或规划Ⅲ类运行的跑道，"
                "飞行区与建筑物限制区重叠范围内规划建设超过高度限制的机库、"
                "航站楼等大型建筑物，应采用计算机仿真的方式确定建筑物的尺寸；"
                "飞行区外的建筑物限制区范围内规划建设超过高度限制的民用设施等"
                "大型建筑物，宜采用计算机仿真的方式确定建筑物的尺寸。"
            ),
        ),
        gb=None,
    )


def test_build_rule_standards_returns_loc_run_area_critical_mapping() -> None:
    standards = build_rule_standards(
        station_type="LOC",
        rule_name="loc_run_area_protection_critical",
        region_code="C",
    )

    assert standards == AnalysisStandardSet(
        mh=AnalysisStandardReference(
            code="MH_ILSLOC_运行保护区_临界区",
            text=(
                "航向信标台运行保护区：实施Ⅰ/Ⅱ/Ⅲ类运行时，临界区内不应停放"
                "车辆、机械和航空器，不应有任何地面交通活动。"
            ),
        ),
        gb=None,
    )


def test_build_rule_standards_returns_loc_run_area_sensitive_mapping() -> None:
    standards = build_rule_standards(
        station_type="LOC",
        rule_name="loc_run_area_protection_sensitive",
        region_code="A",
    )

    assert standards == AnalysisStandardSet(
        mh=AnalysisStandardReference(
            code="MH_ILSLOC_运行保护区_敏感区",
            text=(
                "航向信标台运行保护区：车辆、航空器等移动物体未经许可不应进入"
                "相应类别的敏感区，跑道等待位置应位于敏感区外。"
            ),
        ),
        gb=None,
    )


def test_build_rule_standards_returns_gp_gb_region_a_mapping() -> None:
    standards = build_rule_standards(
        station_type="GP",
        rule_name="gp_site_protection_gb_region_a",
        region_code="A",
    )

    assert standards.gb == AnalysisStandardReference(
        code="GB_ILSGP_GB场地保护区_A",
        text=load_standard_config_entries()["GB_ILSGP_GB场地保护区_A"],
    )
    assert standards.mh is None


def test_build_rule_standards_returns_gp_mh_cable_region_a_mapping() -> None:
    standards = build_rule_standards(
        station_type="GP",
        rule_name="gp_site_protection_mh_region_a_cable",
        region_code="A",
    )

    assert standards.gb is None
    assert standards.mh == AnalysisStandardReference(
        code="MH_ILSGP_场地保护区_A线缆",
        text=load_standard_config_entries()["MH_ILSGP_场地保护区_A线缆"],
    )


def test_build_rule_standards_returns_gp_mh_region_b_by_station_sub_type() -> None:
    subtype_to_code = {
        "I": "MH_ILSGP_场地保护区_B_Ⅰ",
        "II": "MH_ILSGP_场地保护区_B_Ⅱ",
        "III": "MH_ILSGP_场地保护区_B_Ⅲ",
    }

    for station_sub_type, expected_code in subtype_to_code.items():
        standards = build_rule_standards(
            station_type="GP",
            rule_name=f"gp_site_protection_mh_region_b_{station_sub_type.lower()}",
            region_code="B",
        )

        assert standards.gb is None
        assert standards.mh == AnalysisStandardReference(
            code=expected_code,
            text=load_standard_config_entries()[expected_code],
        )


def test_standard_mappings_are_registered_by_station_type() -> None:
    assert "NDB" in _STANDARD_KEYS_BY_STATION_TYPE
    assert "LOC" in _STANDARD_KEYS_BY_STATION_TYPE
    assert "GP" in _STANDARD_KEYS_BY_STATION_TYPE
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
    assert (
        _STANDARD_KEYS_BY_STATION_TYPE["LOC"]["loc_building_restriction_zone"][0]
        is None
    )
    assert (
        _STANDARD_KEYS_BY_STATION_TYPE["LOC"]["loc_run_area_protection_critical"][0]
        is None
    )
    assert (
        _STANDARD_KEYS_BY_STATION_TYPE["LOC"]["loc_run_area_protection_critical"][1]
        == "MH_ILSLOC_运行保护区_临界区"
    )
    assert (
        _STANDARD_KEYS_BY_STATION_TYPE["LOC"]["loc_run_area_protection_sensitive"][0]
        is None
    )
    assert (
        _STANDARD_KEYS_BY_STATION_TYPE["LOC"]["loc_run_area_protection_sensitive"][1]
        == "MH_ILSLOC_运行保护区_敏感区"
    )
    assert (
        _STANDARD_KEYS_BY_STATION_TYPE["GP"]["gp_site_protection_gb_region_a"][0]
        == "GB_ILSGP_GB场地保护区_A"
    )
    assert (
        _STANDARD_KEYS_BY_STATION_TYPE["GP"]["gp_site_protection_mh_region_b_ii"][1]
        == "MH_ILSGP_场地保护区_B_Ⅱ"
    )
