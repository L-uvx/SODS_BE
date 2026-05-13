# 按台站跑道号匹配跑道上下文（LOC / GP / MB 共用）。
def resolve_runway_context(
    *,
    station: object,
    runways: list[dict[str, object]],
) -> dict[str, object] | None:
    runway_no = getattr(station, "runway_no", None)
    if runway_no is None:
        return None

    for runway in runways:
        if runway.get("runNumber") == runway_no:
            return runway
    return None
