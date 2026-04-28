from collections.abc import Mapping


# 计算 GP 净空限高，当前仅提供共享入口。
def calculate_gp_clearance_limit_height_meters(
    *,
    runway_context: Mapping[str, object],
    obstacle: Mapping[str, object],
) -> float | None:
    _ = runway_context
    _ = obstacle
    return None


__all__ = ["calculate_gp_clearance_limit_height_meters"]
