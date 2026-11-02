"""
Cases API Router for Dev 4 (Step 11).

Endpoints:
  GET  /cases?sort=priority
  GET  /cases?status=HALTED,UNRECOVERED (includes reason on every row)
  GET  /cases/{case_id} (case detail with attempt timeline and policy checks)
  GET  /outbox
  GET  /reconciliation/summary (matched, review, exception)
  GET  /approvals
  POST /approvals/{id}/decide
  POST /cases/{case_id}/reopen (audited)
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.channels.outbox import list_messages
from backend.app.reconciliation.normalizer import load_all_recon_records
from backend.app.reconciliation.tiers import ReconVerdict
from backend.app.recovery.state_machine import halt_case, reopen, transition
from backend.app.stubs import audit, executor, policy
from backend.app.stubs.contracts_stub import CaseState, PolicyDecision, Proposal, Verdict
from backend.app.stubs.repositories import case_repo, contact_repo

router = APIRouter(tags=["cases"])


class ReopenRequest(BaseModel):
    actor: str = Field(default="human_operator")
    reason: str = Field(default="reopened_by_support")


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(..., description="'approve' or 'reject'")
    actor: str = Field(default="human_operator")
    notes: str = Field(default="")


# ── GET /cases ────────────────────────────────────────────────────────────────

@router.get("/cases")
def list_cases(
    status: str | None = None,
    sort: str | None = None,
) -> list[dict[str, Any]]:
    cases = case_repo.list_all()

    # Filter by comma-separated status list
    if status:
        allowed = {s.strip().upper() for s in status.split(",") if s.strip()}
        filtered: list[dict[str, Any]] = []
        for c in cases:
            c_state = str(c.get("state")).upper()
            if any(s in c_state for s in allowed):
                row = dict(c)
                # Ensure a reason is present on every row
                history = c.get("history", [])
                reason = history[-1].get("reason", "unknown") if history else "initial"
                row["reason"] = c.get("unrecovered_reason") or reason
                filtered.append(row)
        cases = filtered
    else:
        # Attach reason to all rows
        for c in cases:
            history = c.get("history", [])
            reason = history[-1].get("reason", "unknown") if history else "initial"
            c["reason"] = c.get("unrecovered_reason") or reason

    # Sort by priority
    if sort == "priority":
        cases.sort(
            key=lambda x: (
                float(x.get("priority_score") or x.get("amount_usd", 0.0))
            ),
            reverse=True,
        )

    return cases


# ── GET /cases/{case_id} ──────────────────────────────────────────────────────

@router.get("/cases/{case_id}")
def get_case_detail(case_id: str) -> dict[str, Any]:
    case = case_repo.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    contacts = contact_repo.list_for_case(case_id)
    history = case.get("history", [])

    # Format attempt timeline
    attempt_timeline = []
    for h in history:
        attempt_timeline.append({
            "from_state": h.get("from_state"),
            "to_state": h.get("to_state"),
            "actor": h.get("actor"),
            "reason": h.get("reason"),
            "timestamp": h.get("timestamp"),
        })

    # Policy checks audit
    case_audits = [
        e for e in audit.get_events()
        if e.get("case_id") == case_id or str(e.get("case_id")) in case_id
    ]

    return {
        "case": case,
        "attempt_timeline": attempt_timeline,
        "contacts": contacts,
        "policy_checks": case_audits,
    }


# ── GET /outbox ───────────────────────────────────────────────────────────────

@router.get("/outbox")
def get_outbox() -> list[dict[str, Any]]:
    return list_messages()


# ── GET /reconciliation/summary ───────────────────────────────────────────────

@router.get("/reconciliation/summary")
def get_reconciliation_summary() -> dict[str, Any]:
    from backend.app.reconciliation.matcher import match_case_against_record

    records = load_all_recon_records()
    cases = case_repo.list_all()

    matched: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    exception: list[dict[str, Any]] = []

    for c in cases:
        case_matched = False
        for r in records:
            res = match_case_against_record(c, r)
            if res.verdict == ReconVerdict.AUTO_MATCH.value:
                matched.append({
                    "case_id": c.get("id"),
                    "external_id": r.external_id,
                    "amount": r.amount,
                    "score": res.score,
                    "source": r.source,
                })
                case_matched = True
                break
            elif res.verdict == ReconVerdict.HUMAN_REVIEW.value:
                review.append({
                    "case_id": c.get("id"),
                    "external_id": r.external_id,
                    "score": res.score,
                    "anomalies": res.anomalies,
                })
                case_matched = True
                break

        if not case_matched and c.get("state") in (CaseState.UNRECOVERED, CaseState.HALTED):
            exception.append({
                "case_id": c.get("id"),
                "reason": "unmatched_exception",
                "amount": c.get("amount_usd"),
            })

    return {
        "matched": matched,
        "review": review,
        "exception": exception,
        "total_matched": len(matched),
        "total_review": len(review),
        "total_exception": len(exception),
    }


# ── GET /approvals & POST /approvals/{id}/decide ─────────────────────────────

@router.get("/approvals")
def list_pending_approvals() -> list[dict[str, Any]]:
    cases = case_repo.list_all()
    pending = [
        c for c in cases
        if c.get("state") in (CaseState.ACTION_PENDING_APPROVAL, "ACTION_PENDING_APPROVAL")
    ]
    return pending


@router.post("/approvals/{case_id}/decide")
def decide_approval(case_id: str, req: ApprovalDecisionRequest) -> dict[str, Any]:
    case = case_repo.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    decision_norm = req.decision.strip().lower()
    if decision_norm not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'reject'")

    if decision_norm == "approve":
        transition(
            case,
            to_state=CaseState.ACTION_SENT,
            actor=req.actor,
            reason=f"ops_approved: {req.notes}".strip(),
        )
        audit.log_event("ops_approval_granted", {
            "case_id": case_id,
            "actor": req.actor,
            "notes": req.notes,
        })
        return {"status": "approved", "case_id": case_id, "state": CaseState.ACTION_SENT.value}
    else:
        transition(
            case,
            to_state=CaseState.HALTED,
            actor=req.actor,
            reason=f"ops_rejected: {req.notes}".strip(),
        )
        audit.log_event("ops_approval_rejected", {
            "case_id": case_id,
            "actor": req.actor,
            "notes": req.notes,
        })
        return {"status": "rejected", "case_id": case_id, "state": CaseState.HALTED.value}


# ── POST /cases/{case_id}/reopen ──────────────────────────────────────────────

@router.post("/cases/{case_id}/reopen")
def reopen_case_endpoint(case_id: str, req: ReopenRequest) -> dict[str, Any]:
    case = case_repo.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    try:
        updated = reopen(case, actor=req.actor, reason=req.reason)
        return updated
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
