"""
ProofPay Core Clock.

A controllable clock abstraction:
- In production: returns real UTC time.
- In demo/tests: can be set to a fixed time or advanced forward.

This is the REAL implementation. The stub at backend/app/stubs/clock.py
re-exports from here for backward compatibility.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

_CURRENT_TIME: datetime | None = None
_TICK_LISTENERS: list[Callable[[datetime], None]] = []


def utcnow() -> datetime:
    """Return current UTC time. Honours a fixed/advanced demo clock."""
    if _CURRENT_TIME is not None:
        return _CURRENT_TIME
    return datetime.now(tz=timezone.utc)


def set_time(dt: datetime) -> None:
    """Pin the clock to a specific UTC datetime (demo / test use only)."""
    global _CURRENT_TIME
    _CURRENT_TIME = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def reset() -> None:
    """Return to real-time mode."""
    global _CURRENT_TIME
    _CURRENT_TIME = None


def advance_time(delta: timedelta) -> datetime:
    """Advance the clock by delta and notify tick listeners."""
    global _CURRENT_TIME
    if _CURRENT_TIME is None:
        _CURRENT_TIME = datetime.now(tz=timezone.utc)
    _CURRENT_TIME += delta
    _trigger_ticks()
    return _CURRENT_TIME


def simulate_days(n: float | int) -> datetime:
    """Convenience: advance by n days."""
    return advance_time(timedelta(days=n))


def register_tick_listener(callback: Callable[[datetime], None]) -> None:
    """Register a callback invoked whenever the clock is advanced."""
    if callback not in _TICK_LISTENERS:
        _TICK_LISTENERS.append(callback)


def _trigger_ticks() -> None:
    now = utcnow()
    for listener in list(_TICK_LISTENERS):
        try:
            listener(now)
        except Exception:
            pass

import sys
clock = sys.modules[__name__]
