# TEMP: replaced by core/clock
"""Stub clock — supports fixed time, advancing time, and simulate_days."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from typing import Any

_CURRENT_TIME: datetime | None = None
_TICK_LISTENERS: list[Any] = []

clock = sys.modules[__name__]


def set_time(dt: datetime) -> None:
    """Set the clock to a specific datetime."""
    global _CURRENT_TIME
    if dt.tzinfo is None:
        _CURRENT_TIME = dt.replace(tzinfo=timezone.utc)
    else:
        _CURRENT_TIME = dt.astimezone(timezone.utc)


def reset() -> None:
    """Reset clock to dynamic real-time mode."""
    global _CURRENT_TIME
    _CURRENT_TIME = None


def utcnow() -> datetime:
    """Return current UTC time from FakeClock or system datetime."""
    if _CURRENT_TIME is not None:
        return _CURRENT_TIME
    return datetime.now(tz=timezone.utc)


def advance_time(delta: timedelta) -> datetime:
    """Advance the clock by a timedelta."""
    global _CURRENT_TIME
    if _CURRENT_TIME is None:
        _CURRENT_TIME = datetime.now(tz=timezone.utc)
    _CURRENT_TIME += delta
    _trigger_ticks()
    return _CURRENT_TIME


def register_tick_listener(callback: Any) -> None:
    """Register a callback invoked when clock advances."""
    if callback not in _TICK_LISTENERS:
        _TICK_LISTENERS.append(callback)


def _trigger_ticks() -> None:
    for listener in list(_TICK_LISTENERS):
        try:
            listener(utcnow())
        except Exception:
            pass


def simulate_days(n: float | int) -> datetime:
    """Advance the FakeClock by n days and trigger scheduler ticks."""
    return advance_time(timedelta(days=n))
