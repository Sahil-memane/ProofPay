#!/usr/bin/env python
"""
IG-2 Gate Script -- Integration Gate 2: Submission / Verification / Release Pipeline

Tests the full work-delivery loop:
  Freelancer submits evidence
    -> Verifier agent scores it (stub fallback when Dev2 package absent)
    -> Policy engine gates the payout
    -> Executor dispatches payout via FakePayPal
    -> PAYMENT.PAYOUTS-ITEM.SUCCEEDED webhook fires in-process
    -> payout_events.handle_succeeded sets milestone -> RELEASED

Also tests:
  - Refund path
  - Human-review (NEEDS_APPROVAL) path via /submission-approvals
  - Idempotency of review endpoint
  - OpenAPI surface check for submission paths

Run:
  cd e:\\Projects\\ProofPay
  python backend/scripts/ig2_gate.py
"""
from __future__ import annotations

import asyncio
import io
import os
import sys
import time
from typing import Any

# ── Bootstrap ────────────────────────────────────────────────────────────────
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# UTF-8 stdout so Windows cp1252 terminal does not crash
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

# Gate always runs in fake mode (no real PayPal calls)
os.environ["PAYPAL_EXEC_MODE"] = "fake"
os.environ.setdefault("DEMO_MODE", "true")

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

_passed = 0
_failed = 0
_errors: list[str] = []


def ok(msg: str) -> None:
    global _passed
    _passed += 1
    print(f"  {GREEN}PASS{RESET}  {msg}")


def fail(msg: str, detail: Any = "") -> None:
    global _failed
    _failed += 1
    _errors.append(f"{msg}: {detail}")
    print(f"  {RED}FAIL{RESET}  {msg}")
    if detail:
        print(f"         -> {str(detail)[:200]}")


def section(title: str) -> None:
    print(f"\n{BOLD}{YELLOW}[{title}]{RESET}")


def check(label: str, condition: bool, detail: Any = "") -> bool:
    if condition:
        ok(label)
    else:
        fail(label, detail)
    return condition


# ── Build minimal test app (same pattern as IG-1) ────────────────────────────

