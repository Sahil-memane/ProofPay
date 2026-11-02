"""
End-to-End Scenario Test Suite: test_ig3.py (Step 13).

Validates the full ProofPay Recovery pipeline:
  1. Zero contacts to any already-paid customer while baseline contacts them.
  2. A dispute injected mid-ladder halts the case with no further proposal.
  3. No case exceeds 4 contacts, and no two contacts are under 48 hours apart.
  4. The comparison scoreboard table is generated.
  5. The share of cases with no LLM call is reported.
"""
from datetime import timedelta
from pathlib import Path
import pytest

from backend.app.agents.recovery.agent import process_case
from backend.app.eval.report import generate_markdown_report
from backend.app.eval.runner import run_evaluation
from backend.app.simulator.profiles import CustomerProfile
from backend.app.stubs import audit, clock, policy, repositories
from backend.app.stubs.contracts_stub import CaseState

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def reset_runtime_state():
    """Reset shared singleton state between test runs."""
    clock.reset()
    policy.reset_daily_cap()
    repositories.case_repo.reset()
    repositories.contact_repo._store.clear()
    audit.clear()
    yield
    clock.reset()
    policy.reset_daily_cap()
    repositories.case_repo.reset()
    repositories.contact_repo._store.clear()
    audit.clear()


def test_ig3_all_seeded_cases_comparison_and_zero_wrongful_contacts():
    """
    Runs all 150+ seeded cases under both baseline and Recovery Agent:
      - Asserts zero contacts to any already-paid customer (agent).
      - Asserts baseline contacts multiple already-paid customers.
      - Asserts comparison table is generated.
      - Asserts share of cases with no LLM call is reported.
    """
    comp = run_evaluation(cases_limit=None, seed=42)

    base = comp["baseline"]
    agent = comp["recovery_agent"]

    # 1. Total cases verified (150 cases from datagen: 90 subscriptions + 60 invoices)
    assert base["total_cases"] >= 150
    assert agent["total_cases"] >= 150

    # 2. Zero contacts to already-paid customers by Recovery Agent
    assert agent["wrongful_contact_count"] == 0, (
        f"Recovery agent made {agent['wrongful_contact_count']} wrongful contacts!"
    )
    assert len(agent["wrongfully_contacted_customers"]) == 0

    # 3. Baseline contacts some already-paid customers
    assert base["wrongful_contact_count"] > 0, (
        "Baseline was expected to contact already-paid customers without reconciliation!"
    )

    # 4. Comparison table is generated
    md_table = generate_markdown_report(comp)
    assert "Scoreboard" in md_table
    assert "Naive Baseline" in md_table
    assert "ProofPay Recovery Agent" in md_table
    assert "Reconciliation Precision / Recall" in md_table

    # 5. Share of cases with no LLM call is reported
    assert "share_of_cases_with_no_llm_call" in agent
    assert agent["share_of_cases_with_no_llm_call"] >= 0.90  # >90% purely rule-based


def test_ig3_dispute_mid_ladder_halts_with_no_further_proposals():
    """A dispute injected mid-ladder halts the case with no further proposal."""
    case_id = "CASE-IG3-DISPUTE"
    repositories.case_repo._store[case_id] = {
        "id": case_id,
        "case_id": case_id,
        "customer_id": "CUST-DISPUTE-01",
        "amount_usd": 120.0,
        "state": CaseState.OPEN,
        "contact_count": 0,
        "last_contact_at": None,
        "history": [],
        "profile": CustomerProfile(
            customer_id="CUST-DISPUTE-01",
            email="dispute@example.com",
            timezone="UTC",
            behaviour="disputes_if_chased_early",
        ),
    }

    # Step 0: Initial contact
    c1 = process_case(case_id=case_id)
    # The simulator for disputes_if_chased_early disputes immediately when contacted early
    assert c1["state"] == CaseState.HALTED
    assert c1.get("has_open_dispute") is True or c1.get("state") == CaseState.HALTED

    contact_count_at_halt = c1["contact_count"]

    # Subsequent process attempts: must NEVER propose or send anything further!
    clock.advance_time(timedelta(days=5))
    c_after = process_case(case_id=case_id)
    assert c_after["state"] == CaseState.HALTED
    assert c_after["contact_count"] == contact_count_at_halt


def test_ig3_no_case_exceeds_4_contacts_and_all_gaps_ge_48h():
    """No case exceeds 4 contacts and none has two contacts under 48 hours apart."""
    case_id = "CASE-IG3-CAP"
    repositories.case_repo._store[case_id] = {
        "id": case_id,
        "case_id": case_id,
        "customer_id": "CUST-CAP-01",
        "amount_usd": 85.0,
        "currency": "USD",
        "state": CaseState.OPEN,
        "contact_count": 0,
        "last_contact_at": None,
        "history": [],
        "profile": CustomerProfile(
            customer_id="CUST-CAP-01",
            email="cap@example.com",
            timezone="UTC",
            behaviour="ignores_everything",
        ),
    }

    # Contact 1
    c1 = process_case(case_id=case_id)
    assert c1["contact_count"] == 1

    # Contact 2 (after 49 hours)
    clock.advance_time(timedelta(hours=49))
    c2 = process_case(case_id=case_id)
    assert c2["contact_count"] == 2

    # Contact 3 (after 49 hours)
    clock.advance_time(timedelta(hours=49))
    c3 = process_case(case_id=case_id)
    assert c3["contact_count"] == 3

    # Contact 4 (after 49 hours) -> transitions to UNRECOVERED
    clock.advance_time(timedelta(hours=49))
    c4 = process_case(case_id=case_id)
    assert c4["contact_count"] == 4
    assert c4["state"] == CaseState.UNRECOVERED

    # Contact 5 attempt (after 49 hours) -> strictly blocked!
    clock.advance_time(timedelta(hours=49))
    c5 = process_case(case_id=case_id)
    assert c5["contact_count"] == 4
    assert c5["state"] == CaseState.UNRECOVERED

    # Verify all contacts have >= 48 hours gap
    contacts = repositories.contact_repo.list_for_case(case_id)
    assert len(contacts) == 4
    from datetime import datetime
    for i in range(1, len(contacts)):
        t_prev = datetime.fromisoformat(contacts[i-1]["sent_at"])
        t_curr = datetime.fromisoformat(contacts[i]["sent_at"])
        gap_h = (t_curr - t_prev).total_seconds() / 3600.0
        assert gap_h >= 48.0, f"Contact gap was {gap_h} hours (< 48h)"
