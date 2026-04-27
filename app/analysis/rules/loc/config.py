LOC_SITE_PROTECTION = {
    "circle_radius_m": 75.0,
    "rectangle_width_m": 120.0,
    "minimum_rectangle_length_m": 300.0,
}

LOC_FORWARD_SECTOR_3000M_15M = {
    "radius_m": 3000.0,
    "half_angle_degrees": 10.0,
    "height_limit_offset_m": 15.0,
}

LOC_BUILDING_RESTRICTION_ZONE = {
    "zone_code": "loc_building_restriction_zone",
    "zone_name": "building restriction zone",
    "root_half_width_m": 500.0,
    "region_1_2_forward_length_m": 500.0,
    "region_1_2_outer_offset_m": 1500.0,
    "region_1_2_side_angle_degrees": 20.0,
    "region_1_2_height_offset_m": 20.0,
    "region_4_side_offset_m": 500.0,
    "region_4_backward_length_m": 500.0,
    "arc_radius_offset_m": 6000.0,
    "arc_height_offset_m": 70.0,
    "base_angle_degrees": 20.0,
    "region_codes": ("1", "2", "3", "4"),
}
