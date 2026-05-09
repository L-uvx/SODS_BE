from app.analysis.standards import _LOC_STANDARD_KEYS


def _resolve_loc_standard_names(standards_rule_code: str) -> tuple[str, str]:
    gb_codes, mh_codes = _LOC_STANDARD_KEYS.get(standards_rule_code, ([], []))
    gb_name = gb_codes[0] if gb_codes else ""
    mh_name = mh_codes[0] if mh_codes else ""
    return gb_name, mh_name


def _join_loc_standard_names(gb_name: str, mh_name: str) -> str:
    if gb_name and mh_name:
        return f"{gb_name}和{mh_name}"
    if gb_name:
        return gb_name
    return mh_name
