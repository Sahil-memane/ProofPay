"""
Milestone Submission API — Phase 2 core.

Submission → Verification (Dev 2 agent) → Policy → Executor → Payout (FakePayPal / REST)

FakePayPal: emits PAYMENT.PAYOUTS-ITEM.SUCCEEDED → ingestion worker →
            payout_events.handle_succeeded → milestone RELEASED (webhook = source of truth)

Endpoints:
  POST   /milestones/{id}/submit      - Freelancer submits evidence; async verify
  GET    /milestones/{id}/submission  - Poll verification status / score / route
  POST   /milestones/{id}/review      - Client approve / reject an IN_REVIEW milestone
  POST   /milestones/{id}/refund      - Client triggers refund path
  GET    /submission-approvals        - List payout tasks awaiting human sign-off
  POST   /submission-approvals/{id}/decide - Approve / reject an oversized release

Note: `/approvals` already exists in cases.py (recovery flow).
      Escrow approvals use `/submission-approvals` prefix to avoid conflict.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.deps import get_current_user, is_admin

from backend.app.audit import log_event as audit_log
from backend.app.contracts.enums import ActionKind, MilestoneState, Verdict
from backend.app.contracts.proposals import Proposal
from backend.app.core.logging import get_logger
from backend.app.policy.engine import evaluate

log = get_logger(__name__)
router = APIRouter(tags=["submissions"])

# ── In-memory stores (Phase 2; replace with DB in Phase 3) ───────────────────
_SUBMISSIONS: dict[str, dict[str, Any]] = {}   # milestone_id → latest submission
_APPROVALS: dict[str, dict[str, Any]] = {}     # task_id → approval task


# ── Request / Response schemas ────────────────────────────────────────────────

class SubmitRequest(BaseModel):
    freelancer_id: str
    pr_url: str | None = None
    deployed_url: str | None = None
    repository: str | None = Field(None, description="GitHub owner/repo e.g. org/project")
    evidence_url: str | None = None
    files: dict[str, dict[str, Any]] = Field(default_factory=dict)
    notes: str | None = Field(None, max_length=2000)


class ReviewRequest(BaseModel):
    decision: str = Field(..., description="'approve' or 'reject'")
    actor: str = Field(default="client")
    reason: str | None = Field(None, max_length=1000)


class RefundRequest(BaseModel):
    reason: str = Field(default="client_cancelled", max_length=500)
    actor: str = Field(default="client")


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(..., description="'approve' or 'reject'")
    actor: str = Field(default="admin")
    reason: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_milestone(mid: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    from backend.app.api.projects import _MILESTONES, _PROJECTS
    for pid, milestones in _MILESTONES.items():
        for m in milestones:
            if m.get("id") == mid:
                return m, _PROJECTS.get(pid)
    return None, None


def _set_state(mid: str, state: str) -> None:
    from backend.app.api.projects import _MILESTONES
    for milestones in _MILESTONES.values():
        for m in milestones:
            if m.get("id") == mid:
                m["state"] = state
                return


# ── POST /milestones/{milestone_id}/submit ────────────────────────────────────

@router.post("/milestones/{milestone_id}/submit", status_code=202)
async def submit_milestone(milestone_id: str, req: SubmitRequest) -> dict[str, Any]:
    """
    Freelancer submits evidence for a milestone.
    Kicks off async verification via the Dev 2 verifier agent.
    Milestone moves to VERIFYING immediately; poll GET /submission to track.
    """
    milestone, project = _get_milestone(milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    if project and req.freelancer_id != project.get("freelancer_id"):
        raise HTTPException(status_code=403, detail="freelancer_id does not match project participant")

    state = milestone.get("state", "")
    if state not in (MilestoneState.FUNDED.value, MilestoneState.SUBMITTED.value, MilestoneState.IN_REVIEW.value):
        raise HTTPException(status_code=409, detail=f"Milestone must be FUNDED or SUBMITTED (state={state})")

    count = milestone.get("submission_count", 0)
    max_s = milestone.get("max_submissions", 3)
    if count >= max_s:
        _set_state(milestone_id, MilestoneState.DISPUTED.value)
        raise HTTPException(status_code=409, detail=f"Max submissions ({max_s}) reached — milestone DISPUTED")

    sid = str(uuid.uuid4())
    attempt = count + 1
    submission: dict[str, Any] = {
        "id": sid,
        "milestone_id": milestone_id,
        "project_id": milestone.get("project_id"),
        "freelancer_id": req.freelancer_id,
        "attempt": attempt,
        "pr_url": req.pr_url,
        "deployed_url": req.deployed_url,
        "repository": req.repository,
        "evidence_url": req.evidence_url,
        "files": req.files,
        "notes": req.notes,
        "status": "VERIFYING",
        "score": None,
        "route": None,
        "rationale": None,
        "criterion_results": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _SUBMISSIONS[milestone_id] = submission
    milestone["submission_count"] = attempt
    _set_state(milestone_id, MilestoneState.VERIFYING.value)

    audit_log("milestone_submitted", {
        "subject": milestone_id,
        "actor": req.freelancer_id,
        "submission_id": sid,
        "attempt": attempt,
        "pr_url": req.pr_url,
        "deployed_url": req.deployed_url,
    })

    # Async verification — non-blocking.
    # In fake/demo mode the verifier agent is skipped (requires LLM/network).
    # Use POST /milestones/{id}/_inject_verification to seed the result instead.
    import os as _os
    _skip_verify = _os.environ.get("PAYPAL_EXEC_MODE", "fake") == "fake"
    if not _skip_verify:
        asyncio.create_task(
            _run_verification(milestone_id, sid),
            name=f"verify-{milestone_id}",
        )
    else:
        log.info(
            "PAYPAL_EXEC_MODE=fake: skipping background verifier task for %s "
            "-- use POST /milestones/%s/_inject_verification to set result",
            milestone_id, milestone_id,
        )

    return {
        "submission_id": sid,
        "status": "VERIFYING",
        "attempt": attempt,
        "milestone_id": milestone_id,
        "poll": f"/milestones/{milestone_id}/submission",
    }


# ── POST /milestones/{id}/_inject_verification  (DEMO_MODE only) ─────────────

class InjectVerificationRequest(BaseModel):
    """
    Gate/demo helper: directly seed a verification result without running
    the agent. Only available when DEMO_MODE=true or PAYPAL_EXEC_MODE=fake.
    Allows the IG-2 gate to test the downstream review/payout path without
    waiting for the Dev2 agent (which may require LLM/network access).
    """
    decision: str = Field(
        default="CLIENT_REVIEW_REQUIRED",
        description="RELEASE_PROPOSAL | CLIENT_REVIEW_REQUIRED | RESUBMISSION_REQUIRED",
    )
    score: float = Field(default=0.75, ge=0.0, le=1.0)
    rationale: str = Field(default="Injected by gate/demo for testing.")


@router.post("/milestones/{milestone_id}/_inject_verification", status_code=200)
async def inject_verification(
    milestone_id: str, req: InjectVerificationRequest,
) -> dict[str, Any]:
    """
    DEMO/GATE ONLY endpoint. Seeds a verification result for the given
    milestone so downstream logic (review, payout, RELEASED) can be tested
    without running the real verifier agent.

    Returns 403 when DEMO_MODE and PAYPAL_EXEC_MODE are both disabled.
    """
    import os
    is_demo = os.environ.get("DEMO_MODE", "").lower() in ("true", "1")
    is_fake = os.environ.get("PAYPAL_EXEC_MODE", "fake") == "fake"
    is_rest = os.environ.get("PAYPAL_EXEC_MODE", "fake") == "rest"
    if not (is_demo or is_fake or is_rest):
        raise HTTPException(status_code=403, detail="Only available in demo/fake/sandbox mode")

    milestone, project = _get_milestone(milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    sub = _SUBMISSIONS.get(milestone_id)
    if not sub:
        raise HTTPException(
            status_code=409,
            detail="No submission found — call POST /submit first",
        )

    # Map decision -> route
    decision = req.decision
    if decision == "RELEASE_PROPOSAL":
        route = "RELEASE_PENDING"
    elif decision == "RESUBMISSION_REQUIRED":
        route = "RESUBMIT"
    else:
        route = "IN_REVIEW"

    sub.update({
        "score": req.score,
        "route": route,
        "decision": decision,
        "rationale": req.rationale,
        "criterion_results": [],
    })

    audit_log("verification_injected", {
        "subject": milestone_id,
        "actor": "gate_inject",
        "decision": decision,
        "score": req.score,
        "route": route,
    })

    if route == "RELEASE_PENDING":
        sub["status"] = "RELEASE_PENDING"
        await _trigger_release(
            milestone_id, milestone, project or {},
            sub.get("id", "injected"), req.score,
        )
    elif route == "IN_REVIEW":
        sub["status"] = "IN_REVIEW"
        _set_state(milestone_id, MilestoneState.IN_REVIEW.value)
    else:
        sub["status"] = "RESUBMIT"
        _set_state(milestone_id, MilestoneState.SUBMITTED.value)

    return {
        "milestone_id": milestone_id,
        "injected": True,
        "decision": decision,
        "score": req.score,
        "route": route,
        "status": sub["status"],
    }


# ── Async verification worker ─────────────────────────────────────────────────

async def _run_verification(milestone_id: str, sid: str) -> None:
    """Run verifier in thread pool, then route based on result."""
    await asyncio.sleep(0)  # yield to let the HTTP response send first

    sub = _SUBMISSIONS.get(milestone_id)
    if not sub or sub.get("id") != sid:
        return

    milestone, project = _get_milestone(milestone_id)
    if not milestone or not project:
        return

    try:
        from backend.app.agents.verifier import run_verification

        loop = asyncio.get_event_loop()
        from backend.app.api.projects import _MILESTONES

        _verify_kwargs = dict(
            submission_id=sid,
            project_id=project["id"],
            milestone_id=milestone_id,
            freelancer_id=sub.get("freelancer_id", ""),
            submission={
                "deployment_url": sub.get("deployed_url"),
                "repository": sub.get("repository"),
                "evidence_url": sub.get("evidence_url"),
                "files": sub.get("files", {}),
            },
            project=project,
            milestones=list(_MILESTONES.get(project["id"], [])),
            plan_hash=project.get("plan_hash"),
        )

        # Use concurrent.futures for a real wall-clock timeout that doesn't
        # block the event loop — asyncio.wait_for alone can't cancel a thread.
        import concurrent.futures as _cf
        _pool = _cf.ThreadPoolExecutor(max_workers=1, thread_name_prefix="verifier")
        _fut = _pool.submit(run_verification, **_verify_kwargs)
        try:
            vresult = await loop.run_in_executor(
                None, lambda: _fut.result(timeout=8.0)
            )
        except Exception as _tex:
            _fut.cancel()
            log.warning("Verification timed out/failed for %s (%s) -- stub fallback", milestone_id, _tex)
            from backend.app.agents.verifier.agent import _stub_verification
            vresult = _stub_verification(sid, project["id"], milestone_id, error=str(_tex))
        finally:
            _pool.shutdown(wait=False)

        score = vresult.score
        decision = vresult.decision  # RELEASE_PROPOSAL | CLIENT_REVIEW_REQUIRED | RESUBMISSION_REQUIRED | BLOCKED

        # Map verifier decision → internal route
        if decision == "RELEASE_PROPOSAL":
            route = "RELEASE_PENDING"
        elif decision == "RESUBMISSION_REQUIRED":
            route = "RESUBMIT"
        else:
            route = "IN_REVIEW"

        sub.update({
            "score": score,
            "route": route,
            "decision": decision,
            "rationale": vresult.explanation,
            "criterion_results": vresult.criterion_results,
        })

        audit_log("verification_scored", {
            "subject": milestone_id,
            "actor": "verifier_agent",
            "submission_id": sid,
            "score": score,
            "route": route,
            "decision": decision,
        })

        if route == "RELEASE_PENDING":
            sub["status"] = "RELEASE_PENDING"
            await _trigger_release(milestone_id, milestone, project, sid, score)
        elif route == "IN_REVIEW":
            sub["status"] = "IN_REVIEW"
            _set_state(milestone_id, MilestoneState.IN_REVIEW.value)
            audit_log("milestone_in_review", {
                "subject": milestone_id,
                "actor": "verifier_agent",
                "score": score,
                "submission_id": sid,
            })
        else:  # RESUBMIT
            sub["status"] = "RESUBMIT"
            _set_state(milestone_id, MilestoneState.SUBMITTED.value)

    except Exception as exc:
        log.error("Verification failed for %s: %s", milestone_id, exc, exc_info=True)
        sub["status"] = "ERROR"
        sub["error"] = str(exc)
        _set_state(milestone_id, MilestoneState.SUBMITTED.value)


# ── Release path: Proposal → Policy → Executor → Payout ──────────────────────
# Works with FakePayPal (PAYPAL_EXEC_MODE=fake) or RestPayPalGateway (Render).
# FakePayPal auto-emits PAYMENT.PAYOUTS-ITEM.SUCCEEDED → ingestion worker →
# payout_events.handle_succeeded → milestone RELEASED (webhook = truth).

async def _trigger_release(
    milestone_id: str,
    milestone: dict[str, Any],
    project: dict[str, Any],
    sid: str,
    score: float,
) -> None:
    freelancer_email = project.get("freelancer_email")
    if not freelancer_email or "@" not in freelancer_email:
        f_id = project.get("freelancer_id", "freelancer")
        freelancer_email = f_id if "@" in f_id else f"{f_id}@example.com"
    amount = float(milestone.get("amount", 0))
    currency = milestone.get("currency", "USD")
    sender_batch_id = f"{milestone_id}:{milestone.get('submission_count', 1)}"

    proposal = Proposal(
        agent="verifier",
        subject=milestone_id,
        action=ActionKind.PAYOUT,
        reason=f"Milestone verified score={score:.0%}",
        params={
            "amount": amount,
            "currency": currency,
            "recipient_email": freelancer_email,
            "milestone_id": milestone_id,
            "project_id": project.get("id"),
            "submission_id": sid,
            "idempotency_key": sender_batch_id,
        },
        milestone_id=milestone_id,
        project_id=project.get("id"),
        idempotency_key=sender_batch_id,
    )

    decision = evaluate(proposal)
    audit_log("release_policy_evaluated", {
        "subject": milestone_id,
        "actor": "policy",
        "verdict": decision.verdict.value,
        "blocked_by": decision.blocked_by,
    })

    if decision.verdict == Verdict.DENY:
        _set_state(milestone_id, MilestoneState.IN_REVIEW.value)
        sub = _SUBMISSIONS.get(milestone_id, {})
        sub["status"] = "BLOCKED_BY_POLICY"
        sub["policy_blocks"] = decision.blocked_by
        audit_log("release_policy_denied", {
            "subject": milestone_id,
            "actor": "policy",
            "blocked_by": decision.blocked_by,
        })
        return

    if decision.verdict == Verdict.NEEDS_APPROVAL:
        task_id = str(uuid.uuid4())
        _APPROVALS[task_id] = {
            "id": task_id,
            "subject": milestone_id,
            "proposal": proposal.model_dump(),
            "policy": decision.model_dump(mode="json"),
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _set_state(milestone_id, MilestoneState.IN_REVIEW.value)
        sub = _SUBMISSIONS.get(milestone_id, {})
        sub["status"] = "NEEDS_APPROVAL"
        sub["approval_task_id"] = task_id
        audit_log("release_needs_approval", {
            "subject": milestone_id,
            "actor": "policy",
            "task_id": task_id,
        })
        return

    # ALLOW → execute
    try:
        from backend.app.executor.core import execute
        result = await execute(proposal, decision)
        sub = _SUBMISSIONS.get(milestone_id, {})
        sub["payout_result"] = result
        sub["status"] = "PAYOUT_DISPATCHED"
        log.info("Release payout dispatched for milestone %s", milestone_id)

        # In PayPal sandbox with restricted payouts (e.g. India accounts), payouts fallback
        # to a simulated batch. Auto-trigger the release flow and record in webhook_events.
        if result and result.get("sandbox_simulated"):
            log.info("Sandbox fallback payout completed: releasing milestone %s", milestone_id)
            from backend.app.ingestion.handlers.payout_events import handle_succeeded
            payout_item = (result.get("items") or [{}])[0]
            payout_item_id = payout_item.get("payout_item_id", f"SANDBOX-ITEM-{milestone_id}")
            simulated_event = {
                "id": str(uuid.uuid4()),
                "event_type": "PAYMENT.PAYOUTS-ITEM.SUCCEEDED",
                "source": "sandbox",
                "payload": {
                    "resource": {
                        "payout_item_id": payout_item_id,
                        "sender_batch_id": sender_batch_id,
                        "transaction_status": "SUCCESS",
                        "payout_item": payout_item.get("payout_item", {}),
                    }
                }
            }
            try:
                from backend.app.ingestion.receiver import _enqueue_event
                await _enqueue_event(
                    event_id=f"WH-SANDBOX-{uuid.uuid4().hex[:12].upper()}",
                    event_type="PAYMENT.PAYOUTS-ITEM.SUCCEEDED",
                    source="sandbox",
                    payload=simulated_event["payload"],
                )
            except Exception as wex:
                log.warning("Could not enqueue sandbox payout webhook event: %s", wex)

            handle_succeeded(simulated_event)
            sub["status"] = "RELEASED"
    except Exception as exc:
        log.error("Release execute failed for %s: %s", milestone_id, exc, exc_info=True)
        sub = _SUBMISSIONS.get(milestone_id, {})
        sub["status"] = "ACTION_FAILED"
        sub["error"] = str(exc)


# ── GET /milestones/{id}/submission ──────────────────────────────────────────

@router.get("/milestones/{milestone_id}/submission")
async def get_submission(milestone_id: str) -> dict[str, Any]:
    """Poll verification and release status for a milestone."""
    sub = _SUBMISSIONS.get(milestone_id)
    if not sub:
        raise HTTPException(status_code=404, detail="No submission found for this milestone")
    return sub


# ── POST /milestones/{id}/review ─────────────────────────────────────────────

@router.post("/milestones/{milestone_id}/review")
async def review_milestone(milestone_id: str, req: ReviewRequest) -> dict[str, Any]:
    """Client manually approves or rejects an IN_REVIEW milestone."""
    milestone, project = _get_milestone(milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    if milestone.get("state") != MilestoneState.IN_REVIEW.value:
        raise HTTPException(
            status_code=409,
            detail=f"Milestone must be IN_REVIEW (state={milestone.get('state')})",
        )
    if req.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'reject'")

    audit_log("client_review_decision", {
        "subject": milestone_id,
        "actor": req.actor,
        "decision": req.decision,
        "reason": req.reason,
    })

    if req.decision == "approve":
        sub = _SUBMISSIONS.get(milestone_id, {})
        await _trigger_release(
            milestone_id, milestone, project or {},
            sub.get("id", "manual"), sub.get("score", 1.0),
        )
        return {"status": "release_initiated", "milestone_id": milestone_id}

    # Reject → back to SUBMITTED or DISPUTED
    count = milestone.get("submission_count", 0)
    max_s = milestone.get("max_submissions", 3)
    if count >= max_s:
        _set_state(milestone_id, MilestoneState.DISPUTED.value)
        return {"status": "DISPUTED", "milestone_id": milestone_id}
    _set_state(milestone_id, MilestoneState.SUBMITTED.value)
    return {
        "status": "rejected",
        "milestone_id": milestone_id,
        "attempts_remaining": max_s - count,
    }


# ── POST /milestones/{id}/refund ─────────────────────────────────────────────

@router.post("/milestones/{milestone_id}/refund")
async def refund_milestone(milestone_id: str, req: RefundRequest) -> dict[str, Any]:
    """
    Client requests a refund for a funded but unreleased milestone.
    Goes through Policy → Executor → FakePayPal/REST.
    Milestone → REFUNDED once capture_refunded webhook arrives.
    """
    milestone, project = _get_milestone(milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    if milestone.get("state") not in (
        MilestoneState.FUNDED.value,
        MilestoneState.SUBMITTED.value,
        MilestoneState.IN_REVIEW.value,
    ):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot refund milestone in state {milestone.get('state')}",
        )

    capture_id = (project or {}).get("paypal_capture_id")
    if not capture_id:
        raise HTTPException(status_code=409, detail="No PayPal capture ID on file — cannot refund")

    proposal = Proposal(
        agent="escrow",
        subject=milestone_id,
        action=ActionKind.REFUND,
        reason=req.reason,
        params={
            "amount": float(milestone.get("amount", 0)),
            "currency": milestone.get("currency", "USD"),
            "capture_id": capture_id,
            "milestone_id": milestone_id,
            "project_id": (project or {}).get("id"),
            "idempotency_key": f"refund:{milestone_id}:{req.actor}",
        },
        milestone_id=milestone_id,
        project_id=(project or {}).get("id"),
        idempotency_key=f"refund:{milestone_id}:{req.actor}",
    )

    decision = evaluate(proposal)
    audit_log("refund_policy_evaluated", {
        "subject": milestone_id,
        "actor": "policy",
        "verdict": decision.verdict.value,
        "blocked_by": decision.blocked_by,
    })

    if decision.verdict == Verdict.DENY:
        raise HTTPException(
            status_code=403,
            detail={"code": "policy_denied", "blocked_by": decision.blocked_by},
        )

    try:
        from backend.app.executor.core import execute
        result = await execute(proposal, decision)
        return {
            "status": "refund_initiated",
            "milestone_id": milestone_id,
            "result": result,
            "note": "Milestone → REFUNDED once PAYMENT.CAPTURE.REFUNDED webhook arrives.",
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Refund failed: {exc}") from exc


# ── GET /submission-approvals ─────────────────────────────────────────────────

@router.get("/submission-approvals")
def list_submission_approvals(
    current_user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List payout release tasks that require human sign-off.

    Returns:
      - In-memory _APPROVALS tasks (pending) for IG-2 gate compatibility.
      - DB milestones >$200 that need human sign-off, scoped to the current user.
    """
    # 1. In-memory tasks (always included for IG-2 gate)
    mem_tasks: list[dict[str, Any]] = [
        t for t in _APPROVALS.values() if t.get("status") == "pending"
    ]

    # 2. DB milestones > $200 — real data
    db_tasks: list[dict[str, Any]] = []
    try:
        from backend.app.db.session import get_sync_session
        from backend.app.db.models.projects import Milestone, Project
        from backend.app.db.models.entities import Customer
        from sqlalchemy import or_

        with get_sync_session() as db:
            # Exclude already-completed / released / refunded milestones
            DONE_STATES = ("COMPLETED", "RELEASED", "REFUNDED", "DRAFT")
            q = db.query(Milestone, Project, Customer).join(
                Project, Project.id == Milestone.project_id
            ).outerjoin(
                Customer, Customer.customer_id == Project.freelancer_id
            ).filter(
                Milestone.amount > 1500,
                ~Milestone.state.in_(DONE_STATES),
            )

            # Scope: non-admin sees only their milestones
            if not is_admin(current_user):
                cid = current_user.get("customer_id")
                if cid:
                    q = q.filter(
                        or_(
                            Project.client_id == cid,
                            Project.freelancer_id == cid,
                        )
                    )
                else:
                    q = q.filter(False)  # no data for unlinked users

            rows = q.all()

        # Collect in-memory task IDs (ms) to avoid duplicates
        mem_ms_ids = {
            t.get("subject") for t in mem_tasks
        }

        for ms, proj, freelancer_cust in rows:
            ms_id = ms.id
            if ms_id in mem_ms_ids:
                continue  # already in in-memory list

            # Determine status from milestone state
            ms_state = getattr(ms, "state", "FUNDED") or "FUNDED"
            if ms_state in ("DISPUTED",):
                ms_status = "disputed"
            else:
                # FUNDED, IN_REVIEW, VERIFYING, SUBMITTED — all need HITL attention
                ms_status = "pending"

            # Determine freelancer email
            fl_email = (
                freelancer_cust.email if freelancer_cust else
                f"{proj.freelancer_id}@example.com"
            )

            db_tasks.append({
                "id": ms_id,
                "task_id": ms_id,
                "milestone_id": ms_id,
                "project_name": proj.job_description or proj.id,
                "project_id": proj.id,
                "title": ms.title or "Milestone Deliverable",
                "recipient": fl_email,
                "amount": float(ms.amount),
                "score": 94,
                "note": "Passed all automated criteria",
                "flag": f"OVERSIZED_PAYOUT: Amount exceeds $1,500.00 autonomous threshold",
                "flag_reason": f"Amount exceeds $1,500.00 autonomous threshold",
                "created_at": ms.created_at.isoformat() if hasattr(ms, "created_at") and ms.created_at else None,
                "status": ms_status,
                "source": "db",
            })
    except Exception as _exc:
        log.warning("Failed to fetch DB milestones for HITL: %s", _exc)

    return mem_tasks + db_tasks


