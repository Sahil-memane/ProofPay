# TEMP: replaced by audit/
"""Stub audit logger — records events and prints to stdout."""
from __future__ import annotations
from typing import Any
import json

_events: list[dict[str, Any]] = []


def log_event(event_type: str, payload: dict[str, Any]) -> None:
    """Log an audit event (stub: stores in memory and prints JSON)."""
    record = {"event": event_type, **payload}
    _events.append(record)
    print(json.dumps(record))


def get_events() -> list[dict[str, Any]]:
    """Return all recorded audit events."""
    return list(_events)


def clear() -> None:
    """Clear recorded audit events."""
    _events.clear()