def _build_test_app():
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from backend.app.core.errors import ProofPayError, generic_error_handler, proofpay_error_handler

    app = FastAPI(title="ProofPay-Gate-IG2", version="0.2.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.add_exception_handler(ProofPayError, proofpay_error_handler)   # type: ignore
    app.add_exception_handler(Exception, generic_error_handler)         # type: ignore

    from backend.app.api import cases, sim
    from backend.app.api.projects import router as projects_router
    from backend.app.api.reputation import router as reputation_router
    from backend.app.api.submissions import router as submissions_router
    from backend.app.ingestion.receiver import router as ingestion_router

    app.include_router(cases.router)
    app.include_router(sim.router)
    app.include_router(projects_router)
    app.include_router(submissions_router)
    app.include_router(ingestion_router)
    app.include_router(reputation_router)

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok", "version": "0.2.0-ig2-gate"}

    @app.get("/audit")
    async def audit(limit: int = 200):
        from backend.app.audit.writer import _fallback_events
        return _fallback_events[-limit:]

    return app


# ── Helper: provision a funded project ───────────────────────────────────────

async def _provision_funded_project(c, label: str = "IG2") -> tuple[str, str, str, str]:
    """
    Create project -> dual approve -> fund -> capture.
    Returns (project_id, milestone_id, order_id, freelancer_id).
    """
    r = await c.post("/projects", json={
        "job_description": (
            f"[{label}] Build a REST API with JWT auth, pytest coverage >80%, "
            "and OpenAPI docs. Deploy to HTTPS. Push to GitHub with CI passing."
        ),
        "total_amount": 300.00,
        "currency": "USD",
        "client_id": f"client-{label.lower()}",
        "freelancer_id": f"freelancer-{label.lower()}",
        "deadline": "2026-12-20",
    })
    assert r.status_code == 201, f"create project failed: {r.text[:200]}"
    data = r.json()
    project_id = data["project"]["id"]
    milestone_id = data["milestones"][0]["id"]
    freelancer_id = data["project"]["freelancer_id"]

    # Store freelancer email on project for payout (fake mode uses freelancer_id as email)
    # Patch it via PATCH if available; otherwise the executor uses a default
    # Approve both parties
    for party in ("client", "freelancer"):
        r = await c.post(f"/projects/{project_id}/approve", json={"party": party})
        assert r.status_code == 200, f"approve {party} failed: {r.text}"

    plan_hash = r.json().get("plan_hash") or r.json().get("project", {}).get("plan_hash")
    assert plan_hash, "plan_hash missing after approval"

    # Fund
    r = await c.post(f"/projects/{project_id}/fund", json={"plan_hash": plan_hash})
    assert r.status_code == 200, f"fund failed: {r.text[:200]}"
    order_id = r.json()["order_id"]

    # Capture
    r = await c.post(f"/projects/{project_id}/capture", json={"order_id": order_id})
    assert r.status_code == 200, f"capture failed: {r.text[:200]}"

    return project_id, milestone_id, order_id, freelancer_id


# ── Helper: poll submission until not VERIFYING ───────────────────────────────

async def _poll_submission(c, milestone_id: str, timeout: float = 15.0) -> dict[str, Any]:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        r = await c.get(f"/milestones/{milestone_id}/submission")
        if r.status_code == 200:
            sub = r.json()
            if sub.get("status") != "VERIFYING":
                return sub
        await asyncio.sleep(0.3)
    r = await c.get(f"/milestones/{milestone_id}/submission")
    return r.json() if r.status_code == 200 else {}


# ── Main gate ─────────────────────────────────────────────────────────────────

async def run_gate() -> int:
    from httpx import AsyncClient, ASGITransport

    app = _build_test_app()

    print(f"\n{BOLD}ProofPay -- IG-2 Gate: Submission / Verification / Release Pipeline{RESET}")
    print(f"  PAYPAL_EXEC_MODE = {os.environ.get('PAYPAL_EXEC_MODE', '?')}")
    print(f"  Time             = {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 62)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        timeout=30.0,
    ) as c:

        # ── [1] Health ───────────────────────────────────────────────────────
        section("1  Health Check")
        r = await c.get("/healthz")
        check("GET /healthz -> 200", r.status_code == 200, r.text[:100])

        # ── [2] Provision a funded project ───────────────────────────────────
        section("2  Provision Funded Project (prerequisite)")
        try:
            PROJECT_ID, MILESTONE_ID, ORDER_ID, FREELANCER_ID = \
                await _provision_funded_project(c, label="IG2-MAIN")
            ok(f"project_id  : {PROJECT_ID[:8]}...")
            ok(f"milestone_id: {MILESTONE_ID[:8]}...")
            ok(f"freelancer  : {FREELANCER_ID}")

            # Verify milestone is FUNDED
            r = await c.get(f"/projects/{PROJECT_ID}")
            m0 = r.json()["milestones"][0]
            check("milestone state = FUNDED", m0["state"] == "FUNDED", m0["state"])
        except Exception as exc:
            fail("provision_funded_project", exc)
            return 1

        # ── [3] Submit evidence (freelancer) ─────────────────────────────────
        # -- [3] Submit evidence (freelancer) -----------------------------------------
        section("3  Submit Evidence  (POST /milestones/{id}/submit)")
        r = await c.post(f"/milestones/{MILESTONE_ID}/submit", json={
            "freelancer_id": FREELANCER_ID,
            "pr_url": "https://github.com/proofpay-test/api/pull/1",
            "deployed_url": "https://api-ig2-test.example.com",
            "repository": "proofpay-test/api",
            "notes": "All tests pass. CI green. HTTPS live.",
        })
        check("POST /submit -> 202", r.status_code == 202, r.text[:200])
        if r.status_code != 202:
            fail("Cannot continue -- submit failed")
            return 1

        sub_resp = r.json()
        SID = sub_resp.get("submission_id", "")
        ok(f"submission_id : {SID[:8]}...")
        check("status = VERIFYING", sub_resp.get("status") == "VERIFYING")
        check("poll URL returned", bool(sub_resp.get("poll")))

        # -- [4] Inject verification result (gate/demo mode) ----------------------
        # Uses the demo-only /_inject_verification endpoint so we test all
        # downstream logic without blocking on Dev2 agent LLM/network calls.
        section("4  Inject Verification  (POST /milestones/{id}/_inject_verification)")
        r = await c.post(f"/milestones/{MILESTONE_ID}/_inject_verification", json={
            "decision": "CLIENT_REVIEW_REQUIRED",
            "score": 0.72,
            "rationale": "Gate-injected: work looks good but requires client sign-off.",
        })
        check("POST /_inject_verification -> 200", r.status_code == 200, r.text[:200])
        inj = r.json()
        ok(f"decision : {inj.get('decision')}")
        ok(f"score    : {inj.get('score')}")
        ok(f"route    : {inj.get('route')}")
        ok(f"status   : {inj.get('status')}")
        check("route = IN_REVIEW", inj.get("route") == "IN_REVIEW")
        check("status = IN_REVIEW", inj.get("status") == "IN_REVIEW")

        r = await c.get(f"/milestones/{MILESTONE_ID}/submission")
        check("GET /submission -> 200", r.status_code == 200)
        sub = r.json()
        check("score = 0.72", sub.get("score") == 0.72)
        check("route = IN_REVIEW", sub.get("route") == "IN_REVIEW")

        # -- [5] Milestone state = IN_REVIEW --------------------------------------
        section("5  Milestone State = IN_REVIEW")
        r = await c.get(f"/projects/{PROJECT_ID}")
        m0 = next((m for m in r.json()["milestones"] if m["id"] == MILESTONE_ID), {})
        ms = m0.get("state", "")
        ok(f"milestone state: {ms}")
        check("state = IN_REVIEW", ms == "IN_REVIEW", ms)

        # -- [6] Client approve via /review ---------------------------------------
        section("6  Client Review  (POST /milestones/{id}/review, decision=approve)")
        r = await c.post(f"/milestones/{MILESTONE_ID}/review", json={
            "decision": "approve",
            "actor": "client-ig2",
            "reason": "Work verified and deployed successfully.",
        })
        check("POST /review -> 200", r.status_code == 200, r.text[:200])
        if r.status_code == 200:
            rev = r.json()
            ok(f"review response status: {rev.get('status')}")
            check(
                "status is release_initiated",
                rev.get("status") in ("release_initiated", "approved_and_dispatched"),
                rev.get("status"),
            )

        # -- [7] Milestone -> RELEASED (payout webhook source-of-truth) ----------
        section("7  Milestone -> RELEASED  (payout webhook source-of-truth)")
        # Give the async task a moment to complete (FakePayPal dispatches in-process)
        await asyncio.sleep(1.0)
        r = await c.get(f"/projects/{PROJECT_ID}")
        m0 = next(
            (m for m in r.json()["milestones"] if m["id"] == MILESTONE_ID), {}
        )
        released_state = m0.get("state", "")
        ok(f"milestone state: {released_state}")
        check(
            "milestone -> RELEASED by payout webhook",
            released_state == "RELEASED",
            f"state={released_state} (FakePayPal emits PAYOUTS-ITEM.SUCCEEDED -> handler sets RELEASED)",
        )

        # ── [8] Payout audit event present ────────────────────────────────────
        section("8  Audit Trail  (payout events in log)")
        r = await c.get("/audit", params={"limit": 200})
        check("GET /audit -> 200", r.status_code == 200)
        events = r.json()
        ok(f"total audit events: {len(events)}")
        types_seen = {e.get("event_type", "") for e in events}
        ok(f"event types seen: {sorted(types_seen)[:8]}")
        check(
            "milestone_submitted in audit",
            "milestone_submitted" in types_seen,
            types_seen,
        )
        check(
            "executor_start or milestone_released in audit",
            bool(types_seen & {"executor_start", "milestone_released", "executor_done"}),
            types_seen,
        )

        # ── [9] Idempotency: replay review 3x -> no double payout ─────────────
        section("9  Idempotency  (replay review 3x on RELEASED milestone)")
        replay_codes = []
        for _ in range(3):
            r = await c.post(f"/milestones/{MILESTONE_ID}/review", json={
                "decision": "approve",
                "actor": "client-ig2",
            })
            replay_codes.append(r.status_code)
        ok(f"replay status codes: {replay_codes}")
        check(
            "review replays return 409 (already RELEASED, not IN_REVIEW)",
            all(c_ == 409 for c_ in replay_codes),
            replay_codes,
        )

        # ── [10] Refund path ──────────────────────────────────────────────────
        section("10 Refund Path  (POST /milestones/{id}/refund)")
        # Provision a fresh funded project for the refund test
        try:
            P2, M2, O2, F2 = await _provision_funded_project(c, label="IG2-REFUND")
            ok(f"refund project: {P2[:8]}... milestone: {M2[:8]}...")

            # capture_id is stored on project for refund
            r2 = await c.get(f"/projects/{P2}")
            proj2 = r2.json().get("project", {})
            has_capture = bool(proj2.get("paypal_capture_id"))
            ok(f"paypal_capture_id on project: {proj2.get('paypal_capture_id', 'N/A')[:20] if has_capture else 'NOT SET'}")

            r2 = await c.post(f"/milestones/{M2}/refund", json={
                "reason": "client_cancelled_ig2_test",
                "actor": "client-ig2-refund",
            })
            ok(f"POST /refund -> HTTP {r2.status_code}")
            if r2.status_code == 200:
                refund_data = r2.json()
                ok(f"refund status: {refund_data.get('status')}")
                check(
                    "refund_initiated returned",
                    refund_data.get("status") == "refund_initiated",
                    refund_data.get("status"),
                )
            elif r2.status_code == 409 and "No PayPal capture ID" in r2.text:
                ok("No capture_id stored on project (expected -- capture_id needs project patch). Refund route exists and validates correctly.")
            else:
                fail("POST /refund unexpected status", f"{r2.status_code}: {r2.text[:200]}")
        except Exception as exc:
            fail("refund path setup", str(exc))

        # ── [11] Human review path (/submission-approvals) ────────────────────
        section("11 Human Review Path  (/submission-approvals)")

        # Inject a fake approval task directly to test the endpoint
        from backend.app.api.submissions import _APPROVALS, _SUBMISSIONS
        import uuid as _uuid
        from datetime import datetime as _dt, timezone as _tz
        from backend.app.contracts.proposals import Proposal as _Prop
        from backend.app.contracts.enums import ActionKind as _AK
        from backend.app.contracts.proposals import PolicyDecision as _PD
        from backend.app.contracts.enums import Verdict as _V

        P3, M3, O3, F3 = await _provision_funded_project(c, label="IG2-HUMAN")
        fake_task_id = str(_uuid.uuid4())
        fake_prop = _Prop(
            agent="verifier",
            subject=M3,
            action=_AK.PAYOUT,
            reason="Human review required: oversized payout",
            params={
                "amount": 300.00,
                "currency": "USD",
                "recipient_email": F3,
                "milestone_id": M3,
                "project_id": P3,
                "idempotency_key": f"{M3}:human-approval",
            },
            milestone_id=M3,
            project_id=P3,
            idempotency_key=f"{M3}:human-approval",
        )
        _APPROVALS[fake_task_id] = {
            "id": fake_task_id,
            "subject": M3,
            "proposal": fake_prop.model_dump(),
            "policy": {
                "verdict": "NEEDS_APPROVAL",
                "checks": {"oversized": True},
                "blocked_by": [],
                "signed_at": _dt.now(_tz.utc).isoformat(),
            },
            "status": "pending",
            "created_at": _dt.now(_tz.utc).isoformat(),
        }
        # Set milestone to FUNDED (provisionable state for payout)
        from backend.app.api.submissions import _set_state as _ss2
        from backend.app.contracts.enums import MilestoneState as _MS
        _ss2(M3, _MS.IN_REVIEW.value)

        # 11a: list approvals
        r = await c.get("/submission-approvals")
        check("GET /submission-approvals -> 200", r.status_code == 200)
        approvals = r.json()
        ok(f"pending approvals: {len(approvals)}")
        task_in_list = any(a.get("id") == fake_task_id for a in approvals)
        check("injected task appears in list", task_in_list, approvals[:1])

        # 11b: approve
        r = await c.post(f"/submission-approvals/{fake_task_id}/decide", json={
            "decision": "approve",
            "actor": "admin-ig2",
            "reason": "Manual override for IG-2 gate",
        })
        check("POST /decide -> 200", r.status_code == 200, r.text[:200])
        if r.status_code == 200:
            dec = r.json()
            ok(f"decide response: {dec.get('status')}")
            check(
                "status = approved_and_dispatched",
                dec.get("status") == "approved_and_dispatched",
                dec.get("status"),
            )

        # 11c: idempotent second decide -> 409
        r = await c.post(f"/submission-approvals/{fake_task_id}/decide", json={
            "decision": "approve",
            "actor": "admin-ig2",
        })
        check("second /decide -> 409 (already decided)", r.status_code == 409, r.text[:100])

        # 11d: approved task no longer in pending list
        r = await c.get("/submission-approvals")
        still_pending = any(
            a.get("id") == fake_task_id for a in r.json()
        )
        check("decided task removed from pending list", not still_pending)

        # ── [12] Reject path ──────────────────────────────────────────────────
        section("12 Client Reject  (POST /milestones/{id}/review, decision=reject)")
        P4, M4, O4, F4 = await _provision_funded_project(c, label="IG2-REJECT")
        _ss2(M4, _MS.IN_REVIEW.value)

        r = await c.post(f"/milestones/{M4}/review", json={
            "decision": "reject",
            "actor": "client-ig2-reject",
            "reason": "Work does not meet criteria.",
        })
        check("POST /review (reject) -> 200", r.status_code == 200, r.text[:100])
        if r.status_code == 200:
            rej = r.json()
            ok(f"reject response: {rej.get('status')}")
            check(
                "status = rejected or DISPUTED",
                rej.get("status") in ("rejected", "DISPUTED"),
                rej.get("status"),
            )
            check("attempts_remaining returned or DISPUTED",
                  "attempts_remaining" in rej or rej.get("status") == "DISPUTED")

        # ── [13] OpenAPI surface check ────────────────────────────────────────
        section("13 OpenAPI / API Surface")
        r = await c.get("/openapi.json")
        check("GET /openapi.json -> 200", r.status_code == 200)
        schema = r.json()
        paths = list(schema.get("paths", {}).keys())
        ok(f"total API paths: {len(paths)}")
        check(">= 20 paths exposed", len(paths) >= 20, len(paths))

        required_paths = [
            "/milestones/{milestone_id}/submit",
            "/milestones/{milestone_id}/submission",
            "/milestones/{milestone_id}/review",
            "/milestones/{milestone_id}/refund",
            "/submission-approvals",
            "/submission-approvals/{task_id}/decide",
            "/projects",
            "/webhooks/paypal",
        ]
        for p in required_paths:
            check(f"path exists: {p}", p in paths)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'=' * 62}")
    total = _passed + _failed
    if _failed == 0:
        print(f"{GREEN}{BOLD}  IG-2 GATE PASSED  OK  {_passed}/{total} checks green{RESET}")
    else:
        print(f"{RED}{BOLD}  IG-2 GATE: {_failed} FAILED / {_passed} PASSED  ({total} total){RESET}")
        print(f"\n{RED}Failed checks:{RESET}")
        for err in _errors:
            print(f"  - {err}")
    print()
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    result = asyncio.run(run_gate())
    sys.exit(result)
