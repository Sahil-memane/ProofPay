"""
Simulator & Demo API Router for Dev 4 (Step 11).

Endpoints (active only when DEMO_MODE is enabled, otherwise returns 404):
  POST /demo/inject-failure - Inject synthetic payment failure trigger
  POST /demo/run-simulator  - Direct trigger of customer response simulation
  POST /demo/advance-clock  - Fast-forward the FakeClock by days/hours
  POST /demo/reset          - Clean reset of environment and test fixtures
"""
from __future__ import annotations

import os
import random
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.agents.recovery.agent import process_case
from backend.app.channels.outbox import clear_outbox
from backend.app.recovery.state_machine import clear_trigger_dedup_cache, create_case_from_trigger
from backend.app.simulator.profiles import respond
from backend.app.stubs import audit, clock, llm, policy, repositories, scheduler

router = APIRouter(tags=["demo"])

# Demo mode toggle — defaults to False (or reads DEMO_MODE env)
_DEMO_MODE: bool = os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes")


def set_demo_mode(enabled: bool) -> None:
    """Programmatically toggle demo mode (for test fixtures)."""
    global _DEMO_MODE
    _DEMO_MODE = enabled


def get_demo_mode() -> bool:
    return _DEMO_MODE


def _check_demo_mode() -> None:
    if not _DEMO_MODE:
        raise HTTPException(
            status_code=404,
            detail="Demo endpoints are disabled. Enable DEMO_MODE to use this endpoint.",
        )


# ── Request Schemas ───────────────────────────────────────────────────────────

class InjectFailureRequest(BaseModel):
    customer_id: str = Field(default="CUST-DEMO-01")
    failure_code: str = Field(default="insufficient_funds")
    amount_usd: float = Field(default=125.0)
    currency: str = Field(default="USD")
    invoice_id: str | None = None


class RunSimulatorRequest(BaseModel):
    case_id: str
    action: str = Field(default="send_reminder")
    seed: int = Field(default=42)


class AdvanceClockRequest(BaseModel):
    days: float = Field(default=0.0)
    hours: float = Field(default=0.0)


# ── Demo Endpoints ────────────────────────────────────────────────────────────

@router.post("/demo/inject-failure")
def demo_inject_failure(req: InjectFailureRequest) -> dict[str, Any]:
    _check_demo_mode()

    inv_id = req.invoice_id or f"INV-{req.customer_id}-{random.randint(1000, 9999)}"
    case = create_case_from_trigger(
        trigger_type="failed_payment",
        event_id=f"demo-evt-{inv_id}",
        payload={
            "customer_id": req.customer_id,
            "failure_code": req.failure_code,
            "amount_usd": req.amount_usd,
            "currency": req.currency,
            "invoice_id": inv_id,
        },
    )

    # Trigger agent process
    processed = process_case(case_id=case["id"])
    return {
        "status": "failure_injected",
        "case_id": case["id"],
        "case": processed,
    }


@router.post("/demo/run-simulator")
def demo_run_simulator(req: RunSimulatorRequest) -> dict[str, Any]:
    _check_demo_mode()

    case = repositories.case_repo.get(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {req.case_id} not found")

    rng = random.Random(req.seed)
    sim_event = respond(
        case=case,
        action=req.action,
        now=clock.utcnow(),
        rng=rng,
    )

    return {
        "case_id": req.case_id,
        "action": req.action,
        "event_type": sim_event.event_type.value,
        "message": sim_event.message,
        "meta": sim_event.meta,
    }


@router.post("/demo/advance-clock")
def demo_advance_clock(req: AdvanceClockRequest) -> dict[str, Any]:
    _check_demo_mode()

    delta = timedelta(days=req.days, hours=req.hours)
    new_dt = clock.advance_time(delta)
    return {
        "advanced_by": {"days": req.days, "hours": req.hours},
        "current_time": new_dt.isoformat(),
    }


@router.post("/demo/reset")
def demo_reset_endpoint() -> dict[str, Any]:
    _check_demo_mode()

    # Clear state
    repositories.case_repo.reset()
    repositories.contact_repo._store.clear()
    clock.reset()
    scheduler.reset()
    audit.clear()
    clear_outbox()
    llm.reset()
    policy.reset_daily_cap()
    clear_trigger_dedup_cache()

    return {
        "status": "demo_environment_reset_complete",
        "timestamp": clock.utcnow().isoformat(),
    }
