"""
Scenario Tests for Recovery Agent (Step 8).

Verifies the 3 core required recovery agent scenarios:
  1. A dispute mid-ladder halts the case and nothing more is proposed.
  2. No case exceeds 4 contacts or has two contacts under 48 hours apart.
  3. Already-paid customers get zero contacts.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
import pytest

from backend.app.agents.recovery.agent import process_case
from backend.app.channels.outbox import clear_outbox, list_messages
from backend.app.recovery.state_machine import clear_trigger_dedup_cache
from backend.app.simulator.profiles import CustomerProfile
from backend.app.stubs import clock, executor, llm, policy, repositories, scheduler
from backend.app.stubs.contracts_stub import CaseState

NOW = datetime(2025, 6, 1, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def setup_test_env():
    clear_outbox()
    executor.reset()
    policy.reset_daily_cap()
    repositories.case_repo.reset()
    repositories.contact_repo.reset()
    scheduler.reset()
    llm.reset()
    clear_trigger_dedup_cache()
    clock.set_time(NOW)
    yield
    clock.reset()


# ── Scenario 1: A Dispute Mid-Ladder Halts the Case ───────────────────────────

def test_scenario_dispute_mid_ladder_halts_and_nothing_more_proposed():
    """
    Scenario 1: Customer disputes mid-ladder.
    The case transitions to HALTED, all scheduled next steps are cancelled,
    and no further proposals or contacts are executed.
    """
    case_id = "CASE-SCENARIO-DISPUTE"
    repositories.case_repo._store[case_id] = {
        "id": case_id,
        "case_id": case_id,
        "customer_id": "CUST-DISP-99",
        "amount_usd": 120.0,
        "currency": "USD",
        "state": CaseState.OPEN,
        "contact_count": 0,
        "history": [],
        "profile": CustomerProfile(
            customer_id="CUST-DISP-99",
            email="dispute@example.com",
            timezone="America/New_York",
            behaviour="disputes_if_chased_early",
        ),
        "due_date": NOW - timedelta(days=1),  # Chased within 3 days -> triggers dispute
    }

    # Step 1: Process the case
    halted_case = process_case(case_id=case_id)

    # Must be in HALTED state
    assert halted_case["state"] == CaseState.HALTED

    # Scheduled jobs for this case must be cancelled (or empty)
    pending_jobs = [j for j in scheduler.get_jobs() if case_id in str(j)]
    assert len(pending_jobs) == 0, "No scheduled jobs should remain after halt"

    # Attempt to re-process the case: nothing more should be proposed or executed
    executed_before = len(executor.get_executed())
    re_processed = process_case(case_id=case_id)
    assert re_processed["state"] == CaseState.HALTED
    assert len(executor.get_executed()) == executed_before, "No new actions proposed after halt"


# ── Scenario 2: No Case Exceeds 4 Contacts or Has Contacts < 48 Hours Apart ───

def test_scenario_contact_cap_and_48h_gap_enforcement():
    """
    Scenario 2: No case exceeds 4 contacts, and no two contacts are made under 48 hours apart.
    """
    case_id = "CASE-SCENARIO-CAP"
    repositories.case_repo._store[case_id] = {
        "id": case_id,
        "case_id": case_id,
        "customer_id": "CUST-IGNORES-99",
        "amount_usd": 85.0,
        "currency": "USD",
        "state": CaseState.OPEN,
        "contact_count": 0,
        "last_contact_at": None,
        "history": [],
        "profile": CustomerProfile(
            customer_id="CUST-IGNORES-99",
            email="ignore@example.com",
            timezone="UTC",
            behaviour="ignores_everything",  # Never responds
        ),
    }

    # Attempt to run process_case multiple times
    # 1st Contact at t=0
    c1 = process_case(case_id=case_id)
    assert c1["contact_count"] == 1
    assert c1["state"] == CaseState.AWAITING_RESULT

    # Immediate second call without advancing time (only 1 hour later) -> 48h gap policy rejects!
    clock.advance_time(timedelta(hours=1))
    c_early = process_case(case_id=case_id)
    # Contact count must not increase because 48h gap was not met
    assert c_early["contact_count"] == 1

    # Advance 49 hours -> 2nd Contact allowed
    clock.advance_time(timedelta(hours=49))
    c2 = process_case(case_id=case_id)
    assert c2["contact_count"] == 2

    # Advance 49 hours -> 3rd Contact allowed
    clock.advance_time(timedelta(hours=49))
    c3 = process_case(case_id=case_id)
    assert c3["contact_count"] == 3

    # Advance 49 hours -> 4th Contact allowed
    clock.advance_time(timedelta(hours=49))
    c4 = process_case(case_id=case_id)
    assert c4["contact_count"] == 4
    # Upon reaching 4 contacts, case transitions to UNRECOVERED
    assert c4["state"] == CaseState.UNRECOVERED

    # Advance another 49 hours -> 5th Contact attempt must be rejected (cannot exceed 4 contacts)
    clock.advance_time(timedelta(hours=49))
    c5 = process_case(case_id=case_id)
    assert c5["contact_count"] == 4
    assert c5["state"] == CaseState.UNRECOVERED

    # Verify all contacts in contact_repo have >= 48 hours gap
    contacts = repositories.contact_repo.list_for_case(case_id)
    assert len(contacts) == 4
    for i in range(1, len(contacts)):
        t_prev = datetime.fromisoformat(contacts[i-1]["sent_at"])
        t_curr = datetime.fromisoformat(contacts[i]["sent_at"])
        diff_hours = (t_curr - t_prev).total_seconds() / 3600.0
        assert diff_hours >= 48.0, f"Contact gap was {diff_hours} hours (< 48h!)"


# ── Scenario 3: Already-Paid Customers Get Zero Contacts ──────────────────────

def test_scenario_already_paid_customers_get_zero_contacts():
    """
    Scenario 3: A customer who already paid (e.g. via bank transfer auto_match)
    is closed as PAID_ELSEWHERE immediately, receiving exactly ZERO contacts.
    """
    # Customer CUST-00112 is planted in bank_statement.csv
    case_id = "CASE-SCENARIO-ALREADY-PAID"
    cid = "CUST-00112"

    trigger = {
        "trigger_type": "overdue_invoice",
        "event_id": "EVT-PAID-001",
        "customer_id": cid,
        "amount_usd": 125.0,
        "currency": "USD",
        "due_at": "2025-01-10T12:00:00+00:00",
    }

    processed_case = process_case(case_id=case_id, trigger=trigger)

    # Must immediately close as PAID_ELSEWHERE
    assert processed_case["state"] == CaseState.PAID_ELSEWHERE

    # Must have received ZERO contacts!
    assert processed_case.get("contact_count", 0) == 0
    assert len(repositories.contact_repo.list_for_case(processed_case["id"])) == 0
    assert len(list_messages(processed_case["id"])) == 0

