from app.analysis.rules.ndb.common import NdbRule


class NdbMinimumDistance300mRule(NdbRule):
    rule_name = "ndb_minimum_distance_300m"
    zone_name = "NDB 300m minimum distance zone"
    zone_definition = {"shape": "circle", "radius_m": 300.0}