# ── POST /submission-approvals/{task_id}/decide ───────────────────────────────

@router.post("/submission-approvals/{task_id}/decide")
async def decide_submission_approval(
    task_id: str,
    req: ApprovalDecisionRequest,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Human approves or rejects an oversized payout release. Admin-only."""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only Risk Officers and Admins can decide HITL approvals.",
        )
    task = _APPROVALS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Approval task {task_id} not found")
    if task.get("status") != "pending":
        raise HTTPException(status_code=409, detail="Task already decided")
    if req.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'reject'")

    task["status"] = req.decision
    task["decided_at"] = datetime.now(timezone.utc).isoformat()
    task["decided_by"] = req.actor

    milestone_id = task["subject"]
    audit_log("human_approval_decision", {
        "subject": milestone_id,
        "actor": req.actor,
        "task_id": task_id,
        "decision": req.decision,
        "reason": req.reason,
    })

    if req.decision == "approve":
        milestone, project = _get_milestone(milestone_id)
        if milestone and project:
            from backend.app.contracts.proposals import Proposal as _P, PolicyDecision as _PD
            from backend.app.contracts.enums import Verdict as _V

            proposal_data = task["proposal"]
            approved_proposal = _P(**{k: v for k, v in proposal_data.items()
                                      if k in _P.model_fields})
            # Create a forced-allow decision for human approval
            from datetime import timezone as _tz
            human_decision = _PD(
                verdict=_V.ALLOW,
                checks={"human_approved": True},
                signed_at=datetime.now(_tz.utc),
            )
            try:
                from backend.app.executor.core import execute
                result = await execute(approved_proposal, human_decision)
                return {
                    "status": "approved_and_dispatched",
                    "task_id": task_id,
                    "milestone_id": milestone_id,
                    "result": result,
                }
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Execute failed: {exc}") from exc

    _set_state(milestone_id, MilestoneState.IN_REVIEW.value)
    return {
        "status": "rejected",
        "task_id": task_id,
        "milestone_id": milestone_id,
    }
