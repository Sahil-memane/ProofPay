# Replaced by backend/app/core/clock.py — re-exporting for backward compatibility.
# Dev 3's imports (from backend.app.stubs import clock; clock.utcnow()) continue to work.
from __future__ import annotations

import sys

from backend.app.core.clock import (  # noqa: F401
    _TICK_LISTENERS,
    advance_time,
    register_tick_listener,
    reset,
    set_time,
    simulate_days,
    utcnow,
)

# Allow `from backend.app.stubs import clock; clock.utcnow()` pattern
clock = sys.modules[__name__]

