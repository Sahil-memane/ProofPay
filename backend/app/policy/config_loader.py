"""
Policy config loader.
Reads configuration from DB policy_config table with in-memory caching and fallback defaults.
"""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy import select

from backend.app.db.models.support import PolicyConfig
from backend.app.db.session import get_sync_session

_CACHE: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 30.0  # seconds

DEFAULTS = {
    "auto_action_limit_usd": "200.0",
    "max_contact_cap": "4",
    "min_gap_hours": "48.0",
    "quiet_hours_start": "21:00",
    "quiet_hours_end": "08:00",
    "daily_action_cap": "50",
    "max_release_amount_usd": "5000.0",
    "max_project_total_usd": "25000.0",
    "llm_daily_cap": "100",
    "llm_case_budget": "2",
}


def get_config(key: str, default: str | None = None) -> str:
    now = time.time()
    if key in _CACHE:
        val, expiry = _CACHE[key]
        if now < expiry:
            return val

    # Try DB
    try:
        with get_sync_session() as session:
            stmt = select(PolicyConfig).where(PolicyConfig.key == key)
            row = session.execute(stmt).scalar_one_or_none()
            if row:
                _CACHE[key] = (row.value, now + _CACHE_TTL)
                return row.value
    except Exception:
        pass

    fallback = DEFAULTS.get(key, default or "")
    _CACHE[key] = (fallback, now + _CACHE_TTL)
    return fallback


def set_config(key: str, value: str) -> None:
    now = time.time()
    _CACHE[key] = (value, now + _CACHE_TTL)
    try:
        with get_sync_session() as session:
            stmt = select(PolicyConfig).where(PolicyConfig.key == key)
            row = session.execute(stmt).scalar_one_or_none()
            if row:
                row.value = value
            else:
                row = PolicyConfig(key=key, value=value)
                session.add(row)
            session.commit()
    except Exception:
        pass


def get_float(key: str, default: float = 0.0) -> float:
    try:
        return float(get_config(key, str(default)))
    except (ValueError, TypeError):
        return default


def get_int(key: str, default: int = 0) -> int:
    try:
        return int(get_config(key, str(default)))
    except (ValueError, TypeError):
        return default
