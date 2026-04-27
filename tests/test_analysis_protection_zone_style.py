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
        ("loc_building_restriction_zone", "1"),
        ("loc_building_restriction_zone", "2"),
        ("loc_building_restriction_zone", "3"),
        ("loc_building_restriction_zone", "4"),
    }

    mapped_color_keys = {
        resolve_protection_zone_style(zone_code=zone_code, region_code=region_code)[
            "colorKey"
        ]
        for zone_code, region_code in current_zone_pairs
    }

    assert len(mapped_color_keys) == len(current_zone_pairs)


def test_resolve_protection_zone_style_assigns_distinct_colors_to_loc_building_restriction_regions() -> None:
    color_keys = {
        resolve_protection_zone_style(
            zone_code="loc_building_restriction_zone",
            region_code=region_code,
        )["colorKey"]
        for region_code in ("1", "2", "3", "4")
    }

    assert len(color_keys) == 4
