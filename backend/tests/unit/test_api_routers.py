"""
Unit tests for FastAPI API Routers for Dev 4 (Step 11).

Tests all endpoints:
  - api/cases.py:
      GET /cases?sort=priority
      GET /cases?status=HALTED,UNRECOVERED (reason on every row)
      GET /cases/{case_id} (attempt timeline + policy checks)
      GET /outbox
      GET /reconciliation/summary (matched, review, exception)
      GET /approvals and POST /approvals/{id}/decide
      POST /cases/{id}/reopen (audited)
  - api/dashboard.py:
      GET /dashboard/headline (recovered, at-risk, count, recovered count)
      GET /eval/latest
  - api/sim.py:
      POST /demo/inject-failure
      POST /demo/run-simulator
      POST /demo/advance-clock
      POST /demo/reset
      (Verifies 404 on all demo endpoints when DEMO_MODE is off)
"""
import pytest
from fastapi import HTTPException

from backend.app.api.cases import (
    ApprovalDecisionRequest,
    ReopenRequest,
    decide_approval,
    get_case_detail,
    get_outbox,
    get_reconciliation_summary,
    list_cases,
    list_pending_approvals,
    reopen_case_endpoint,
)
from backend.app.api.dashboard import get_dashboard_headline, get_latest_eval
from backend.app.api.sim import (
    AdvanceClockRequest,
    InjectFailureRequest,
    RunSimulatorRequest,
    demo_advance_clock,
    demo_inject_failure,
    demo_reset_endpoint,
    demo_run_simulator,
    set_demo_mode,
)
from backend.app.channels.outbox import record_message
from backend.app.simulator.profiles import CustomerProfile
from backend.app.stubs import audit, clock, repositories
from backend.app.stubs.contracts_stub import CaseState


@pytest.fixture(autouse=True)
def reset_test_state():
    repositories.case_repo.reset()
    repositories.contact_repo._store.clear()
    audit.clear()
    set_demo_mode(False)
    yield
    set_demo_mode(False)


# ── Cases Router Tests ────────────────────────────────────────────────────────

def test_cases_list_priority_sort_and_status_filter_with_reason():
    # Setup test cases
    c1 = {
        "id": "CASE-01",
        "case_id": "CASE-01",
        "customer_id": "CUST-01",
        "amount_usd": 150.0,
        "priority_score": 150.0,
        "state": CaseState.OPEN,
        "history": [{"from_state": None, "to_state": "OPEN", "reason": "created"}],
    }
    c2 = {
        "id": "CASE-02",
        "case_id": "CASE-02",
        "customer_id": "CUST-02",
        "amount_usd": 500.0,
        "priority_score": 500.0,
        "state": CaseState.HALTED,
        "history": [{"from_state": "OPEN", "to_state": "HALTED", "reason": "customer_dispute"}],
    }
    c3 = {
        "id": "CASE-03",
        "case_id": "CASE-03",
        "customer_id": "CUST-03",
        "amount_usd": 75.0,
        "priority_score": 75.0,
        "state": CaseState.UNRECOVERED,
        "history": [{"from_state": "OPEN", "to_state": "UNRECOVERED", "reason": "max_contacts_reached"}],
    }

    repositories.case_repo._store["CASE-01"] = c1
    repositories.case_repo._store["CASE-02"] = c2
    repositories.case_repo._store["CASE-03"] = c3

    # 1. Sort by priority
    sorted_cases = list_cases(sort="priority")
    assert [c["id"] for c in sorted_cases] == ["CASE-02", "CASE-01", "CASE-03"]

    # 2. Filter by status=HALTED,UNRECOVERED with reason on EVERY row
    filtered = list_cases(status="HALTED,UNRECOVERED")
    assert len(filtered) == 2
    for row in filtered:
        assert row["state"] in (CaseState.HALTED, CaseState.UNRECOVERED)
        assert "reason" in row
        assert len(row["reason"]) > 0

    c2_row = next(r for r in filtered if r["id"] == "CASE-02")
    assert c2_row["reason"] == "customer_dispute"


def test_case_detail_attempt_timeline_and_policy_checks():
    case_id = "CASE-DETAIL-01"
    repositories.case_repo._store[case_id] = {
        "id": case_id,
        "case_id": case_id,
        "customer_id": "CUST-01",
        "amount_usd": 120.0,
        "state": CaseState.ACTION_SENT,
        "history": [
            {"from_state": None, "to_state": "OPEN", "reason": "trigger", "actor": "system", "timestamp": "2025-06-01"},
            {"from_state": "OPEN", "to_state": "ACTION_SENT", "reason": "sent_email", "actor": "agent", "timestamp": "2025-06-01"},
        ],
    }
    repositories.contact_repo.add(case_id, channel="email", sent_at=clock.utcnow())
    audit.log_event("proposal_policy_evaluated", {"case_id": case_id, "checks": ["gap_48h_ok"]})

    detail = get_case_detail(case_id)
    assert detail["case"]["id"] == case_id
    assert len(detail["attempt_timeline"]) == 2
    assert len(detail["contacts"]) == 1
    assert len(detail["policy_checks"]) >= 1


