"""
Evaluation Runner for ProofPay.

Executes both the Naive Baseline Agent and the ProofPay Recovery Agent
across the synthetic dataset, verifying results against the hidden answer key.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.eval.baseline import BaselineAgent
from backend.app.eval.metrics import AgentEvalMetrics, compare_agents, compute_agent_metrics
from backend.app.stubs import clock, llm, policy, repositories
from backend.app.stubs.contracts_stub import CaseState

ROOT = Path(__file__).resolve().parents[3]
DATA_GEN = ROOT / "data" / "generated"
DATA_KEY = ROOT / "data" / "answer_key"


def load_evaluation_data() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Load generated cases and secret true customer profiles."""
    cases: list[dict[str, Any]] = []

    # Invoices
    inv_file = DATA_GEN / "invoices.json"
    if inv_file.exists():
        with open(inv_file, "r", encoding="utf-8") as f:
            cases.extend(json.load(f))

    # Failed Subscriptions
    sub_file = DATA_GEN / "subscriptions.json"
    if sub_file.exists():
        with open(sub_file, "r", encoding="utf-8") as f:
            cases.extend(json.load(f))

    # Secret profiles from answer key
    profiles: dict[str, dict[str, Any]] = {}
    prof_yaml = DATA_KEY / "customers.yaml"
    prof_json = DATA_KEY / "true_profiles.json"
    if prof_yaml.exists():
        import yaml
        with open(prof_yaml, "r", encoding="utf-8") as f:
            profiles = yaml.safe_load(f) or {}
    elif prof_json.exists():
        with open(prof_json, "r", encoding="utf-8") as f:
            raw_profiles = json.load(f)
            if isinstance(raw_profiles, list):
                profiles = {p["customer_id"]: p for p in raw_profiles}
            elif isinstance(raw_profiles, dict):
                profiles = raw_profiles

    return cases, profiles


def run_evaluation(
    cases_limit: int | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    """
    Run the end-to-end evaluation harness:
    1. Runs the Baseline Agent across all cases.
    2. Runs the ProofPay Recovery Agent across all cases.
    3. Evaluates both against the hidden answer key.
    4. Produces comparative summary statistics.
    """
    cases, true_profiles = load_evaluation_data()
    if cases_limit is not None:
        cases = cases[:cases_limit]

    # ── 1. Run Baseline Agent ─────────────────────────────────────────────────
    baseline_agent = BaselineAgent(seed=seed)
    baseline_results: list[dict[str, Any]] = []

    for c in cases:
        cid = str(c.get("customer_id") or c.get("id", ""))
        case_copy = dict(c)
        case_copy["profile"] = true_profiles.get(cid)
        res = baseline_agent.process_case(case_copy)
        res["customer_id"] = cid
        baseline_results.append(res)

    baseline_metrics = compute_agent_metrics("Naive Baseline", baseline_results, true_profiles)

    # ── 2. Run ProofPay Recovery Agent ────────────────────────────────────────
    from backend.app.agents.recovery.agent import process_case
    from backend.app.channels.outbox import clear_outbox
    from backend.app.recovery.state_machine import clear_trigger_dedup_cache
    from backend.app.simulator.profiles import CustomerProfile

    # Reset platform state for evaluation run
    repositories.case_repo.reset()
    repositories.contact_repo._store.clear()
    clear_outbox()
    clear_trigger_dedup_cache()
    policy.reset_daily_cap()
    llm.reset()
    clock.reset()

    recovery_results: list[dict[str, Any]] = []

    for c in cases:
        cid = str(c.get("customer_id") or c.get("id", ""))
        p_info = true_profiles.get(cid, {})
        prof = CustomerProfile(
            customer_id=cid,
            email=p_info.get("email", f"{cid}@example.com"),
            timezone=p_info.get("timezone", "UTC"),
            language=p_info.get("language", "en"),
            behaviour=p_info.get("behaviour", "pays_after_one_reminder"),
            opted_out=p_info.get("opted_out", False),
        )

        amount = float(c.get("amount_usd") or c.get("amount", 100.0))
        currency = str(c.get("currency", "USD"))
        case_id = str(c.get("id") or c.get("invoice_id") or c.get("case_id", f"EVAL-{cid}"))

        # Pre-seed case into repo with attached profile for the simulator
        repositories.case_repo._store[case_id] = {
            "id": case_id,
            "case_id": case_id,
            "customer_id": cid,
            "amount_usd": amount,
            "currency": currency,
            "state": CaseState.OPEN,
            "contact_count": 0,
            "last_contact_at": None,
            "due_at": c.get("due_at") or c.get("failed_at") or c.get("created_at"),
            "date": c.get("date") or c.get("due_at") or c.get("failed_at") or c.get("created_at"),
            "failed_at": c.get("failed_at"),
            "payload": dict(c),
            "history": [],
            "profile": prof,
        }

        # Process case through Recovery Agent
        processed = process_case(case_id=case_id)
        llm_calls = llm.get_call_count(case_id)

        # Extract intervention type and unrecovered reason from history
        history = processed.get("history", [])
        last_reason = history[-1].get("reason", "") if history else ""
        
        intervention = "reconciliation_auto_match" if processed.get("state") == CaseState.PAID_ELSEWHERE else None
        if not intervention and history:
            for h in reversed(history):
                r_text = h.get("reason", "")
                if "Executed" in r_text:
                    intervention = r_text.replace("Executed ", "")
                    break

        recovery_results.append({
            "case_id": case_id,
            "customer_id": cid,
            "state": processed.get("state").value if hasattr(processed.get("state"), "value") else str(processed.get("state")),
            "recovered": processed.get("state") in (CaseState.RECOVERED, CaseState.PAID_ELSEWHERE),
            "halted": processed.get("state") == CaseState.HALTED,
            "contact_count": processed.get("contact_count", 0),
            "amount_usd": amount,
            "amount_recovered": amount if processed.get("state") in (CaseState.RECOVERED, CaseState.PAID_ELSEWHERE) else 0.0,
            "days_to_recover": 0.0 if processed.get("state") == CaseState.PAID_ELSEWHERE else 1.0,
            "intervention_type": intervention,
            "dispute_occurred": "dispute" in last_reason,
            "unrecovered_reason": last_reason if processed.get("state") not in (CaseState.RECOVERED, CaseState.PAID_ELSEWHERE) else None,
            "llm_calls_used": llm_calls,
            "agent_type": "proofpay_recovery",
        })

    # Count unsafe actions blocked by policy from audit log
    from backend.app.stubs import audit
    blocked_count = sum(
        1 for e in audit.get_events()
        if e.get("event") in ("proposal_policy_denied", "approval_task_created")
    )

    recovery_metrics = compute_agent_metrics(
        "ProofPay Recovery Agent",
        recovery_results,
        true_profiles,
        unsafe_actions_blocked=blocked_count,
    )

    return compare_agents(baseline_metrics, recovery_metrics)

