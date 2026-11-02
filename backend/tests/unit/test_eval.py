"""
Unit tests for the Evaluation Subsystem (Step 10).
"""
import pytest
from backend.app.eval.baseline import BaselineAgent
from backend.app.eval.metrics import AgentEvalMetrics, compare_agents, compute_agent_metrics
from backend.app.eval.report import generate_json_report, generate_markdown_report
from backend.app.eval.runner import run_evaluation


def test_baseline_agent_basic_run():
    agent = BaselineAgent(seed=42)
    case = {
        "id": "CASE-TEST-01",
        "customer_id": "CUST-0001",
        "amount_usd": 120.0,
        "profile": {"behaviour": "pays_after_one_reminder"},
    }
    result = agent.process_case(case)
    assert result["agent_type"] == "baseline"
    assert result["recovered"] is True
    assert result["amount_recovered"] == 120.0
    assert result["contact_count"] >= 1


def test_compute_metrics_and_wrongful_contacts():
    # Customer who already paid elsewhere receiving 2 contacts = 2 wrongful contacts!
    results = [
        {
            "case_id": "C-1",
            "customer_id": "CUST-PAID",
            "recovered": True,
            "state": "RECOVERED",
            "amount_usd": 100.0,
            "amount_recovered": 100.0,
            "contact_count": 2,
            "days_to_recover": 2.0,
            "llm_calls_used": 1,
        },
        {
            "case_id": "C-2",
            "customer_id": "CUST-REGULAR",
            "recovered": True,
            "state": "RECOVERED",
            "amount_usd": 200.0,
            "amount_recovered": 200.0,
            "contact_count": 1,
            "days_to_recover": 1.0,
            "llm_calls_used": 0,
        },
    ]
    true_profiles = {
        "CUST-PAID": {"behaviour": "already_paid_elsewhere"},
        "CUST-REGULAR": {"behaviour": "pays_after_one_reminder"},
    }
    m = compute_agent_metrics("Test Agent", results, true_profiles)
    assert m.total_cases == 2
    assert m.recovered_cases == 2
    assert m.recovery_rate == 1.0
    assert m.total_contacts == 3
    assert m.wrongful_contacts == 2  # The 2 contacts to CUST-PAID
    assert m.wrongful_contact_rate == round(2 / 3, 4)
    assert m.total_llm_calls == 1
    assert m.total_llm_cost_usd == 0.002
    assert m.net_dollars_recovered == round(300.0 - 0.002, 2)


def test_compare_agents_and_report_generation():
    m_base = AgentEvalMetrics(
        agent_name="Baseline",
        total_cases=10,
        recovered_cases=5,
        unrecovered_cases=5,
        halted_cases=0,
        recovery_rate=0.50,
        total_at_risk_usd=1000.0,
        gross_dollars_recovered=500.0,
        recovered_over_at_risk=0.50,
        total_contacts=20,
        contacts_per_recovery=4.0,
        wrongful_contact_count=5,
        wrongful_contact_rate=0.25,
        disputes_count=2,
        avg_days_to_recover=4.0,
        total_llm_calls=0,
        total_llm_cost_usd=0.0,
        net_dollars_recovered=500.0,
    )
    m_agent = AgentEvalMetrics(
        agent_name="Recovery Agent",
        total_cases=10,
        recovered_cases=8,
        unrecovered_cases=2,
        halted_cases=0,
        recovery_rate=0.80,
        total_at_risk_usd=1000.0,
        gross_dollars_recovered=800.0,
        recovered_over_at_risk=0.80,
        total_contacts=12,
        contacts_per_recovery=1.5,
        wrongful_contact_count=0,
        wrongful_contact_rate=0.0,
        disputes_count=0,
        avg_days_to_recover=2.0,
        total_llm_calls=5,
        total_llm_cost_usd=0.01,
        net_dollars_recovered=799.99,
    )
    comp = compare_agents(m_base, m_agent)
    assert comp["comparison"]["recovery_rate_lift_pct"] == 30.0
    assert comp["comparison"]["wrongful_contacts_avoided"] == 5

    md = generate_markdown_report(comp)
    assert "ProofPay Recovery Agent" in md
    assert "Scoreboard" in md
    assert "30.0%" in md

    json_str = generate_json_report(comp)
    assert '"recovery_rate_lift_pct": 30.0' in json_str


def test_eval_runner_with_small_batch():
    comp = run_evaluation(cases_limit=5, seed=42)
    assert "baseline" in comp
    assert "recovery_agent" in comp
    assert comp["recovery_agent"]["total_cases"] == 5
