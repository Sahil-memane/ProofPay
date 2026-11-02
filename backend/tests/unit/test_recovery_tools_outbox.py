"""
Unit tests for Step 7: Recovery Tools, Channels Outbox, and Stub Executor.
Verifies:
  1. An allowed proposal runs once
  2. The same key twice does nothing (idempotency)
  3. A denied decision never executes
"""
from __future__ import annotations

import pytest

from backend.app.channels.outbox import clear_outbox, list_messages
from backend.app.recovery.tools import (
    create_payment_link,
    escalate_to_human,
    get_case,
    get_customer_history,
    log_promise_to_pay,
    make_idempotency_key,
    offer_split_payment,
    schedule_retry,
    send_invoice_reminder,
)
from backend.app.stubs import executor, repositories
from backend.app.stubs.contracts_stub import (
    ActionKind,
    PolicyDecision,
    Proposal,
    Verdict,
)


@pytest.fixture(autouse=True)
def clean_fixtures():
    clear_outbox()
    executor.reset()
    repositories.case_repo.reset()
    repositories.contact_repo.reset()
    yield


# ── The Three Required Step 7 Tests ───────────────────────────────────────────

def test_allowed_proposal_runs_once():
    """Test 1: An allowed proposal runs once, writes to outbox, and returns a valid receipt."""
    case_id = "CASE-EXEC-001"
    repositories.case_repo.create("CUST-100", 120.0)
    repositories.case_repo._store[case_id] = {
        "id": case_id,
        "customer_id": "CUST-100",
        "amount_usd": 120.0,
        "email": "cust100@example.com",
    }

    proposal = send_invoice_reminder(case_id, template_name="forgot_to_pay")
    decision = PolicyDecision(verdict=Verdict.ALLOW, checks={"under_auto_limit": True})

    receipt = executor.execute(proposal, decision)

    assert receipt["status"] == "sent"
    assert len(executor.get_executed()) == 1

    # Verify message was written to the outbox
    messages = list_messages(case_id)
    assert len(messages) == 1
    assert messages[0]["recipient"] == "cust100@example.com"
    assert "forgot_to_pay" in messages[0]["metadata"].get("template", "")


def test_same_key_twice_does_nothing():
    """Test 2: Executing a proposal with the same idempotency key twice does nothing."""
    case_id = "CASE-IDEMP-001"
    key = make_idempotency_key(case_id, ladder_step=0, attempt=0)

    proposal = create_payment_link(case_id, amount_usd=50.0)
    # Ensure idempotency key is set
    proposal.params["idempotency_key"] = key
    decision = PolicyDecision(verdict=Verdict.ALLOW, checks={"under_auto_limit": True})

    # Execution 1
    receipt1 = executor.execute(proposal, decision)
    assert len(executor.get_executed()) == 1
    assert len(list_messages(case_id)) == 1

    # Execution 2 with the identical proposal and key
    receipt2 = executor.execute(proposal, decision)

    # Must do nothing new (returns existing receipt, does not append to executed or outbox)
    assert receipt2["receipt_id"] == receipt1["receipt_id"]
    assert len(executor.get_executed()) == 1
    assert len(list_messages(case_id)) == 1


def test_denied_decision_never_executes():
    """Test 3: A denied decision must never execute, raising ValueError."""
    case_id = "CASE-DENIED-001"
    proposal = create_payment_link(case_id, amount_usd=500.0)
    decision = PolicyDecision(
        verdict=Verdict.DENY,
        checks={"under_auto_limit": False},
        blocked_by=["over_auto_limit"],
    )

    with pytest.raises(ValueError) as excinfo:
        executor.execute(proposal, decision)

    assert "deny" in str(excinfo.value).lower()
    # Nothing was executed or written to outbox
    assert len(executor.get_executed()) == 0
    assert len(list_messages(case_id)) == 0


# ── Additional Tools Verification ─────────────────────────────────────────────

def test_tool_proposals_never_execute_directly():
    """Write tools must return Proposal objects only without executing."""
    p_retry = schedule_retry("C1", run_at="2025-06-05T10:00:00Z")
    assert isinstance(p_retry, Proposal)
    assert p_retry.action in (ActionKind.SEND_EMAIL, ActionKind.SEND_PAYMENT_LINK)

    p_split = offer_split_payment("C1", installments=3)
    assert isinstance(p_split, Proposal)
    assert p_split.params["installments"] == 3

    p_promise = log_promise_to_pay("C1", promised_date="2025-06-15")
    assert isinstance(p_promise, Proposal)
    assert p_promise.action == ActionKind.NO_OP

    p_esc = escalate_to_human("C1", reason="Unresponsive debtor")
    assert isinstance(p_esc, Proposal)
    assert p_esc.action == ActionKind.ESCALATE
    # Confirms nothing was added to executor or outbox
    assert len(executor.get_executed()) == 0
    assert len(list_messages()) == 0

