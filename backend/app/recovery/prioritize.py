"""
Case Prioritization and Queue Management.

Calculates priority score as:
  priority = amount_usd * recovery_likelihood
Derived from config/priority_weights.yaml.
Maintains a daily queue ordered by priority and restricted by the daily action cap.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from backend.app.recovery.diagnose import diagnose_case


_WEIGHTS_CACHE: dict[str, Any] | None = None


def load_priority_weights() -> dict[str, Any]:
    global _WEIGHTS_CACHE
    if _WEIGHTS_CACHE is not None:
        return _WEIGHTS_CACHE

    root = Path(__file__).resolve().parents[3]
    config_path = root / "backend" / "app" / "recovery" / "config" / "priority_weights.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            _WEIGHTS_CACHE = yaml.safe_load(f) or {}
            return _WEIGHTS_CACHE
    return {
        "likelihood_by_diagnosis": {
            "forgot_to_pay": 0.85,
            "expired_card": 0.75,
            "temporary_hold": 0.65,
            "insufficient_funds": 0.60,
            "large_overdue_invoice": 0.50,
            "suspicious_hard_decline": 0.15,
        },
        "default_likelihood": 0.50,
        "default_daily_action_cap": 50,
    }


def calculate_priority(
    case: dict[str, Any],
    weights_table: dict[str, Any] | None = None,
) -> float:
    """
    Compute priority score = round(amount_usd * likelihood, 2).
    """
    weights = weights_table or load_priority_weights()
    likelihood_map = weights.get("likelihood_by_diagnosis", {})
    default_lik = float(weights.get("default_likelihood", 0.50))

    amount = float(case.get("amount_usd") or case.get("amount", 0.0))
    diagnosis = case.get("diagnosis")
    if not diagnosis:
        diagnosis = diagnose_case(case)

    likelihood = float(likelihood_map.get(diagnosis, default_lik))
    return round(amount * likelihood, 2)


def get_daily_queue(
    cases: list[dict[str, Any]],
    daily_cap: int | None = None,
    weights_table: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Order cases by priority score (descending) and cap the queue by daily_cap.
    Adds 'priority_score' and 'diagnosis' to each case in the returned queue.
    """
    weights = weights_table or load_priority_weights()
    cap = daily_cap if daily_cap is not None else int(weights.get("default_daily_action_cap", 50))

    scored_cases: list[dict[str, Any]] = []
    for c in cases:
        c_copy = dict(c)
        if not c_copy.get("diagnosis"):
            c_copy["diagnosis"] = diagnose_case(c_copy)
        c_copy["priority_score"] = calculate_priority(c_copy, weights)
        scored_cases.append(c_copy)

    # Sort descending by priority score
    scored_cases.sort(key=lambda x: x["priority_score"], reverse=True)

    # Return top capped cases
    return scored_cases[:cap]

