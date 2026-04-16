from app.analysis.rules.ndb.common import NdbRule


class NdbMinimumDistance150mRule(NdbRule):
    rule_name = "ndb_minimum_distance_150m"
    zone_name = "NDB 150m minimum distance zone"
    zone_definition = {"shape": "circle", "radius_m": 150.0}
