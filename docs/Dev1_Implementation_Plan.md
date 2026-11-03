# ProofPay — Dev 1 Implementation Plan
*Tech Lead · Platform · PayPal Integration Engineer*
*Nov 3 → Nov 11, 2026 | Hard deadline: 12 Nov 3:00 pm EST*

---

## Quick Reference

| Item | Value |
|---|---|
| Your role | Dev 1 — Tech Lead, Platform & PayPal Integration |
| Current phase | Phase 1 → 2 boundary |
| IG-1 target | Nov 5 (hosted URL) |
| IG-2 target | Nov 6 (hosted URL) |
| PayPal mode (local) | `PAYPAL_EXEC_MODE=fake` — **keep it, no sandbox needed for feature work** |
| PayPal mode (Render) | `PAYPAL_EXEC_MODE=rest` — set only when running gate scripts |

---

## PayPal Sandbox — When Do You Actually Need It?

> **Short answer: Not now. Use `FakePayPal` for all feature work.**

The [`FakePayPal`](file:///e:/Projects/ProofPay/backend/app/paypal/fake_paypal.py) in the codebase is not a naive stub. It:
- Returns realistic `FAKE-ORDER-xxxx`, `FAKE-CAPTURE-xxxx`, `FAKE-BATCH-xxxx` IDs
- **Auto-emits webhooks directly into the real `webhook_events` DB table** via `emit_webhook()`
- Has programmable failure switches: `fail_capture`, `fail_payout`, `deny_payout`, `fail_refund`, `fail_invoice`
- Runs the **identical ingestion worker code path** as a real PayPal webhook

```
PAYPAL_EXEC_MODE=fake   → FakePayPal()        ← use this always on your laptop
PAYPAL_EXEC_MODE=rest   → RestPayPalGateway() ← set only in Render dashboard for gate runs
```

### The exact split

| Task | `fake` enough? | Notes |
|---|---|---|
| All feature coding (Steps 1–13) | ✅ Yes | FakePayPal covers every code path |
| CI pipeline (all test suites) | ✅ Yes | CI must always use `fake` |
| IG-1 / IG-2 gate runs locally | ✅ Yes | `/sim/events` + fake works |
| IG-1 / IG-2 on **Render hosted URL** | ❌ Need REST | Real webhooks need public URL |
| PayPal JS SDK checkout buttons | ❌ Need `PAYPAL_CLIENT_ID` | JS SDK won't load without it |
| Verify Payouts is enabled (D-1 decision) | ❌ One `curl` call | Do this once, 5 min |
| Video / demo recording | ❌ Need REST on Render | Judges want real PayPal branding |

### When you DO set up sandbox (one-time, before IG-1 gate on Render)

1. Go to **[developer.paypal.com](https://developer.paypal.com)**
2. Create 3 sandbox accounts: Business (platform), Personal (buyer), Personal (freelancer)
3. Create a REST app → copy Client ID + Secret into **Render dashboard only**
4. Test Payouts with one `curl` — if 403, trigger **D-1 fallback** (Orders + Invoicing release)
5. Register webhook → `https://your-app.onrender.com/webhooks/paypal` → get `PAYPAL_WEBHOOK_ID`
6. Set `PAYPAL_EXEC_MODE=rest` in **Render dashboard only** — your local `.env` stays `fake`

---

## Execution Timeline

```
TODAY Nov 3
  Step 1 → Place scoping + verifier agents from Dev 2
  Step 2 → Fix payout_events.py TODO (20 min)
  Step 3 → Generate contracts/openapi.json

NOV 4
  Step 4 → Submission API (submit, verify, review, refund, approvals)
  Step 5 → Wire REFUND dispatch in executor

NOV 5
  Step 6 → Escrow timer scheduler jobs
  Step 7 → RUN IG-1 GATE on hosted URL

NOV 6
  Step 8 → RUN IG-2 GATE on hosted URL

NOV 7–8
  Step 9  → paypal/subscriptions.py
  Step 10 → paypal/disputes.py
  Step 11 → Dispute event handler (halt case + freeze milestone)
  Step 12 → Reputation full wiring
  Step 13 → Write docs/adr/ decision records

NOV 9–10
  Step 14 → Security pass (CORS, rate limits, secrets scan)
  Step 15 → Postman collection v1 + Newman CI
  Step 16 → README draft + docs/sponsors.md
```

---

## STEP 1 — Place Scoping & Verifier Agents (Nov 3)

> Dev 2 handed you these files. If not yet received, create the stubs below — the import chain will work immediately and the real agent drops in later without any other change.

### 1a. `backend/app/agents/scoping/__init__.py`

```python
# backend/app/agents/scoping/__init__.py
"""Scoping agent package — Dev 2 authored."""
from backend.app.agents.scoping.agent import run_scoping  # noqa: F401
```

### 1b. `backend/app/agents/scoping/agent.py`

```python
# backend/app/agents/scoping/agent.py
"""
Scoping Agent.

Pipeline:
  1. Pre-validate (length, currency, budget within limits)
  2. LLM call 1 → 2–6 milestones (schema-constrained, library types only)
  3. Validators → repair call if errors
  4. Template fallback (single milestone) if both LLM calls fail
  5. Persist DRAFT and return milestones

Import boundary: MUST NOT import from paypal/ or executor/.
"""
from __future__ import annotations

import uuid
from typing import Any

from backend.app.audit.writer import log_event
from backend.app.core.logging import get_logger

log = get_logger(__name__)

_MIN_MILESTONE_AMOUNT = 5.0
_HARD_WEIGHT_FLOOR = 0.70


def run_scoping(
    job_description: str,
    total_amount: float,
    currency: str = "USD",
    deadline: str | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Run the scoping pipeline and return milestones list."""
    # Try real agent if Dev 2 module is present
    try:
        from backend.app.agents.scoping._real_agent import scope  # type: ignore[import]
        return scope(
            job_description=job_description,
            total_amount=total_amount,
            currency=currency,
            deadline=deadline,
            project_id=project_id,
        )
    except ImportError:
        pass

    # Template fallback: single milestone
    log.info("Scoping: using template fallback for project %s", project_id)
    milestones = _template_fallback(
        total_amount=total_amount,
        currency=currency,
        deadline=deadline,
        project_id=project_id or str(uuid.uuid4()),
    )
    log_event("scoping_complete", {
        "subject": project_id, "actor": "scoping_agent",
        "milestone_count": len(milestones), "llm_used": False, "fallback": True,
    })
    return {"milestones": milestones, "llm_used": False, "fallback": True, "errors": []}


def validate_milestones(milestones: list[dict[str, Any]], total: float) -> list[str]:
    """Pure validators — no LLM. Called by the edit endpoint too."""
    errors: list[str] = []
    if not milestones:
        errors.append("At least one milestone required")
        return errors

    total_ms = round(sum(float(m.get("amount", 0)) for m in milestones), 2)
    if abs(total_ms - round(total, 2)) > 0.01:
        errors.append(
            f"Milestone amounts ({total_ms}) do not sum to project total ({round(total, 2)})"
        )

    for i, m in enumerate(milestones):
        if float(m.get("amount", 0)) < _MIN_MILESTONE_AMOUNT:
            errors.append(f"Milestone {i+1}: amount below minimum ${_MIN_MILESTONE_AMOUNT}")
        criteria = m.get("criteria", [])
        if not criteria:
            errors.append(f"Milestone {i+1}: at least one criterion required")
            continue
        hard_w = sum(float(c.get("weight", 0)) for c in criteria if c.get("must_pass"))
        total_w = sum(float(c.get("weight", 0)) for c in criteria)
        if total_w > 0 and hard_w / total_w < _HARD_WEIGHT_FLOOR:
            errors.append(
                f"Milestone {i+1}: hard criteria must carry ≥70% of weight "
                f"(current: {hard_w / total_w:.0%})"
            )
    return errors


def _template_fallback(
    total_amount: float, currency: str, deadline: str | None, project_id: str
) -> list[dict[str, Any]]:
    return [{
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "title": "Project Completion",
        "amount": total_amount,
        "currency": currency,
        "state": "DRAFT",
        "sequence": 0,
        "criteria": [{"id": "manual_review", "type": "manual_review",
                       "params": {}, "weight": 1.0, "must_pass": True}],
        "deadline": deadline,
        "submission_count": 0,
        "max_submissions": 3,
    }]
```

### 1c. `backend/app/agents/verifier/__init__.py`

```python
# backend/app/agents/verifier/__init__.py
"""Verifier agent package — Dev 2 authored."""
from backend.app.agents.verifier.agent import run_verification  # noqa: F401
```

### 1d. `backend/app/agents/verifier/agent.py`

```python
# backend/app/agents/verifier/agent.py
"""
Verifier Agent.

Pipeline:
  1. Collect facts (GitHub, HTTP prober, file inspector) per criterion
  2. Score = Σ weight(passed hard criteria) / Σ weight(all hard criteria)
  3. Route: ≥0.90 → RELEASE_PENDING | 0.60–0.89 → IN_REVIEW | <0.60 → RESUBMIT
  4. Rationale LLM call (optional, template fallback)

Import boundary: MUST NOT import from paypal/ or executor/.
"""
from __future__ import annotations
from typing import Any
from backend.app.audit.writer import log_event
from backend.app.core.logging import get_logger

log = get_logger(__name__)
_THRESHOLD_AUTO_RELEASE = 0.90
_THRESHOLD_HUMAN_REVIEW = 0.60


def run_verification(
    milestone: dict[str, Any],
    submission: dict[str, Any],
    project: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run verification pipeline. Returns facts, score, route, rationale."""
    try:
        from backend.app.agents.verifier._real_agent import verify  # type: ignore[import]
        return verify(milestone=milestone, submission=submission, project=project)
    except ImportError:
        pass

    criteria = milestone.get("criteria", [])
    facts = _collect_facts(criteria, submission)
    score, must_pass_failed = _score(facts, criteria)
    route = _route(score, must_pass_failed)
    rationale = _template_rationale(facts, score, route)

    log_event("verification_complete", {
        "subject": milestone.get("id"), "actor": "verifier_agent",
        "score": score, "route": route, "llm_used": False,
        "must_pass_failed": must_pass_failed,
    })
    return {
        "facts": facts, "score": score, "route": route,
        "rationale": rationale, "llm_used": False,
        "must_pass_failed": must_pass_failed,
    }


def _collect_facts(criteria, submission) -> list[dict]:
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    facts = []
    for c in criteria:
        ctype = c.get("type", "manual_review")
        cid = c.get("id", ctype)
        if ctype == "manual_review":
            facts.append({"criterion_id": cid, "passed": False, "value": None,
                           "source": "manual", "checked_at": now,
                           "reason": "Requires manual review"})
        elif ctype == "url_returns_200":
            passed, val = _probe_url(submission.get("deployed_url", ""))
            facts.append({"criterion_id": cid, "passed": passed, "value": val,
                           "source": submission.get("deployed_url", ""), "checked_at": now})
        elif ctype == "github_pr_merged":
            passed, val = _check_github_pr(submission.get("pr_url", ""))
            facts.append({"criterion_id": cid, "passed": passed, "value": val,
                           "source": submission.get("pr_url", ""), "checked_at": now})
        else:
            facts.append({"criterion_id": cid, "passed": False, "value": None,
                           "source": "unknown", "checked_at": now,
                           "reason": f"Unknown criterion type: {ctype}"})
    return facts


def _probe_url(url: str) -> tuple[bool, str]:
    if not url:
        return False, "no_url"
    try:
        import httpx
        r = httpx.get(url, timeout=5.0, follow_redirects=True)
        return r.status_code == 200, str(r.status_code)
    except Exception as e:
        return False, str(e)[:120]


def _check_github_pr(pr_url: str) -> tuple[bool, str]:
    if not pr_url or "github.com" not in pr_url:
        return False, "no_pr_url"
    try:
        parts = pr_url.rstrip("/").split("/")
        if len(parts) < 7:
            return False, "invalid_pr_url"
        owner, repo, num = parts[3], parts[4], parts[6]
        import httpx
        from backend.app.core.config import settings
        headers = {}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
        r = httpx.get(f"https://api.github.com/repos/{owner}/{repo}/pulls/{num}",
                      headers=headers, timeout=8.0)
        if r.status_code == 200:
            merged = r.json().get("merged", False)
            return merged, "merged" if merged else r.json().get("state", "unknown")
        return False, f"http_{r.status_code}"
    except Exception as e:
        return False, str(e)[:120]


def _score(facts, criteria) -> tuple[float, bool]:
    wmap = {c.get("id", c.get("type")): float(c.get("weight", 1.0)) for c in criteria}
    must_ids = {c.get("id", c.get("type")) for c in criteria if c.get("must_pass")}
    hard_total = sum(wmap.get(c.get("id", c.get("type")), 1.0)
                     for c in criteria if c.get("must_pass"))
    passed_w = 0.0
    must_pass_failed = False
    for f in facts:
        cid = f.get("criterion_id")
        if cid in must_ids:
            if f.get("passed"):
                passed_w += wmap.get(cid, 1.0)
            else:
                must_pass_failed = True
    if hard_total == 0:
        return 0.0, must_pass_failed
    return round(passed_w / hard_total, 4), must_pass_failed


def _route(score: float, must_pass_failed: bool) -> str:
    if score >= _THRESHOLD_AUTO_RELEASE and not must_pass_failed:
        return "RELEASE_PENDING"
    elif score >= _THRESHOLD_HUMAN_REVIEW:
        return "IN_REVIEW"
    return "RESUBMIT"


def _template_rationale(facts, score, route) -> str:
    lines = [f"Score: {score:.0%}. Route: {route}."]
    for f in facts:
        status = "✓" if f.get("passed") else "✗"
        lines.append(f"{status} {f.get('criterion_id')}: {f.get('value') or f.get('reason', '')}")
    return " | ".join(lines)[:500]
```

### 1e. Wire Scoping into `POST /projects` in `api/projects.py`

Replace the `create_project` endpoint body:

```python
@router.post("/projects", status_code=201)
async def create_project(req: CreateProjectRequest) -> dict[str, Any]:
    project_id = str(uuid.uuid4())

    from backend.app.agents.scoping.agent import run_scoping, validate_milestones
    scoping_result = run_scoping(
        job_description=req.job_description,
        total_amount=req.total_amount,
        currency=req.currency,
        deadline=req.deadline,
        project_id=project_id,
    )
    milestones = scoping_result["milestones"]
    for m in milestones:
        m["project_id"] = project_id
        if "id" not in m:
            m["id"] = str(uuid.uuid4())

    errors = validate_milestones(milestones, req.total_amount)
    if errors:
        raise HTTPException(status_code=422, detail={"validation_errors": errors})

    project: dict[str, Any] = {
        "id": project_id, "state": "DRAFT", "plan_hash": None,
        "total_amount": req.total_amount, "currency": req.currency,
        "client_id": req.client_id, "freelancer_id": req.freelancer_id,
        "client_approved": False, "freelancer_approved": False,
        "paypal_order_id": None, "paypal_capture_id": None,
        "job_description": req.job_description, "deadline": req.deadline,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scoping_fallback": scoping_result.get("fallback", False),
    }
    _PROJECTS[project_id] = project
    _MILESTONES[project_id] = milestones

    audit_log("project_created", {
        "subject": project_id, "actor": "system",
        "total_amount": req.total_amount, "currency": req.currency,
        "milestone_count": len(milestones),
        "scoping_fallback": scoping_result.get("fallback", False),
    })
    return {
        "project": project, "milestones": milestones,
        "scoping": {"llm_used": scoping_result.get("llm_used", False),
                    "fallback": scoping_result.get("fallback", True)},
    }
```

---

## STEP 2 — Fix `payout_events.py` TODO (Nov 3, ~20 min)

**File:** `backend/app/ingestion/handlers/payout_events.py`

Replace the `handle_succeeded` function with the full wiring:

```python
@register("payout_item_succeeded")
def handle_succeeded(event: dict[str, Any]) -> None:
    resource = event.get("payload", {}).get("resource", {})
    payout_item_id = resource.get("payout_item_id", "")
    sender_batch_id = resource.get("sender_batch_id", "")
    transaction_id = resource.get("transaction_id", "")

    log.info("payout_item_succeeded: payout_item_id=%s sender_batch_id=%s",
             payout_item_id, sender_batch_id)

    try:
        import uuid
        from datetime import datetime, timezone
        from backend.app.db.session import get_sync_session
        from backend.app.db.models.projects import Milestone, LedgerEntry
        from backend.app.audit import log_event as audit_log
        from backend.app.reputation.ledger import record_event as rep_event
        from sqlalchemy import select

        with get_sync_session() as session:
            # sender_batch_id = "milestone_id:attempt" (see executor)
            milestone = session.execute(
                select(Milestone).where(
                    Milestone.id == sender_batch_id.split(":")[0]
                )
            ).scalar_one_or_none()

            if not milestone:
                log.warning("payout_item_succeeded: no milestone for sender_batch_id=%s",
                            sender_batch_id)
                audit_log("payout_item_succeeded_no_milestone", {
                    "actor": "webhook",
                    "payout_item_id": payout_item_id,
                    "sender_batch_id": sender_batch_id,
                })
                return

            # Idempotency guard
            if milestone.state == "RELEASED":
                log.info("payout_item_succeeded: milestone %s already RELEASED", milestone.id)
                return

            # Write RELEASE ledger entry (INSERT-ONLY table)
            session.add(LedgerEntry(
                id=str(uuid.uuid4()),
                type="RELEASE",
                subject_id=milestone.id,
                amount=milestone.amount,
                currency=milestone.currency,
                paypal_id=payout_item_id,
                note=f"Milestone released via payout {payout_item_id}",
            ))
            milestone.state = "RELEASED"
            session.commit()

        # Reputation event (outside transaction, non-fatal)
        try:
            with get_sync_session() as s2:
                from backend.app.db.models.projects import Project
                project = s2.execute(
                    select(Project).where(Project.id == milestone.project_id)
                ).scalar_one_or_none()
                if project and project.freelancer_id:
                    rep_event(project.freelancer_id, "on_time_release")
        except Exception as rep_exc:
            log.warning("Reputation update failed (non-fatal): %s", rep_exc)

        audit_log("payout_item_succeeded", {
            "subject": milestone.id, "actor": "webhook",
            "payout_item_id": payout_item_id,
            "sender_batch_id": sender_batch_id,
            "transaction_id": transaction_id,
            "milestone_state": "RELEASED",
        })
        log.info("payout_item_succeeded: milestone %s → RELEASED", milestone.id)

    except Exception as exc:
        log.error("payout_item_succeeded handler error: %s", exc, exc_info=True)
        raise
```

Also complete `capture_refunded` in `backend/app/ingestion/handlers/capture_denied.py`:

```python
@register("capture_refunded")
def handle_refunded(event: dict[str, Any]) -> None:
    resource = event.get("payload", {}).get("resource", {})
    refund_id = resource.get("id", "")
    links = resource.get("links", [])
    capture_href = next((l["href"] for l in links if l.get("rel") == "up"), "")
    capture_id = capture_href.rstrip("/").split("/")[-1] if capture_href else ""

    log.info("capture_refunded: refund_id=%s capture_id=%s", refund_id, capture_id)

    try:
        import uuid
        from backend.app.db.session import get_sync_session
        from backend.app.db.models.projects import Project, Milestone, LedgerEntry
        from backend.app.audit import log_event as audit_log
        from sqlalchemy import select

        with get_sync_session() as session:
            project = session.execute(
                select(Project).where(Project.paypal_capture_id == capture_id)
            ).scalar_one_or_none()

            if not project:
                audit_log("capture_refunded_no_project", {
                    "actor": "webhook", "refund_id": refund_id, "capture_id": capture_id,
                })
                return

            milestones = session.execute(
                select(Milestone).where(
                    Milestone.project_id == project.id,
                    Milestone.state.in_(["FUNDED", "SUBMITTED", "IN_REVIEW"])
                )
            ).scalars().all()

            for m in milestones:
                session.add(LedgerEntry(
                    id=str(uuid.uuid4()), type="REFUND", subject_id=m.id,
                    amount=m.amount, currency=m.currency, paypal_id=refund_id,
                    note=f"Milestone refunded via PayPal refund {refund_id}",
                ))
                m.state = "REFUNDED"

            if milestones:
                project.state = "CANCELLED"
            session.commit()

        audit_log("capture_refunded", {
            "subject": project.id, "actor": "webhook",
            "refund_id": refund_id, "capture_id": capture_id,
            "milestones_refunded": len(milestones),
        })
    except Exception as exc:
        log.error("capture_refunded handler error: %s", exc, exc_info=True)
        raise
```

---

## STEP 3 — Generate OpenAPI Spec (Nov 3)

Create `backend/scripts/export_openapi.py`:

```python
#!/usr/bin/env python
"""Export FastAPI OpenAPI schema to contracts/openapi.json."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.app.main import app

OUTPUT = Path(__file__).resolve().parents[2] / "contracts" / "openapi.json"
OUTPUT.parent.mkdir(exist_ok=True)
schema = app.openapi()
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(schema, f, indent=2)
print(f"✓ Written {len(schema.get('paths', {}))} paths to {OUTPUT}")
```

Run:
```bash
cd e:\Projects\ProofPay
python backend/scripts/export_openapi.py
git add contracts/openapi.json && git commit -m "feat: generate contracts/openapi.json"
```

---

## STEP 4 — Submission API (Nov 4)

Create `backend/app/api/submissions.py` and mount it in `main.py`.

### Endpoints delivered by this file

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/milestones/{id}/submit` | Submit PR URL + deployed URL; kicks off async verification |
| `GET` | `/milestones/{id}/submission` | Poll verification progress (facts, score, route) |
| `POST` | `/milestones/{id}/review` | Client approve/reject an IN_REVIEW milestone |
| `POST` | `/milestones/{id}/refund` | Initiate refund → policy → executor → PayPal |
| `GET` | `/approvals` | List pending over-limit approval tasks |
| `POST` | `/approvals/{id}/decide` | Human approve/reject large release |

```python
# backend/app/api/submissions.py
"""
Milestone Submission API — Phase 2 core.
Submission → Verification (async) → Release path → Payout (via FakePayPal or real sandbox)
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.audit.writer import log_event as audit_log
from backend.app.contracts.enums import ActionKind, MilestoneState, Verdict
from backend.app.contracts.proposals import Proposal
from backend.app.core.logging import get_logger
from backend.app.paypal import get_gateway
from backend.app.policy.engine import evaluate

log = get_logger(__name__)
router = APIRouter(tags=["submissions"])

_SUBMISSIONS: dict[str, dict[str, Any]] = {}   # milestone_id → latest submission
_APPROVALS:   dict[str, dict[str, Any]] = {}   # task_id → approval task


class SubmitRequest(BaseModel):
    pr_url: str | None = None
    deployed_url: str | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ReviewRequest(BaseModel):
    decision: str = Field(..., description="'approve' or 'reject'")
    actor: str = Field(default="client")
    reason: str | None = Field(default=None, max_length=1000)


class RefundRequest(BaseModel):
    reason: str = Field(default="client_cancelled", max_length=500)
    actor: str = Field(default="client")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_milestone(mid: str) -> tuple[dict | None, dict | None]:
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
    milestone, project = _get_milestone(milestone_id)
    if not milestone:
        raise HTTPException(404, "Milestone not found")

    state = milestone.get("state")
    if state not in (MilestoneState.FUNDED.value, MilestoneState.SUBMITTED.value):
        raise HTTPException(409, f"Milestone must be FUNDED or SUBMITTED (state={state})")

    count = milestone.get("submission_count", 0)
    max_s = milestone.get("max_submissions", 3)
    if count >= max_s:
        _set_state(milestone_id, MilestoneState.DISPUTED.value)
        raise HTTPException(409, f"Max submissions ({max_s}) reached — milestone DISPUTED")

    sid = str(uuid.uuid4())
    attempt = count + 1
    submission = {
        "id": sid, "milestone_id": milestone_id,
        "project_id": milestone.get("project_id"),
        "attempt": attempt, "pr_url": req.pr_url,
        "deployed_url": req.deployed_url, "notes": req.notes,
        "status": "VERIFYING",
        "facts": [], "score": None, "route": None, "rationale": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _SUBMISSIONS[milestone_id] = submission
    milestone["submission_count"] = attempt
    _set_state(milestone_id, MilestoneState.VERIFYING.value)

    audit_log("milestone_submitted", {
        "subject": milestone_id, "actor": "freelancer",
        "submission_id": sid, "attempt": attempt,
        "pr_url": req.pr_url, "deployed_url": req.deployed_url,
    })

    # Kick off async verification — uses FakePayPal in dev, REST on Render
    asyncio.create_task(_run_verification(milestone_id, sid), name=f"verify-{milestone_id}")

    return {"submission_id": sid, "status": "VERIFYING",
            "attempt": attempt, "milestone_id": milestone_id}


# ── Async verification worker ─────────────────────────────────────────────────

async def _run_verification(milestone_id: str, sid: str) -> None:
    await asyncio.sleep(0)
    sub = _SUBMISSIONS.get(milestone_id)
    if not sub or sub.get("id") != sid:
        return

    milestone, project = _get_milestone(milestone_id)
    if not milestone:
        return

    try:
        from backend.app.agents.verifier.agent import run_verification
        result = run_verification(milestone=milestone, submission=sub, project=project)
        sub.update({
            "facts": result["facts"], "score": result["score"],
            "route": result["route"], "rationale": result["rationale"],
            "llm_used": result.get("llm_used", False),
        })
        route = result["route"]
        score = result["score"]

        audit_log("verification_scored", {
            "subject": milestone_id, "actor": "verifier_agent",
            "submission_id": sid, "score": score, "route": route,
        })

        if route == "RELEASE_PENDING":
            sub["status"] = "RELEASE_PENDING"
            await _trigger_release(milestone_id, milestone, project, sid, score)
        elif route == "IN_REVIEW":
            sub["status"] = "IN_REVIEW"
            _set_state(milestone_id, MilestoneState.IN_REVIEW.value)
            audit_log("milestone_in_review", {
                "subject": milestone_id, "actor": "verifier_agent",
                "score": score, "submission_id": sid,
            })
        else:
            sub["status"] = "RESUBMIT"
            _set_state(milestone_id, MilestoneState.SUBMITTED.value)

    except Exception as exc:
        log.error("Verification failed for %s: %s", milestone_id, exc, exc_info=True)
        sub["status"] = "ERROR"
        sub["error"] = str(exc)


# ── Release path: Proposal → Policy → Executor → Payout ──────────────────────
# Works with FakePayPal (dev) or RestPayPalGateway (Render/prod).
# FakePayPal auto-emits PAYMENT.PAYOUTS-ITEM.SUCCEEDED → ingestion worker →
# payout_item_succeeded handler → milestone RELEASED (webhook is source of truth).

async def _trigger_release(
    milestone_id: str, milestone: dict, project: dict | None,
    sid: str, score: float,
) -> None:
    if not project:
        return

    freelancer_email = project.get("freelancer_email") or project.get("freelancer_id", "")
    amount = float(milestone.get("amount", 0))
    currency = milestone.get("currency", "USD")
    sender_batch_id = f"{milestone_id}:{milestone.get('submission_count', 1)}"

    proposal = Proposal(
        agent="verifier", subject=milestone_id, action=ActionKind.PAYOUT,
        reason=f"Milestone verified score={score:.0%}",
        params={
            "amount": amount, "currency": currency,
            "recipient_email": freelancer_email,
            "milestone_id": milestone_id, "project_id": project.get("id"),
            "submission_id": sid,
        },
        milestone_id=milestone_id, project_id=project.get("id"),
        idempotency_key=sender_batch_id,
    )

    decision = evaluate(proposal)
    audit_log("release_policy_evaluated", {
        "subject": milestone_id, "actor": "policy",
        "verdict": decision.verdict.value, "blocked_by": decision.blocked_by,
    })

    if decision.verdict == Verdict.DENY:
        _set_state(milestone_id, MilestoneState.IN_REVIEW.value)
        _SUBMISSIONS[milestone_id]["status"] = "BLOCKED_BY_POLICY"
        _SUBMISSIONS[milestone_id]["policy_blocks"] = decision.blocked_by
        return

    if decision.verdict == Verdict.NEEDS_APPROVAL:
        task_id = str(uuid.uuid4())
        _APPROVALS[task_id] = {
            "id": task_id, "subject": milestone_id,
            "proposal": proposal.model_dump(), "decision": decision.model_dump(),
            "status": "pending", "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _set_state(milestone_id, MilestoneState.IN_REVIEW.value)
        _SUBMISSIONS[milestone_id]["status"] = "NEEDS_APPROVAL"
        _SUBMISSIONS[milestone_id]["approval_task_id"] = task_id
        audit_log("release_needs_approval", {
            "subject": milestone_id, "actor": "policy", "task_id": task_id,
        })
        return

    # ALLOW → execute
    try:
        from backend.app.executor.core import execute
        result = await execute(proposal, decision)
        _SUBMISSIONS[milestone_id]["payout_result"] = result
        # Milestone → RELEASED set by payout_item_succeeded webhook (source of truth)
        # FakePayPal emits that webhook immediately via emit_webhook()
        log.info("Release payout dispatched for milestone %s", milestone_id)
    except Exception as exc:
        log.error("Release execute failed for %s: %s", milestone_id, exc, exc_info=True)
        _SUBMISSIONS[milestone_id]["status"] = "ACTION_FAILED"
        _SUBMISSIONS[milestone_id]["error"] = str(exc)


# ── GET /milestones/{id}/submission ──────────────────────────────────────────

@router.get("/milestones/{milestone_id}/submission")
async def get_submission(milestone_id: str) -> dict[str, Any]:
    sub = _SUBMISSIONS.get(milestone_id)
    if not sub:
        raise HTTPException(404, "No submission found for this milestone")
    return sub


# ── POST /milestones/{id}/review ─────────────────────────────────────────────

@router.post("/milestones/{milestone_id}/review")
async def review_milestone(milestone_id: str, req: ReviewRequest) -> dict[str, Any]:
    milestone, project = _get_milestone(milestone_id)
    if not milestone:
        raise HTTPException(404, "Milestone not found")
    if milestone.get("state") != MilestoneState.IN_REVIEW.value:
        raise HTTPException(409, f"Milestone must be IN_REVIEW (state={milestone.get('state')})")
    if req.decision not in ("approve", "reject"):
        raise HTTPException(400, "decision must be 'approve' or 'reject'")

    audit_log("client_review_decision", {
        "subject": milestone_id, "actor": req.actor,
        "decision": req.decision, "reason": req.reason,
    })

    if req.decision == "approve":
        sub = _SUBMISSIONS.get(milestone_id, {})
        await _trigger_release(milestone_id, milestone, project,
                               sub.get("id", "manual"), sub.get("score", 0.5))
        return {"status": "release_initiated", "milestone_id": milestone_id}

    count = milestone.get("submission_count", 0)
    max_s = milestone.get("max_submissions", 3)
    if count >= max_s:
        _set_state(milestone_id, MilestoneState.DISPUTED.value)
        return {"status": "DISPUTED", "milestone_id": milestone_id}
    _set_state(milestone_id, MilestoneState.SUBMITTED.value)
    return {"status": "rejected", "milestone_id": milestone_id,
            "attempts_remaining": max_s - count}


# ── POST /milestones/{id}/refund ─────────────────────────────────────────────

@router.post("/milestones/{milestone_id}/refund")
async def refund_milestone(milestone_id: str, req: RefundRequest) -> dict[str, Any]:
    milestone, project = _get_milestone(milestone_id)
    if not milestone:
        raise HTTPException(404, "Milestone not found")
    if milestone.get("state") not in (
        MilestoneState.FUNDED.value, MilestoneState.SUBMITTED.value,
        MilestoneState.IN_REVIEW.value,
    ):
        raise HTTPException(409, f"Cannot refund milestone in state {milestone.get('state')}")

    capture_id = (project or {}).get("paypal_capture_id")
    if not capture_id:
        raise HTTPException(409, "No PayPal capture ID on file — cannot refund")

    proposal = Proposal(
        agent="escrow", subject=milestone_id, action=ActionKind.REFUND,
        reason=req.reason,
        params={
            "amount": float(milestone.get("amount", 0)),
            "currency": milestone.get("currency", "USD"),
            "capture_id": capture_id,
            "milestone_id": milestone_id,
            "project_id": (project or {}).get("id"),
        },
        milestone_id=milestone_id,
        project_id=(project or {}).get("id"),
        idempotency_key=f"refund:{milestone_id}:{req.actor}",
    )
    decision = evaluate(proposal)
    audit_log("refund_policy_evaluated", {
        "subject": milestone_id, "actor": "policy",
        "verdict": decision.verdict.value, "blocked_by": decision.blocked_by,
    })

    if decision.verdict == Verdict.DENY:
        raise HTTPException(403, {
            "code": "policy_denied", "blocked_by": decision.blocked_by,
            "checks": decision.checks,
        })

    try:
        from backend.app.executor.core import execute
        result = await execute(proposal, decision)
        return {
            "status": "refund_initiated", "milestone_id": milestone_id, "result": result,
            "note": "Milestone → REFUNDED once capture_refunded webhook arrives.",
        }
    except Exception as exc:
        raise HTTPException(502, f"Refund failed: {exc}")


# ── GET /approvals + POST /approvals/{id}/decide ──────────────────────────────

@router.get("/approvals")
def list_approvals() -> list[dict[str, Any]]:
    return [t for t in _APPROVALS.values() if t.get("status") == "pending"]


@router.post("/approvals/{task_id}/decide")
async def decide_approval(task_id: str, req: ReviewRequest) -> dict[str, Any]:
    task = _APPROVALS.get(task_id)
    if not task:
        raise HTTPException(404, "Approval task not found")
    if task.get("status") != "pending":
        raise HTTPException(409, "Task already decided")

    task.update({
        "status": req.decision, "actor": req.actor,
        "notes": req.reason, "decided_at": datetime.now(timezone.utc).isoformat(),
    })
    audit_log("approval_task_decided", {
        "subject": task.get("subject"), "actor": req.actor,
        "task_id": task_id, "decision": req.decision,
    })

    if req.decision == "approve":
        from backend.app.contracts.proposals import Proposal as P, PolicyDecision as PD
        proposal = P.model_validate(task["proposal"])
        decision = PD(verdict=Verdict.ALLOW, checks={}, blocked_by=[])
        try:
            from backend.app.executor.core import execute
            result = await execute(proposal, decision)
            return {"status": "approved_and_executed", "task_id": task_id, "result": result}
        except Exception as exc:
            raise HTTPException(502, f"Execution failed: {exc}")

    return {"status": "rejected", "task_id": task_id}
```

### Mount in `main.py`

```python
from backend.app.api.submissions import router as submissions_router
app.include_router(submissions_router)
```

---

## STEP 5 — Wire REFUND in Executor (Nov 4, 5 min)

In `backend/app/executor/core.py`, in the `_dispatch` function, add after the `payout` case:

```python
    if action.value == "refund":
        return await gateway.refund_capture(
            capture_id=proposal.params["capture_id"],
            amount=float(proposal.params["amount"]),
            currency=proposal.params.get("currency", "USD"),
            request_id=proposal.params.get("idempotency_key", str(uuid.uuid4())),
            note=proposal.reason,
        )
```

---

## STEP 6 — Escrow Timer Scheduler Jobs (Nov 5)

Add to `backend/app/scheduler/jobs/handlers.py`:

```python
def submission_deadline_reminder(milestone_id: str) -> dict[str, Any]:
    """Remind freelancer N days before milestone deadline."""
    from backend.app.api.projects import _MILESTONES, _PROJECTS
    from backend.app.channels.outbox import enqueue as outbox_enqueue

    milestone, project = None, None
    for pid, ms in _MILESTONES.items():
        for m in ms:
            if m.get("id") == milestone_id:
                milestone, project = m, _PROJECTS.get(pid)
    if not milestone or milestone.get("state") not in ("FUNDED", "SUBMITTED"):
        return {"status": "skipped"}

    outbox_enqueue(
        to=project.get("freelancer_id", ""),
        subject=f"Reminder: '{milestone.get('title')}' submission due soon",
        body=f"Please submit evidence for '{milestone.get('title')}' before the deadline.",
        case_id=milestone_id, channel="email",
    )
    audit.log_event("submission_deadline_reminder_sent",
                    {"subject": milestone_id, "actor": "scheduler"})
    return {"status": "reminder_sent", "milestone_id": milestone_id}


def stale_review_reminder(milestone_id: str) -> dict[str, Any]:
    """Ping client when milestone has been IN_REVIEW > 48 hours."""
    from backend.app.api.projects import _MILESTONES, _PROJECTS
    from backend.app.channels.outbox import enqueue as outbox_enqueue

    milestone, project = None, None
    for pid, ms in _MILESTONES.items():
        for m in ms:
            if m.get("id") == milestone_id:
                milestone, project = m, _PROJECTS.get(pid)
    if not milestone or milestone.get("state") != "IN_REVIEW":
        return {"status": "skipped"}

    outbox_enqueue(
        to=(project or {}).get("client_id", ""),
        subject=f"Action needed: review '{milestone.get('title')}'",
        body="A milestone is waiting for your review in ProofPay.",
        case_id=milestone_id, channel="email",
    )
    audit.log_event("stale_review_reminder_sent",
                    {"subject": milestone_id, "actor": "scheduler"})
    return {"status": "reminder_sent", "milestone_id": milestone_id}


def stale_escrow_reminder(project_id: str) -> dict[str, Any]:
    """Remind both parties when project has no activity for > 7 days."""
    from backend.app.api.projects import _PROJECTS, _MILESTONES
    from backend.app.channels.outbox import enqueue as outbox_enqueue

    project = _PROJECTS.get(project_id)
    if not project or project.get("state") in ("COMPLETED", "CANCELLED"):
        return {"status": "skipped"}

    active = [m for m in _MILESTONES.get(project_id, [])
              if m.get("state") not in ("RELEASED", "REFUNDED", "DISPUTED")]
    if not active:
        return {"status": "skipped", "reason": "no_active_milestones"}

    for party_id in [project.get("client_id"), project.get("freelancer_id")]:
        if party_id:
            outbox_enqueue(
                to=party_id,
                subject="ProofPay: your escrow project needs attention",
                body=f"Project {project_id} has active milestones pending action.",
                case_id=project_id, channel="email",
            )
    audit.log_event("stale_escrow_reminder_sent",
                    {"subject": project_id, "actor": "scheduler"})
    return {"status": "reminder_sent", "project_id": project_id}
```

---

## STEP 7 — IG-1 Gate (Nov 5, on Render)

```bash
BASE=https://your-proofpay-app.onrender.com

# 1. Create project
curl -sX POST $BASE/projects -H "Content-Type: application/json" \
  -d '{"job_description":"Build a REST API with auth and tests","total_amount":100.00}' \
  | python -m json.tool
# → Save PROJECT_ID

# 2. Approve both parties
curl -sX POST $BASE/projects/$PROJECT_ID/approve \
  -H "Content-Type: application/json" -d '{"party":"client"}'
curl -sX POST $BASE/projects/$PROJECT_ID/approve \
  -H "Content-Type: application/json" -d '{"party":"freelancer"}'

# 3. Fund
HASH=$(curl -s $BASE/projects/$PROJECT_ID \
  | python -c "import sys,json; print(json.load(sys.stdin)['project']['plan_hash'])")
curl -sX POST $BASE/projects/$PROJECT_ID/fund \
  -H "Content-Type: application/json" -d "{\"plan_hash\":\"$HASH\"}" | python -m json.tool

# 4. Simulate capture webhook
curl -sX POST $BASE/sim/events \
  -H "Content-Type: application/json" -H "X-Sim-Token: dev-tick-token-change-in-prod" \
  -d '{"event_type":"PAYMENT.CAPTURE.COMPLETED","id":"EVT-IG1-001",
       "resource":{"id":"CAP-IG1-001","order_id":"<order_id>",
                   "amount":{"value":"100.00","currency_code":"USD"}}}'

# 5. Replay same event 5 times → still 1 ledger entry (idempotency test)

# 6. Tampered plan_hash → expect 403
curl -sX POST $BASE/projects/$PROJECT_ID/fund \
  -H "Content-Type: application/json" -d '{"plan_hash":"tampered-xxxx"}' \
  | python -m json.tool

# 7. Check audit log
curl -s "$BASE/audit?limit=20" | python -m json.tool
```

---

## STEP 8 — IG-2 Gate (Nov 6, on Render)

```bash
MILESTONE_ID=<from project above>

# 1. Submit evidence
curl -sX POST $BASE/milestones/$MILESTONE_ID/submit \
  -H "Content-Type: application/json" \
  -d '{"pr_url":"https://github.com/octocat/Hello-World/pull/1",
       "deployed_url":"https://httpbin.org/status/200"}'

# 2. Poll until status != VERIFYING
sleep 5
curl -s $BASE/milestones/$MILESTONE_ID/submission | python -m json.tool

# 3. Simulate payout success → milestone RELEASED (FakePayPal does this automatically)
# On real Render with PAYPAL_EXEC_MODE=rest, wait for real PayPal webhook

# 4. Replay payout webhook → still 1 RELEASE entry
curl -sX POST $BASE/sim/events \
  -H "Content-Type: application/json" -H "X-Sim-Token: dev-tick-token-change-in-prod" \
  -d "{\"event_type\":\"PAYMENT.PAYOUTS-ITEM.SUCCEEDED\",\"id\":\"EVT-PAY-001\",
       \"resource\":{\"payout_item_id\":\"ITEM-001\",\"sender_batch_id\":\"$MILESTONE_ID:1\"}}"

# 5. Test over-limit (policy block)
# 6. Test refund
curl -sX POST $BASE/milestones/$MILESTONE_ID/refund \
  -H "Content-Type: application/json" -d '{"reason":"client_cancelled"}'
```

---

## STEP 9 — `paypal/subscriptions.py` (Nov 7)

```python
# backend/app/paypal/subscriptions.py
"""PayPal Subscriptions v1 API — used by Recovery agent retry tools."""
from __future__ import annotations
from typing import Any
from backend.app.paypal import client


async def get_subscription(subscription_id: str) -> dict[str, Any]:
    return await client.get(f"/v1/billing/subscriptions/{subscription_id}")


async def cancel_subscription(subscription_id: str, reason: str = "Customer request") -> dict[str, Any]:
    return await client.post(f"/v1/billing/subscriptions/{subscription_id}/cancel",
                             {"reason": reason})


async def capture_outstanding_balance(subscription_id: str) -> dict[str, Any]:
    body = {
        "note": "Capturing outstanding balance via ProofPay recovery",
        "capture_type": "OUTSTANDING_BALANCE",
        "amount": {"currency_code": "USD", "value": "0"},
    }
    return await client.post(f"/v1/billing/subscriptions/{subscription_id}/capture", body)


async def list_transactions(subscription_id: str, start_time: str, end_time: str) -> dict[str, Any]:
    return await client.get(
        f"/v1/billing/subscriptions/{subscription_id}/transactions",
        params={"start_time": start_time, "end_time": end_time},
    )
```

---

## STEP 10 — `paypal/disputes.py` (Nov 7)

```python
# backend/app/paypal/disputes.py
"""PayPal Customer Disputes API — used by dispute agent (Phase 4)."""
from __future__ import annotations
from typing import Any
from backend.app.paypal import client


async def get_dispute(dispute_id: str) -> dict[str, Any]:
    return await client.get(f"/v1/customer/disputes/{dispute_id}")


async def list_disputes(dispute_state: str | None = None, start_time: str | None = None) -> dict[str, Any]:
    params: dict[str, str] = {}
    if dispute_state:
        params["dispute_state"] = dispute_state
    if start_time:
        params["start_time"] = start_time
    return await client.get("/v1/customer/disputes", params=params)


async def accept_claim(dispute_id: str, note: str = "ProofPay accepts the claim") -> dict[str, Any]:
    return await client.post(f"/v1/customer/disputes/{dispute_id}/accept-claim", {"note": note})


async def provide_evidence(dispute_id: str, evidence_items: list[dict[str, Any]]) -> dict[str, Any]:
    return await client.post(f"/v1/customer/disputes/{dispute_id}/provide-evidence",
                             {"evidences": evidence_items})
```

---

## STEP 11 — Dispute Event Handler (Nov 7)

Create `backend/app/ingestion/handlers/dispute_events.py`:

```python
# backend/app/ingestion/handlers/dispute_events.py
"""
Handlers: CUSTOMER.DISPUTE.CREATED / UPDATED / RESOLVED

Architecture law: deterministic halt FIRST, before any LLM call.
  1. Recovery case → HALTED
  2. Escrow milestone → DISPUTED (frozen)
  3. Pending scheduler jobs → cancelled
All three happen in the same synchronous handler, before any await.
"""
from __future__ import annotations
from typing import Any
from backend.app.core.logging import get_logger
from backend.app.ingestion.handlers import register

log = get_logger(__name__)


@register("dispute_created")
def handle_dispute_created(event: dict[str, Any]) -> None:
    resource = event.get("payload", {}).get("resource", {})
    dispute_id = resource.get("id", "")
    disputed_txns = resource.get("disputed_transactions", [])

    log.warning("dispute_created: dispute_id=%s txns=%d", dispute_id, len(disputed_txns))

    try:
        from backend.app.audit import log_event as audit_log

        # Extract linked capture ID
        capture_id = next(
            (t.get("seller_transaction_id", "") for t in disputed_txns
             if t.get("seller_transaction_id")), ""
        )

        # 1. Freeze escrow milestones FIRST (no LLM)
        _freeze_milestones(capture_id, dispute_id)
        # 2. Halt recovery case
        _halt_recovery_case(capture_id, dispute_id)
        # 3. Cancel pending scheduler jobs
        _cancel_pending_jobs(capture_id)

        audit_log("dispute_created", {
            "subject": dispute_id, "actor": "webhook",
            "dispute_id": dispute_id, "capture_id": capture_id,
        })
    except Exception as exc:
        log.error("dispute_created error: %s", exc, exc_info=True)
        raise


def _freeze_milestones(capture_id: str, dispute_id: str) -> None:
    try:
        from backend.app.db.session import get_sync_session
        from backend.app.db.models.projects import Project, Milestone
        from backend.app.audit import log_event as audit_log
        from sqlalchemy import select

        with get_sync_session() as session:
            project = session.execute(
                select(Project).where(Project.paypal_capture_id == capture_id)
            ).scalar_one_or_none()
            if not project:
                return

            milestones = session.execute(
                select(Milestone).where(
                    Milestone.project_id == project.id,
                    Milestone.state.notin_(["RELEASED", "REFUNDED", "DISPUTED"])
                )
            ).scalars().all()

            for m in milestones:
                m.state = "DISPUTED"
            session.commit()

            audit_log("milestones_frozen_by_dispute", {
                "subject": project.id, "actor": "webhook",
                "dispute_id": dispute_id, "count": len(milestones),
            })
    except Exception as exc:
        log.error("_freeze_milestones error: %s", exc, exc_info=True)


def _halt_recovery_case(capture_id: str, dispute_id: str) -> None:
    try:
        from backend.app.stubs.repositories import case_repo
        from backend.app.recovery.state_machine import halt_case

        for case in case_repo.list_all():
            state = case.get("state", "")
            if state in ("OPEN", "RECONCILING", "DIAGNOSED", "ACTION_SENT", "AWAITING_RESULT"):
                halt_case(case["id"],
                          reason=f"dispute_created:{dispute_id}",
                          actor="webhook")
                log.info("_halt_recovery_case: halted case %s", case["id"])
    except Exception as exc:
        log.error("_halt_recovery_case error: %s", exc, exc_info=True)


def _cancel_pending_jobs(subject_id: str) -> None:
    try:
        from backend.app.db.session import get_sync_session
        from backend.app.db.models.support import ScheduledAction
        from sqlalchemy import update

        with get_sync_session() as session:
            result = session.execute(
                update(ScheduledAction)
                .where(ScheduledAction.case_id == subject_id,
                       ScheduledAction.status == "pending")
                .values(status="cancelled")
                .returning(ScheduledAction.id)
            )
            cancelled = [r[0] for r in result]
            session.commit()
            if cancelled:
                log.info("_cancel_pending_jobs: cancelled %d jobs", len(cancelled))
    except Exception as exc:
        log.error("_cancel_pending_jobs error: %s", exc, exc_info=True)


@register("dispute_updated")
def handle_dispute_updated(event: dict[str, Any]) -> None:
    resource = event.get("payload", {}).get("resource", {})
    dispute_id = resource.get("id", "")
    try:
        from backend.app.audit import log_event as audit_log
        audit_log("dispute_updated", {
            "subject": dispute_id, "actor": "webhook",
            "dispute_id": dispute_id, "status": resource.get("status", ""),
        })
    except Exception as exc:
        log.error("dispute_updated error: %s", exc, exc_info=True)


@register("dispute_resolved")
def handle_dispute_resolved(event: dict[str, Any]) -> None:
    resource = event.get("payload", {}).get("resource", {})
    dispute_id = resource.get("id", "")
    outcome = resource.get("dispute_outcome", {}).get("outcome_code", "UNKNOWN")
    log.info("dispute_resolved: id=%s outcome=%s", dispute_id, outcome)
    try:
        from backend.app.audit import log_event as audit_log
        audit_log("dispute_resolved", {
            "subject": dispute_id, "actor": "webhook",
            "dispute_id": dispute_id, "outcome": outcome,
        })
    except Exception as exc:
        log.error("dispute_resolved error: %s", exc, exc_info=True)
```

---

## STEP 12 — Reputation Full Wiring (Nov 7)

In `backend/app/recovery/bridges.py`, inside `on_escrow_case_state_change()`, add after the state check:

```python
# After case transitions to RECOVERED:
if new_state == "RECOVERED":
    try:
        from backend.app.reputation.ledger import record_event as rep_event
        customer_id = case.get("customer_id", "")
        if customer_id:
            rep_event(customer_id, "recovered")
    except Exception as rep_exc:
        log.warning("Reputation update failed (non-fatal): %s", rep_exc)
```

The `payout_item_succeeded` handler (Step 2) already fires `rep_event(freelancer_id, "on_time_release")`.

---

## STEP 13 — Write ADR Docs (Nov 7–8)

```bash
mkdir -p e:\Projects\ProofPay\docs\adr
```

Create stubs for `ADR-001` through `ADR-007`. Minimum viable content per file:

```markdown
# ADR-001: Release Path — Payouts or Orders+Invoicing

**Status:** Decided  
**Date:** 2026-11-03  
**Decision:** [rest | fallback]  
**Reason:** [Payouts enabled / Payouts 403 → Orders+Invoicing fallback]
```

Files: `ADR-001-release-path.md`, `ADR-002-mcp-vs-rest.md`, `ADR-003-static-web-export.md`,
`ADR-004-llm-provider.md`, `ADR-005-aggrid-edition.md`, `ADR-006-hosting.md`, `ADR-007-auto-release-timer.md`

---

## STEP 14 — Security Pass (Nov 9)

### Tighten CORS in `main.py`

```python
# Replace allow_origins=["*"] with:
from backend.app.core.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_base_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
```

### Security checklist

```bash
# 1. Scan git history for secrets (never committed, but verify)
git log --all --full-history -- .env

# 2. Verify DEMO_MODE gates
grep -r "sim/events\|demo_reset\|advance_clock" backend/app/api/ \
  | grep -v "demo_mode\|DEMO_MODE"

# 3. Re-run import boundary check
pytest backend/tests/unit/test_import_linter.py -v

# 4. Check webhook signature is never bypassed in production
grep -r "skip.*signature\|verify.*False" backend/app/ingestion/
```

---

## STEP 15 — Postman Collection v1 (Nov 9)

Add to `postman/` collection — folders:

1. **Auth** — token fetch (manual curl)
2. **Orders** — create project → approve × 2 → fund → capture
3. **Payouts** — submit → poll submission → release
4. **Webhooks** — `POST /sim/events` for each event type
5. **Idempotency** — same webhook 5× → assert 1 ledger entry
6. **Refund** — `POST /milestones/{id}/refund`
7. **Policy block** — over-limit release → assert 403 + blocked_by

Newman CI run (add to `.github/workflows/newman.yml`):
```bash
newman run postman/ProofPay.json \
  --environment postman/env.json \
  --reporters cli,junit \
  --reporter-junit-export postman/results.xml
```

---

## Complete File Change Map

| File | Action | Step |
|---|---|---|
| `backend/app/agents/scoping/__init__.py` | CREATE | 1 |
| `backend/app/agents/scoping/agent.py` | CREATE (or place Dev 2 file) | 1 |
| `backend/app/agents/verifier/__init__.py` | CREATE | 1 |
| `backend/app/agents/verifier/agent.py` | CREATE (or place Dev 2 file) | 1 |
| `backend/app/api/projects.py` | EDIT — wire scoping into `create_project` | 1e |
| `backend/app/ingestion/handlers/payout_events.py` | EDIT — complete TODO → RELEASED | 2 |
| `backend/app/ingestion/handlers/capture_denied.py` | EDIT — complete `capture_refunded` | 2 |
| `backend/scripts/export_openapi.py` | CREATE | 3 |
| `contracts/openapi.json` | GENERATE | 3 |
| `backend/app/api/submissions.py` | CREATE | 4 |
| `backend/app/main.py` | EDIT — mount submissions router, tighten CORS | 4, 14 |
| `backend/app/executor/core.py` | EDIT — add REFUND dispatch | 5 |
| `backend/app/scheduler/jobs/handlers.py` | EDIT — add 3 escrow timer jobs | 6 |
| `backend/app/paypal/subscriptions.py` | CREATE | 9 |
| `backend/app/paypal/disputes.py` | CREATE | 10 |
| `backend/app/ingestion/handlers/dispute_events.py` | CREATE | 11 |
| `backend/app/recovery/bridges.py` | EDIT — reputation wiring | 12 |
| `docs/adr/ADR-001` through `ADR-007` | CREATE | 13 |

---

## `.env` Reference (Final)

```bash
# ── Keep PAYPAL_EXEC_MODE=fake on your laptop for ALL feature work ──
# ── Only change to rest= in Render dashboard when running gate scripts ──

PAYPAL_MODE=sandbox
PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com
PAYPAL_CLIENT_ID=                    # fill in Render dashboard only
PAYPAL_CLIENT_SECRET=                # fill in Render dashboard only
PAYPAL_WEBHOOK_ID=                   # fill in Render dashboard only
PAYPAL_EXEC_MODE=fake                # ← keep fake locally always

DEMO_MODE=true
INTERNAL_TICK_TOKEN=dev-tick-token-change-in-prod
```

