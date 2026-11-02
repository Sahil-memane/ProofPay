"""
Dashboard API Router for Dev 4 (Step 11).

Endpoints:
  GET /dashboard/headline - High-level headline metrics for Dev 4 screens
  GET /eval/latest        - Latest evaluation run scoreboard
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from backend.app.stubs.contracts_stub import CaseState
from backend.app.stubs.repositories import case_repo

router = APIRouter(tags=["dashboard"])

ROOT = Path(__file__).resolve().parents[3]
EVAL_JSON = ROOT / "data" / "eval_report.json"


@router.get("/dashboard/headline")
def get_dashboard_headline() -> dict[str, Any]:
    """
    Returns headline numbers for operations overview:
      - recovered_amount ($)
      - at_risk_amount ($)
      - case_count (total)
      - recovered_count (total recovered)
    """
    cases = case_repo.list_all()
    case_count = len(cases)

    recovered_count = 0
    recovered_amount = 0.0
    at_risk_amount = 0.0

    for c in cases:
        amt = float(c.get("amount_usd", 0.0))
        at_risk_amount += amt
        state = c.get("state")
        if state in (CaseState.RECOVERED, CaseState.PAID_ELSEWHERE, "RECOVERED", "PAID_ELSEWHERE"):
            recovered_count += 1
            recovered_amount += amt

    return {
        "recovered_amount": round(recovered_amount, 2),
        "at_risk_amount": round(at_risk_amount, 2),
        "case_count": case_count,
        "recovered_count": recovered_count,
    }


@router.get("/eval/latest")
def get_latest_eval() -> dict[str, Any]:
    """Return the latest evaluation run comparison summary."""
    if EVAL_JSON.exists():
        with open(EVAL_JSON, "r", encoding="utf-8") as f:
            return json.load(f)

    # Fallback to fresh run if report does not exist yet
    from backend.app.eval.runner import run_evaluation
    return run_evaluation(cases_limit=20)
