from app.analysis.rules.loc.building_restriction.helpers import (
    LocBuildingRestrictionZoneRegion1Geometry,
    LocBuildingRestrictionZoneRegion2Geometry,
    LocBuildingRestrictionZoneRegion3AnalysisGeometry,
    LocBuildingRestrictionZoneRegion3Geometry,
    LocBuildingRestrictionZoneRegion4Geometry,
    LocBuildingRestrictionZoneSharedContext,
    build_loc_building_restriction_zone_region_1_geometry,
    build_loc_building_restriction_zone_region_2_geometry,
    build_loc_building_restriction_zone_region_3_geometry,
    build_loc_building_restriction_zone_region_4_geometry,
    build_loc_building_restriction_zone_shared_context,
    calculate_region_3_worst_allowed_height_meters,
)
from app.analysis.rules.loc.building_restriction.region_1 import (
    LocBuildingRestrictionZoneRegion1Rule,
)
from app.analysis.rules.loc.building_restriction.region_2 import (
    LocBuildingRestrictionZoneRegion2Rule,
)
from app.analysis.rules.loc.building_restriction.region_3 import (
    LocBuildingRestrictionZoneRegion3Rule,
)
from app.analysis.rules.loc.building_restriction.region_4 import (
    LocBuildingRestrictionZoneRegion4Rule,
)

SUPPORTED_CATEGORIES = {
    "building_general",
    "building_hangar",
    "building_terminal",
}

__all__ = [
    "LocBuildingRestrictionZoneRegion1Geometry",
    "LocBuildingRestrictionZoneRegion2Geometry",
    "LocBuildingRestrictionZoneRegion3AnalysisGeometry",
    "LocBuildingRestrictionZoneRegion3Geometry",
    "LocBuildingRestrictionZoneRegion4Geometry",
    "LocBuildingRestrictionZoneSharedContext",
    "build_loc_building_restriction_zone_region_1_geometry",
    "build_loc_building_restriction_zone_region_2_geometry",
    "build_loc_building_restriction_zone_region_3_geometry",
    "build_loc_building_restriction_zone_region_4_geometry",
    "build_loc_building_restriction_zone_shared_context",
    "calculate_region_3_worst_allowed_height_meters",
    "LocBuildingRestrictionZoneRegion1Rule",
    "LocBuildingRestrictionZoneRegion2Rule",
    "LocBuildingRestrictionZoneRegion3Rule",
    "LocBuildingRestrictionZoneRegion4Rule",
    "SUPPORTED_CATEGORIES",
]
