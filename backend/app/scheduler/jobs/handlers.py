"""
Scheduler Jobs and Webhook Event Handlers.

Provides:
  - Job Handlers:
      ladder_step, payday_retry, promise_reminder, overdue_invoice_scan,
      escrow_timer, scheduled_eval_run
  - Event Handlers:
      invoice_paid, invoice_cancelled, subscription_payment_failed
All timestamps and time advancement come strictly from the Clock.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.agents.recovery.agent import process_case
from backend.app.recovery.state_machine import create_case_from_trigger, transition
from backend.app.stubs import audit, clock, scheduler
from backend.app.stubs.contracts_stub import CaseState
from backend.app.stubs.repositories import case_repo

ROOT = Path(__file__).resolve().parents[4]
INVOICES_JSON = ROOT / "data" / "generated" / "invoices.json"

_SCANNED_INVOICE_IDS: set[str] = set()


def clear_scanned_invoices() -> None:
    """Clear scanned invoice registry (for test isolation)."""
    _SCANNED_INVOICE_IDS.clear()


# ── Job Handlers ──────────────────────────────────────────────────────────────

def ladder_step(case_id: str, step_index: int = 0) -> dict[str, Any]:
    """Execute the next strategy ladder step for a case."""
    audit.log_event("scheduler_ladder_step_tick", {"case_id": case_id, "step_index": step_index})
    return process_case(case_id=case_id)


def payday_retry(case_id: str) -> dict[str, Any]:
    """Execute payday-aligned payment retry."""
    audit.log_event("scheduler_payday_retry_tick", {"case_id": case_id})
    return process_case(case_id=case_id)


def promise_reminder(case_id: str) -> dict[str, Any]:
    """Execute day-before promise reminder."""
    audit.log_event("scheduler_promise_reminder_tick", {"case_id": case_id})
    return process_case(case_id=case_id)


def overdue_invoice_scan(
    invoices: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Scan for overdue invoices and create a recovery case per invoice.
    Strictly idempotent by invoice ID: scanning twice yields exactly one case per invoice.
    """
    if invoices is not None:
        inv_list = invoices
    elif INVOICES_JSON.exists():
        with open(INVOICES_JSON, "r", encoding="utf-8") as f:
            inv_list = json.load(f)
    else:
        inv_list = []

    created_cases: list[dict[str, Any]] = []

    for inv in inv_list:
        inv_id = str(inv.get("invoice_id") or inv.get("id"))
        if inv_id in _SCANNED_INVOICE_IDS:
            # Already scanned: skip to ensure idempotency
            continue

        # Check existing repo cases
        existing = [
            c for c in case_repo.list_all()
            if c.get("payload", {}).get("invoice_id") == inv_id or c.get("id") == inv_id
        ]
        if existing:
            _SCANNED_INVOICE_IDS.add(inv_id)
            continue

        # Create new case
        case = create_case_from_trigger(
            trigger_type="overdue_invoice",
            event_id=f"scan-inv-{inv_id}",
            payload={
                "invoice_id": inv_id,
                "customer_id": inv.get("customer_id", "CUST-UNKNOWN"),
                "amount_usd": float(inv.get("amount_usd", 100.0)),
                "currency": inv.get("currency", "USD"),
                "due_at": inv.get("due_at"),
            },
        )
        _SCANNED_INVOICE_IDS.add(inv_id)
        created_cases.append(case)

    audit.log_event("overdue_invoice_scan_completed", {
        "scanned_total": len(inv_list),
        "new_cases_created": len(created_cases),
        "timestamp": clock.utcnow().isoformat(),
    })

    return created_cases


def escrow_timer(project_id: str) -> None:
    """Placeholder for escrow project timeout timer; writes audit row."""
    audit.log_event("escrow_timer_tick", {
        "project_id": project_id,
        "timestamp": clock.utcnow().isoformat(),
    })


def scheduled_eval_run() -> None:
    """Placeholder for recurring scheduled model evaluation job; writes audit row."""
    audit.log_event("scheduled_eval_run_tick", {
        "timestamp": clock.utcnow().isoformat(),
    })


# ── Event Handlers ────────────────────────────────────────────────────────────

def invoice_paid(invoice_id: str, amount: float | None = None) -> dict[str, Any] | None:
    """Handle invoice_paid webhook: closes associated case as RECOVERED."""
    matching_cases = [
        c for c in case_repo.list_all()
        if c.get("payload", {}).get("invoice_id") == invoice_id
        or c.get("id") == invoice_id
    ]
    if not matching_cases:
        audit.log_event("invoice_paid_no_case_found", {"invoice_id": invoice_id})
        return None

    case = matching_cases[0]
    if case.get("state") not in (CaseState.RECOVERED, CaseState.HALTED, CaseState.PAID_ELSEWHERE):
        transition(case, to_state=CaseState.RECOVERED, actor="webhook", reason=f"invoice_paid_{invoice_id}")
    return case


def invoice_cancelled(invoice_id: str, reason: str = "customer_cancelled") -> dict[str, Any] | None:
    """Handle invoice_cancelled webhook: closes associated case as UNRECOVERED with reason."""
    matching_cases = [
        c for c in case_repo.list_all()
        if c.get("payload", {}).get("invoice_id") == invoice_id
        or c.get("id") == invoice_id
    ]
    if not matching_cases:
        audit.log_event("invoice_cancelled_no_case_found", {"invoice_id": invoice_id})
        return None

    case = matching_cases[0]
    if case.get("state") not in (CaseState.RECOVERED, CaseState.HALTED, CaseState.PAID_ELSEWHERE):
        transition(case, to_state=CaseState.UNRECOVERED, actor="webhook", reason=f"invoice_cancelled_{reason}")
    return case


def subscription_payment_failed(event_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Handle subscription_payment_failed webhook: opens recovery case."""
    return process_case(
        trigger={
            "trigger_type": "failed_payment",
            "event_id": event_id,
            **payload,
        }
    )


# ── Clock Tick Listener Integration ──────────────────────────────────────────

def _on_clock_tick(new_time: Any) -> None:
    """When clock advances, execute any pending scheduled jobs."""
    jobs = scheduler.get_jobs()
    # Process and execute pending jobs
    for j in list(jobs):
        func_name = j.get("func")
        args = j.get("args", ())
        kwargs = j.get("kwargs", {})
        if func_name == "next_step_job" or "ladder" in func_name:
            case_id = kwargs.get("cid") or kwargs.get("case_id") or (args[0] if args else None)
            scheduler.remove_job(j["id"])
            if case_id:
                try:
                    process_case(case_id=case_id)
                except Exception:
                    pass


clock.register_tick_listener(_on_clock_tick)
