from app.analysis.protection_zone_style import resolve_protection_zone_style


def test_resolve_protection_zone_style_returns_mapped_palette_item() -> None:
    style = resolve_protection_zone_style(
        zone_code="loc_building_restriction_zone",
        region_code="3",
    )

    assert style["colorKey"] == "danger_red"
    assert style["fill"].startswith("rgba(")
    assert style["stroke"].startswith("rgba(")


def test_resolve_protection_zone_style_returns_default_palette_item_when_mapping_missing() -> None:
    style = resolve_protection_zone_style(
        zone_code="missing_zone",
        region_code="missing_region",
    )

    assert style["colorKey"] == "default_blue"
    assert style["fill"] == "rgba(64, 158, 255, 0.25)"
    assert style["stroke"] == "rgba(64, 158, 255, 0.9)"


def test_resolve_protection_zone_style_explicitly_maps_all_current_protection_zones() -> None:
    current_zone_pairs = {
        ("ndb_minimum_distance_50m", "default"),
        ("ndb_minimum_distance_150m", "default"),
        ("ndb_minimum_distance_300m", "default"),
        ("ndb_minimum_distance_500m", "default"),
        ("ndb_conical_clearance_3deg", "default"),
        ("loc_site_protection", "default"),
        ("loc_forward_sector_3000m_15m", "default"),
        ("loc_run_area_protection", "A"),
        ("loc_run_area_protection", "B"),
        ("loc_run_area_protection", "C"),
        ("loc_run_area_protection", "D"),
        ("loc_building_restriction_zone", "1"),
        ("loc_building_restriction_zone", "2"),
        ("loc_building_restriction_zone", "3"),
        ("loc_building_restriction_zone", "4"),
        ("gp_site_protection_gb", "A"),
        ("gp_site_protection_gb", "B"),
        ("gp_site_protection_gb", "C"),
        ("gp_site_protection_mh", "A"),
        ("gp_site_protection_mh", "B"),
        ("gp_site_protection_mh", "C"),
    }

    resolved_color_keys = {
        (zone_code, region_code): resolve_protection_zone_style(
            zone_code=zone_code,
            region_code=region_code,
        )["colorKey"]
        for zone_code, region_code in current_zone_pairs
    }

    assert all(color_key != "default_blue" for color_key in resolved_color_keys.values())


def test_resolve_protection_zone_style_maps_loc_building_restriction_regions_to_stable_palette_keys() -> None:
    resolved_color_keys = {
        region_code: resolve_protection_zone_style(
            zone_code="loc_building_restriction_zone",
            region_code=region_code,
        )["colorKey"]
        for region_code in ("1", "2", "3", "4")
    }

    assert resolved_color_keys == {
        "1": "lime_green",
        "2": "lime_green",
        "3": "danger_red",
        "4": "cyan_blue",
    }


def test_resolve_protection_zone_style_assigns_distinct_colors_to_loc_run_area_regions() -> None:
    expected_color_keys = {
        "A": "sky_blue",
        "B": "teal_green",
        "C": "danger_red",
        "D": "amber_orange",
    }

    resolved_color_keys = {
        region_code: resolve_protection_zone_style(
            zone_code="loc_run_area_protection",
            region_code=region_code,
        )["colorKey"]
        for region_code in ("A", "B", "C", "D")
    }

    assert resolved_color_keys == expected_color_keys


def test_resolve_protection_zone_style_maps_gp_regions_with_shared_standard_colors() -> None:
    for region_code, expected_color_key in {
        "A": "sky_blue",
        "B": "teal_green",
        "C": "danger_red",
    }.items():
        gb_style = resolve_protection_zone_style(
            zone_code="gp_site_protection_gb",
            region_code=region_code,
        )
        mh_style = resolve_protection_zone_style(
            zone_code="gp_site_protection_mh",
            region_code=region_code,
        )

        assert gb_style["colorKey"] == expected_color_key
        assert mh_style["colorKey"] == expected_color_key
