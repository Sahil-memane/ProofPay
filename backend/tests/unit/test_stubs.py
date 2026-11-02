"""Unit tests for stub modules."""
import pytest
from backend.app.stubs.contracts_stub import (
    Proposal, PolicyDecision, Verdict, CaseState, ActionKind, FINAL_STATES,
)
from backend.app.stubs import policy as policy_stub
from backend.app.stubs import executor as executor_stub
from backend.app.stubs import llm as llm_stub
from backend.app.stubs import repositories as repo_stub


def make_proposal(**overrides):
    defaults = dict(
        agent="test",
        subject="case-1",
        action=ActionKind.SEND_EMAIL,
        reason="test reason",
        params={"amount_usd": 50.0},
    )
    defaults.update(overrides)
    return Proposal(**defaults)


# ── contracts ─────────────────────────────────────────────────────────────────

def test_proposal_defaults():
    p = make_proposal()
    assert p.llm_used is False
    assert p.confidence == 1.0
    assert p.inputs_used == []


def test_proposal_confidence_bounds():
    with pytest.raises(Exception):
        make_proposal(confidence=1.5)
    with pytest.raises(Exception):
        make_proposal(confidence=-0.1)


def test_final_states():
    assert CaseState.RECOVERED in FINAL_STATES
    assert CaseState.OPEN not in FINAL_STATES


# ── policy stub ───────────────────────────────────────────────────────────────

def test_policy_allows_under_limit():
    policy_stub.reset_daily_cap()
    p = make_proposal(params={"amount_usd": 100.0})
    d = policy_stub.evaluate(p)
    assert d.verdict == Verdict.ALLOW


def test_policy_denies_over_limit():
    policy_stub.reset_daily_cap()
    p = make_proposal(params={"amount_usd": 300.0})
    d = policy_stub.evaluate(p)
    assert d.verdict in (Verdict.DENY, Verdict.NEEDS_APPROVAL)
    assert "over_auto_limit" in d.blocked_by


def test_policy_daily_cap():
    policy_stub.set_daily_cap_reached()
    p = make_proposal(params={"amount_usd": 50.0})
    d = policy_stub.evaluate(p)
    assert "daily_cap_reached" in d.blocked_by
    policy_stub.reset_daily_cap()


# ── executor stub ─────────────────────────────────────────────────────────────

def test_executor_records_receipt():
    executor_stub.reset()
    p = make_proposal()
    d = PolicyDecision(verdict=Verdict.ALLOW, checks={})
    receipt = executor_stub.execute(p, d)
    assert receipt["status"] == "sent"
    assert len(executor_stub.get_executed()) == 1


def test_executor_rejects_non_allow():
    executor_stub.reset()
    p = make_proposal()
    d = PolicyDecision(verdict=Verdict.DENY, checks={})
    with pytest.raises(ValueError):
        executor_stub.execute(p, d)


# ── llm stub ──────────────────────────────────────────────────────────────────

def test_llm_call_limit():
    llm_stub.reset()
    llm_stub.complete("c1", "prompt")
    llm_stub.complete("c1", "prompt")
    with pytest.raises(RuntimeError):
        llm_stub.complete("c1", "prompt")


def test_llm_separate_cases_independent():
    llm_stub.reset()
    llm_stub.complete("cA", "p")
    llm_stub.complete("cB", "p")
    assert llm_stub.get_call_count("cA") == 1
    assert llm_stub.get_call_count("cB") == 1


# ── repositories ─────────────────────────────────────────────────────────────

def test_case_repo_create_get():
    repo = repo_stub.CaseRepo()
    case = repo.create("cust-1", 150.0)
    assert repo.get(case["id"]) is not None
    assert case["state"] == CaseState.OPEN


def test_case_repo_update():
    repo = repo_stub.CaseRepo()
    case = repo.create("cust-2", 75.0)
    updated = repo.update(case["id"], state=CaseState.RECONCILING)
    assert updated["state"] == CaseState.RECONCILING


def test_contact_repo():
    repo = repo_stub.ContactRepo()
    repo.add("case-x", "email")
    repo.add("case-x", "payment_link")
    contacts = repo.list_for_case("case-x")
    assert len(contacts) == 2
