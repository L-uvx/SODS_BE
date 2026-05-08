from app.analysis.protection_zone_style import (
    resolve_protection_zone_name,
    resolve_protection_zone_style,
)


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
    assert style["fill"] == "rgba(64, 158, 255, 0.5)"
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
        ("radar_site_protection", "default"),
        ("radar_minimum_distance_zone_460m", "default"),
        ("radar_minimum_distance_zone_500m", "default"),
        ("radar_minimum_distance_zone_700m", "default"),
        ("radar_minimum_distance_zone_800m", "default"),
        ("radar_minimum_distance_zone_930m", "default"),
        ("radar_minimum_distance_zone_1000m", "default"),
        ("radar_minimum_distance_zone_1200m", "default"),
        ("radar_minimum_distance_zone_1610m", "default"),
        ("radar_rotating_reflector_zone_16km", "default"),
        ("surface_detection_radar_runway_triangle", "default"),
        ("vor_reflector_mask_area", "default"),
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


def test_resolve_protection_zone_name_returns_configured_chinese_names() -> None:
    assert (
        resolve_protection_zone_name(zone_code="ndb_minimum_distance_50m")
        == "NDB 50米最小间距"
    )
    assert (
        resolve_protection_zone_name(zone_code="loc_run_area_protection")
        == "LOC 运行保护区"
    )
    assert (
        resolve_protection_zone_name(zone_code="gp_site_protection_gb")
        == "GP 场地保护区（GB）"
    )
    assert (
        resolve_protection_zone_name(zone_code="weather_radar_elevation_angle_1deg")
        == "天气雷达 1°仰角限制区域"
    )
    assert (
        resolve_protection_zone_name(zone_code="wind_radar_elevation_angle_15deg")
        == "风温雷达 15°仰角限制区域"
    )


def test_resolve_protection_zone_style_maps_radar_zones_to_stable_palette_keys() -> None:
    assert resolve_protection_zone_style(
        zone_code="radar_minimum_distance_zone_460m",
        region_code="default",
    )["colorKey"] == "sky_blue"
    assert resolve_protection_zone_style(
        zone_code="radar_minimum_distance_zone_1610m",
        region_code="default",
    )["colorKey"] == "slate_gray"
    assert resolve_protection_zone_style(
        zone_code="radar_rotating_reflector_zone_16km",
        region_code="default",
    )["colorKey"] == "danger_red"


def test_resolve_protection_zone_name_returns_radar_zone_names() -> None:
    assert (
        resolve_protection_zone_name(zone_code="radar_site_protection")
        == "Radar 场地保护区"
    )
    assert (
        resolve_protection_zone_name(zone_code="radar_minimum_distance_zone_460m")
        == "Radar 460米最小间距"
    )
    assert (
        resolve_protection_zone_name(zone_code="radar_rotating_reflector_zone_16km")
        == "Radar 16公里保护区"
    )
    assert (
        resolve_protection_zone_name(zone_code="surface_detection_radar_runway_triangle")
        == "场监雷达跑道三角区域"
    )


def test_resolve_protection_zone_style_maps_weather_and_wind_radar_zones() -> None:
    assert resolve_protection_zone_style(
        zone_code="weather_radar_minimum_distance_450m",
        region_code="default",
    )["colorKey"] != "default_blue"
    assert resolve_protection_zone_style(
        zone_code="weather_radar_minimum_distance_800m",
        region_code="default",
    )["colorKey"] != "default_blue"
    assert resolve_protection_zone_style(
        zone_code="weather_radar_elevation_angle_1deg",
        region_code="default",
    )["colorKey"] != "default_blue"
    assert resolve_protection_zone_style(
        zone_code="wind_radar_elevation_angle_15deg",
        region_code="default",
    )["colorKey"] != "default_blue"


def test_resolve_protection_zone_style_returns_radar_a_style() -> None:
    style = resolve_protection_zone_style(
        zone_code="radar_site_protection",
        region_code="default",
    )

    assert style["colorKey"] == "violet_purple"
    assert style["fill"] == "rgba(167, 139, 250, 0.5)"
    assert style["stroke"] == "rgba(167, 139, 250, 0.9)"


def test_resolve_protection_zone_style_returns_surface_detection_radar_triangle_style() -> None:
    style = resolve_protection_zone_style(
        zone_code="surface_detection_radar_runway_triangle",
        region_code="default",
    )

    assert style["colorKey"] == "pink_rose"
    assert style["fill"] == "rgba(244, 114, 182, 0.5)"
    assert style["stroke"] == "rgba(244, 114, 182, 0.9)"


def test_resolve_protection_zone_name_returns_ads_b_zone_names() -> None:
    assert (
        resolve_protection_zone_name(zone_code="adsb_minimum_distance_0_5km")
        == "ADS-B 0.5km最小间距"
    )
    assert (
        resolve_protection_zone_name(zone_code="adsb_minimum_distance_1_2km")
        == "ADS-B 1.2km最小间距"
    )


def test_resolve_protection_zone_style_maps_ads_b_zones_to_explicit_palette_keys() -> None:
    expected_color_keys = {
        "adsb_minimum_distance_0_5km": "sky_blue",
        "adsb_minimum_distance_0_7km": "teal_green",
        "adsb_minimum_distance_0_8km": "amber_orange",
        "adsb_minimum_distance_1km": "violet_purple",
        "adsb_minimum_distance_1_2km": "danger_red",
    }

    resolved_color_keys = {
        zone_code: resolve_protection_zone_style(
            zone_code=zone_code,
            region_code="default",
        )["colorKey"]
        for zone_code in expected_color_keys
    }

    assert resolved_color_keys == expected_color_keys
