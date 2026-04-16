from app.analysis.rules.ndb.common import NdbRule


class NdbConicalClearance3DegRule(NdbRule):
    rule_name = "ndb_conical_clearance_3deg"
    zone_name = "NDB 3 degree conical clearance zone"
    zone_definition = {
        "shape": "radial_band",
        "min_radius_m": 50.0,
        "max_radius_m": 37040.0,
        "vertical_angle_deg": 3.0,
    }
