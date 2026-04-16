from app.analysis.rules.ndb.common import NdbRule


class NdbMinimumDistance500mRule(NdbRule):
    rule_name = "ndb_minimum_distance_500m"
    zone_name = "NDB 500m minimum distance zone"
    zone_definition = {"shape": "circle", "radius_m": 500.0}