def test_outbox_endpoint():
    record_message(
        case_id="CASE-OUT-01",
        channel="email",
        recipient="user@example.com",
        subject="Notice",
        body="Payment reminder",
    )
    messages = get_outbox()
    assert any(m["case_id"] == "CASE-OUT-01" for m in messages)


def test_reconciliation_summary_endpoint():
    summary = get_reconciliation_summary()
    assert "matched" in summary
    assert "review" in summary
    assert "exception" in summary
    assert isinstance(summary["total_matched"], int)


def test_approvals_list_and_decide():
    case_id = "CASE-APP-01"
    repositories.case_repo._store[case_id] = {
        "id": case_id,
        "case_id": case_id,
        "customer_id": "CUST-APP",
        "amount_usd": 350.0,
        "state": CaseState.ACTION_PENDING_APPROVAL,
        "history": [{"from_state": "DIAGNOSED", "to_state": "ACTION_PENDING_APPROVAL", "reason": "over_auto_limit"}],
    }

    # List pending approvals
    pending = list_pending_approvals()
    assert any(c["id"] == case_id for c in pending)

    # Approve decision
    res = decide_approval(case_id, ApprovalDecisionRequest(decision="approve", actor="ops_lead", notes="Verified customer history"))
    assert res["status"] == "approved"
    assert res["state"] == CaseState.ACTION_SENT.value

    # Reject decision on another case
    case_id_2 = "CASE-APP-02"
    repositories.case_repo._store[case_id_2] = {
        "id": case_id_2,
        "case_id": case_id_2,
        "state": CaseState.ACTION_PENDING_APPROVAL,
        "history": [],
    }
    res_rej = decide_approval(case_id_2, ApprovalDecisionRequest(decision="reject", actor="ops_lead", notes="Suspicious activity"))
    assert res_rej["status"] == "rejected"
    assert res_rej["state"] == CaseState.HALTED.value


def test_audited_reopen_endpoint():
    case_id = "CASE-REOPEN-01"
    repositories.case_repo._store[case_id] = {
        "id": case_id,
        "case_id": case_id,
        "state": CaseState.HALTED,
        "history": [],
    }
    updated = reopen_case_endpoint(case_id, ReopenRequest(actor="human_supervisor", reason="customer_called_to_pay"))
    assert updated["state"] == CaseState.OPEN.value


# ── Dashboard Router Tests ────────────────────────────────────────────────────

def test_dashboard_headline():
    repositories.case_repo._store["C1"] = {"id": "C1", "amount_usd": 100.0, "state": CaseState.RECOVERED}
    repositories.case_repo._store["C2"] = {"id": "C2", "amount_usd": 200.0, "state": CaseState.PAID_ELSEWHERE}
    repositories.case_repo._store["C3"] = {"id": "C3", "amount_usd": 150.0, "state": CaseState.UNRECOVERED}

    headline = get_dashboard_headline()
    assert headline["case_count"] == 3
    assert headline["recovered_count"] == 2
    assert headline["recovered_amount"] == 300.0
    assert headline["at_risk_amount"] == 450.0


def test_dashboard_eval_latest():
    eval_summary = get_latest_eval()
    assert "baseline" in eval_summary
    assert "recovery_agent" in eval_summary
    assert "comparison" in eval_summary


# ── Sim & Demo Router Tests (404 when DEMO_MODE is off) ───────────────────────

def test_demo_endpoints_return_404_when_demo_mode_is_off():
    set_demo_mode(False)

    with pytest.raises(HTTPException) as exc_info:
        demo_inject_failure(InjectFailureRequest(customer_id="CUST-01"))
    assert exc_info.value.status_code == 404

    with pytest.raises(HTTPException) as exc_info:
        demo_run_simulator(RunSimulatorRequest(case_id="C-01"))
    assert exc_info.value.status_code == 404

    with pytest.raises(HTTPException) as exc_info:
        demo_advance_clock(AdvanceClockRequest(days=1))
    assert exc_info.value.status_code == 404

    with pytest.raises(HTTPException) as exc_info:
        demo_reset_endpoint()
    assert exc_info.value.status_code == 404


def test_demo_endpoints_work_when_demo_mode_is_on():
    set_demo_mode(True)

    # 1. Inject failure
    inj = demo_inject_failure(InjectFailureRequest(
        customer_id="CUST-DEMO-TEST",
        failure_code="insufficient_funds",
        amount_usd=95.0,
    ))
    assert inj["status"] == "failure_injected"
    cid = inj["case_id"]

    # Attach profile for simulator test
    repositories.case_repo._store[cid]["profile"] = CustomerProfile(
        customer_id="CUST-DEMO-TEST",
        email="demo@example.com",
        timezone="UTC",
        behaviour="pays_after_one_reminder",
    )

    # 2. Run simulator
    sim_res = demo_run_simulator(RunSimulatorRequest(
        case_id=cid,
        action="send_reminder",
        seed=42,
    ))
    assert sim_res["event_type"] in ("payment_success", "free_text_reply")

    # 3. Advance clock
    adv = demo_advance_clock(AdvanceClockRequest(days=2.5, hours=3.0))
    assert "current_time" in adv
    assert adv["advanced_by"]["days"] == 2.5

    # 4. Reset
    reset_res = demo_reset_endpoint()
    assert reset_res["status"] == "demo_environment_reset_complete"
