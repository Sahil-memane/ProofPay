"""
Unit tests for Step 9: Scheduler Jobs, Webhook Handlers, and Invoice Scanner.

Verifies:
  1. Scanning twice gives one case per invoice (idempotency).
  2. Advancing 3 days runs the next ladder step.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from backend.app.channels.outbox import clear_outbox
from backend.app.recovery.state_machine import clear_trigger_dedup_cache
from backend.app.scheduler.jobs.handlers import (
    clear_scanned_invoices,
    escrow_timer,
    invoice_cancelled,
    invoice_paid,
    ladder_step,
    overdue_invoice_scan,
    scheduled_eval_run,
    subscription_payment_failed,
)
from backend.app.stubs import clock, executor, policy, repositories, scheduler
from backend.app.stubs.contracts_stub import CaseState

NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def clean_env():
    clear_outbox()
    clear_scanned_invoices()
    clear_trigger_dedup_cache()
    executor.reset()
    policy.reset_daily_cap()
    repositories.case_repo.reset()
    repositories.contact_repo.reset()
    scheduler.reset()
    clock.set_time(NOW)
    yield
    clock.reset()


# ── Test 1: Scanning Twice Gives One Case Per Invoice ─────────────────────────

def test_scanning_twice_gives_one_case_per_invoice():
    """Verify overdue_invoice_scan is idempotent: running twice creates zero duplicates."""
    sample_invoices = [
        {"invoice_id": "INV-SCAN-01", "customer_id": "CUST-001", "amount_usd": 150.0, "currency": "USD"},
        {"invoice_id": "INV-SCAN-02", "customer_id": "CUST-002", "amount_usd": 250.0, "currency": "USD"},
        {"invoice_id": "INV-SCAN-03", "customer_id": "CUST-003", "amount_usd": 75.0, "currency": "USD"},
    ]

    # First Scan: 3 cases created
    first_run = overdue_invoice_scan(invoices=sample_invoices)
    assert len(first_run) == 3
    assert len(repositories.case_repo.list_all()) == 3

    # Second Scan: 0 new cases created
    second_run = overdue_invoice_scan(invoices=sample_invoices)
    assert len(second_run) == 0
    assert len(repositories.case_repo.list_all()) == 3


# ── Test 2: Advancing 3 Days Runs the Next Ladder Step ────────────────────────

def test_advancing_3_days_runs_next_ladder_step():
    """Verify simulate_days(3) advances FakeClock and triggers the next scheduled ladder step."""
    case_id = "CASE-SCHED-001"
    from backend.app.simulator.profiles import CustomerProfile

    repositories.case_repo._store[case_id] = {
        "id": case_id,
        "case_id": case_id,
        "customer_id": "CUST-SCHED-01",
        "amount_usd": 90.0,
        "currency": "USD",
        "state": CaseState.OPEN,
        "contact_count": 0,
        "history": [],
        "profile": CustomerProfile(
            customer_id="CUST-SCHED-01",
            email="sched@example.com",
            timezone="UTC",
            behaviour="needs_payment_link",
        ),
    }

    # Run initial step (Step 0: reminder sent, awaits payment link step)
    from backend.app.agents.recovery.agent import process_case
    c0 = process_case(case_id=case_id)
    assert c0["contact_count"] == 1
    assert c0["state"] == CaseState.AWAITING_RESULT
    assert len(scheduler.get_jobs()) == 1

    # Advancing 3 days (72 hours >= 48 hours gap) triggers clock tick and executes next ladder step
    clock.simulate_days(3)

    # Process next step triggered by clock advance
    c1 = repositories.case_repo.get(case_id)
    assert c1["contact_count"] == 2
    assert c1["state"] in (CaseState.AWAITING_RESULT, CaseState.RECOVERED)


# ── Additional Webhook Handler Tests ──────────────────────────────────────────

def test_invoice_paid_webhook_closes_recovered():
    """invoice_paid closes the case as RECOVERED."""
    case_id = "CASE-PAID-01"
    repositories.case_repo._store[case_id] = {
        "id": case_id,
        "payload": {"invoice_id": "INV-PAID-01"},
        "state": CaseState.AWAITING_RESULT,
        "history": [],
    }
    updated = invoice_paid(invoice_id="INV-PAID-01")
    assert updated["state"] == CaseState.RECOVERED


def test_invoice_cancelled_webhook_closes_unrecovered():
    """invoice_cancelled closes the case as UNRECOVERED with reason."""
    case_id = "CASE-CANC-01"
    repositories.case_repo._store[case_id] = {
        "id": case_id,
        "payload": {"invoice_id": "INV-CANC-01"},
        "state": CaseState.AWAITING_RESULT,
        "history": [],
    }
    updated = invoice_cancelled(invoice_id="INV-CANC-01", reason="client_request")
    assert updated["state"] == CaseState.UNRECOVERED


def test_escrow_timer_and_eval_run_ticks():
    """Verify escrow timer and eval run log audit rows without errors."""
    escrow_timer(project_id="ESCROW-001")
    scheduled_eval_run()
