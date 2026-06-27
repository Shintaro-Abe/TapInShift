from __future__ import annotations

from datetime import datetime, timedelta


SUPPORTED_ROUNDING_MINUTES = {5, 10, 15, 20, 30}
SUPPORTED_ROUNDING_MODES = {"none"} | {f"{minutes}m" for minutes in SUPPORTED_ROUNDING_MINUTES}


def round_time(value: datetime, mode: str = "none", direction: str = "nearest") -> datetime:
    """Round a timestamp while preserving timezone info.

    mode accepts "none" or values such as "15m" and "30m".
    direction accepts "nearest", "floor", or "ceil".
    """
    if mode == "none":
        return value

    minutes = _parse_mode(mode)
    if direction not in {"nearest", "floor", "ceil"}:
        raise ValueError(f"Unsupported rounding direction: {direction}")

    day_start = value.replace(hour=0, minute=0, second=0, microsecond=0)
    elapsed_seconds = int((value - day_start).total_seconds())
    step_seconds = minutes * 60

    if direction == "floor":
        rounded_seconds = (elapsed_seconds // step_seconds) * step_seconds
    elif direction == "ceil":
        rounded_seconds = ((elapsed_seconds + step_seconds - 1) // step_seconds) * step_seconds
    else:
        rounded_seconds = int(round(elapsed_seconds / step_seconds) * step_seconds)

    return day_start + timedelta(seconds=rounded_seconds)


def _parse_mode(mode: str) -> int:
    if mode not in SUPPORTED_ROUNDING_MODES or not mode.endswith("m"):
        raise ValueError(f"Unsupported rounding mode: {mode}")
    minutes = int(mode[:-1])
    if minutes not in SUPPORTED_ROUNDING_MINUTES:
        raise ValueError(f"Unsupported rounding minutes: {minutes}")
    return minutes
