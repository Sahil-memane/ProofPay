"""
Scoping Agent adapter.

Wraps Dev 2's ScopingAgentRunner (ProofPay_Agent_1_and_2) so it can be
called from our FastAPI projects router without any import boundary
violations (no paypal/ or executor/ imports here).

Key invariant: agents MUST NOT import from paypal/ or executor/.
"""
from __future__ import annotations

import sys
import uuid
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ── Make the Dev2 package importable ─────────────────────────────────────────
_DEV2_ROOT = Path(__file__).resolve().parents[3] / "ProofPay_Agent_1_and_2"
if str(_DEV2_ROOT) not in sys.path:
    sys.path.insert(0, str(_DEV2_ROOT))


@dataclass
class ScopingResult:
    """Structured output from the scoping agent."""

    project_id: str
    milestones: list[dict[str, Any]]
    plan_hash: str | None
    status: str  # DRAFT | PLAN_APPROVED | NEEDS_CLARIFICATION | ERROR
    clarification_questions: list[str] = field(default_factory=list)
    error_message: str | None = None
    raw_state: dict[str, Any] = field(default_factory=dict)


def _convert_milestone(m: dict[str, Any], project_id: str) -> dict[str, Any]:
    """Normalize Dev2 milestone schema → our internal milestone dict."""
    mid = m.get("id") or str(uuid.uuid4())
    criteria_raw = m.get("acceptance_criteria") or m.get("criteria") or []
    criteria = []
    for c in criteria_raw:
        criteria.append({
            "id": c.get("id", str(uuid.uuid4())),
            "type": c.get("type", "manual_review"),
            "params": c.get("params", {}),
            "weight": float(c.get("weight", 1.0)),
            "must_pass": bool(c.get("must_pass", True)),
        })
    if not criteria:
        criteria = [{
            "id": "manual_review",
            "type": "manual_review",
            "params": {},
            "weight": 1.0,
            "must_pass": True,
        }]
    return {
        "id": mid,
        "project_id": project_id,
        "title": m.get("title", "Milestone"),
        "description": m.get("description", ""),
        "amount": float(m.get("payment_amount") or m.get("amount", 0.0)),
        "currency": "USD",
        "state": "DRAFT",
        "sequence": m.get("sequence", 0),
        "criteria": criteria,
        "deadline": m.get("deadline"),
        "submission_count": 0,
        "max_submissions": 3,
    }


def run_scoping(
    project_id: str,
    job_description: str,
    total_amount: float,
    currency: str,
    client_id: str,
    freelancer_id: str,
    deadline: str | None = None,
) -> ScopingResult:
    """
    Run the scoping agent for a new project.

    Falls back to a single-milestone stub if the agent package is
    unavailable (e.g., langgraph not installed in this venv).
    """
    try:
        from ProofPay.agents.scoping_agent.graph import ScopingAgentRunner  # type: ignore[import]

        runner = ScopingAgentRunner()
        project_data: dict[str, Any] = {
            "project_id": project_id,
            "project_description": job_description,
            "total_budget": total_amount,
            "currency": currency,
            "client_id": client_id,
            "freelancer_id": freelancer_id,
            "deadline": deadline or "30 days",
            "user_provided_config": {},
        }
        state = runner.start_project(project_data, thread_id=project_id)
        runner.close()

        milestones_raw: list[dict[str, Any]] = state.get("milestones") or []
        milestones = [
            _convert_milestone(m, project_id) for m in milestones_raw
        ]
        # Re-sequence after conversion
        for i, m in enumerate(milestones):
            m["sequence"] = i

        # Adjust amounts if they don't sum correctly (scoping agent uses
        # payment_amount; we must match total_amount)
        ms_total = round(sum(m["amount"] for m in milestones), 2)
        if milestones and abs(ms_total - round(total_amount, 2)) > 0.01:
            log.warning(
                "Scoping agent milestone sum %.2f != total %.2f — adjusting last milestone",
                ms_total, total_amount,
            )
            diff = round(total_amount - ms_total, 2)
            milestones[-1]["amount"] = round(milestones[-1]["amount"] + diff, 2)

        return ScopingResult(
            project_id=project_id,
            milestones=milestones,
            plan_hash=state.get("plan_hash"),
            status=state.get("project_status", "DRAFT"),
            clarification_questions=state.get("clarification_questions") or [],
            error_message=state.get("error_message"),
            raw_state=dict(state),
        )

    except ImportError as exc:
        log.warning("Scoping agent not available (%s) — using stub fallback", exc)
        return _stub_scoping(project_id, total_amount, currency, deadline)
    except Exception as exc:
        log.error("Scoping agent failed: %s", exc, exc_info=True)
        return _stub_scoping(project_id, total_amount, currency, deadline)


def _stub_scoping(
    project_id: str,
    total_amount: float,
    currency: str,
    deadline: str | None,
) -> ScopingResult:
    """Single-milestone fallback when the real agent is unavailable."""
    milestone_id = str(uuid.uuid4())
    milestones = [
        {
            "id": milestone_id,
            "project_id": project_id,
            "title": "Project Deliverable",
            "description": "Full project deliverable as described.",
            "amount": total_amount,
            "currency": currency,
            "state": "DRAFT",
            "sequence": 0,
            "criteria": [
                {
                    "id": "manual_review",
                    "type": "manual_review",
                    "params": {},
                    "weight": 1.0,
                    "must_pass": True,
                }
            ],
            "deadline": deadline,
            "submission_count": 0,
            "max_submissions": 3,
        }
    ]
    return ScopingResult(
        project_id=project_id,
        milestones=milestones,
        plan_hash=None,
        status="DRAFT",
    )

