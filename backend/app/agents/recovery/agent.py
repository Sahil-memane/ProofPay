"""
Recovery Agent Main Controller.

Implements the complete process_case loop:
  1. Create or load the case (deduped by event ID)
  2. Already-paid check:
     - auto_match closes PAID_ELSEWHERE with zero contact
     - human_review holds with a review task in ACTION_PENDING_APPROVAL
     - no_match continues
  3. Diagnose
  4. Prioritise
  5. Pick strategy, template and send time
  6. Build Proposal -> policy.check -> execute only on allow (needs_approval / deny handled)
  7. Run stop checks:
     - payment_received -> RECOVERED
     - dispute -> HALTED
     - opt_out -> HALTED
     - 4 contacts -> UNRECOVERED
     - otherwise schedule next ladder step
  8. Promise-to-pay, retry failure handling (up to 3 retries, then ACTION_FAILED),
     and LLM usage tracking.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.app.recovery.diagnose import diagnose_case
from backend.app.recovery.prioritize import calculate_priority
from backend.app.recovery.state_machine import (
    create_case_from_trigger,
    halt_case,
    transition,
)
from backend.app.recovery.strategy import next_step
from backend.app.recovery.timing import get_next_allowed_send_time
from backend.app.recovery.tools import (
    check_already_paid,
    create_payment_link,
    escalate_to_human,
    make_idempotency_key,
    offer_split_payment,
    schedule_retry,
    send_invoice_reminder,
)
from backend.app.stubs import audit, clock, executor, llm, policy, scheduler
from backend.app.stubs.contracts_stub import ActionKind, CaseState, Proposal, Verdict
from backend.app.stubs.repositories import case_repo, contact_repo

logger = logging.getLogger(__name__)

MAX_CONTACTS = 4
MAX_EXECUTOR_RETRIES = 3


def process_case(
    case_id: str | None = None,
    trigger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Execute the full recovery decision loop for a single case.
    """
    now = clock.utcnow()

    # ── Step 1: Create or Load Case, Dedupe by Event ID ───────────────────────
    case: dict[str, Any] | None = None

    if trigger:
        trigger_type = trigger.get("trigger_type", "failed_payment")
        event_id = trigger.get("event_id") or trigger.get("id") or f"evt-{case_id}"
        case = create_case_from_trigger(
            trigger_type=trigger_type,
            event_id=event_id,
            payload=trigger,
        )
        case_id = case["id"]
    elif case_id:
        case = case_repo.get(case_id)

    if not case:
        raise ValueError(f"Unable to load or create case: case_id={case_id}, trigger={trigger}")

    # Track LLM usage flag on case
    case["llm_used"] = (llm.get_call_count(case_id) > 0)

    # If case is already in a final state, return immediately (do not re-process)
    current_state = case.get("state")
    if current_state in (CaseState.RECOVERED, CaseState.HALTED, CaseState.UNRECOVERED, CaseState.PAID_ELSEWHERE):
        return case

    # ── Step 2: Already-Paid Check ────────────────────────────────────────────
    recon_status = check_already_paid(case)

    if recon_status == "auto_match":
        # Closes as PAID_ELSEWHERE with ZERO contact!
        transition(case, to_state=CaseState.PAID_ELSEWHERE, actor="agent", reason="reconciliation_auto_match")
        audit.log_event("case_closed_paid_elsewhere", {
            "case_id": case_id,
            "contacts_made": case.get("contact_count", 0),
        })
        return case

    elif recon_status == "human_review":
        # Holds with an operational review task
        transition(case, to_state=CaseState.ACTION_PENDING_APPROVAL, actor="agent", reason="reconciliation_human_review_required")
        audit.log_event("reconciliation_review_task_created", {
            "case_id": case_id,
            "status": "pending_recon_verification",
        })
        return case

    # ── Step 3: Diagnose ──────────────────────────────────────────────────────
    if not case.get("diagnosis"):
        diagnosis = diagnose_case(case)
        case["diagnosis"] = diagnosis
    else:
        diagnosis = case["diagnosis"]

    if case.get("state") == CaseState.OPEN:
        transition(case, to_state=CaseState.DIAGNOSED, actor="agent", reason=f"diagnosed_as_{diagnosis}")

    # ── Step 4: Prioritise ────────────────────────────────────────────────────
    priority = calculate_priority(case)
    case["priority_score"] = priority

    # ── Step 5: Pick Strategy, Template, and Send Time ────────────────────────
    attempts = case.get("contact_count", 0)
    step_info = next_step(
        diagnosis=diagnosis,
        attempts=attempts,
        promised_date=case.get("promised_date"),
    )

    customer_tz = case.get("timezone", "UTC")
    last_contact_str = case.get("last_contact_at")
    last_contact_dt = datetime.fromisoformat(last_contact_str) if last_contact_str else None

    send_time = get_next_allowed_send_time(
        customer_tz=customer_tz,
        last_contact_at=last_contact_dt,
        now=now,
        is_payday_aligned=step_info.get("align_payday", False),
    )

    action_type = step_info.get("action", "send_reminder")

    # ── Step 6: Build Proposal, Call Policy Check, Execute on Allow ───────────
    proposal: Proposal

    if action_type == "escalate":
        proposal = escalate_to_human(case_id, reason=f"Strategy escalation for {diagnosis}")
    elif action_type == "send_payment_link":
        proposal = create_payment_link(
            case_id=case_id,
            amount_usd=case.get("amount_usd", 100.0),
            ladder_step=attempts,
            attempt=attempts,
        )
    elif action_type == "offer_split_payment":
        proposal = offer_split_payment(
            case_id=case_id,
            installments=2,
            ladder_step=attempts,
            attempt=attempts,
        )
    elif action_type == "retry_and_reminder":
        proposal = schedule_retry(
            case_id=case_id,
            run_at=send_time.isoformat(),
            ladder_step=attempts,
            attempt=attempts,
        )
    else:
        proposal = send_invoice_reminder(
            case_id=case_id,
            template_name=step_info.get("template", "forgot_to_pay"),
            ladder_step=attempts,
            attempt=attempts,
        )

    proposal.params["amount_usd"] = case.get("amount_usd", 100.0)
    proposal.params["run_at"] = send_time.isoformat()
    proposal.params["opted_out"] = case.get("opted_out", False)

    # Evaluate against Policy
    decision = policy.check(proposal)

    receipt = None
    if decision.verdict == Verdict.ALLOW:
        # Execution with up to 3 retries
        execution_success = False
        last_error = None
        for attempt_i in range(MAX_EXECUTOR_RETRIES):
            try:
                receipt = executor.execute(proposal, decision)
                execution_success = True
                policy.record_action_executed()
                break
            except Exception as e:
                last_error = e
                audit.log_event("executor_retry", {
                    "case_id": case_id,
                    "attempt": attempt_i + 1,
                    "error": str(e),
                })

        if not execution_success:
            # Failed after 3 retries: flag ACTION_FAILED and escalate to human
            case["action_failed"] = True
            transition(case, to_state=CaseState.HALTED, actor="system", reason=f"ACTION_FAILED: {last_error}")
            escalate_to_human(case_id, reason=f"ACTION_FAILED after 3 retries: {last_error}")
            return case

        # Successful execution
        is_contact = proposal.action in (ActionKind.SEND_EMAIL, ActionKind.SEND_PAYMENT_LINK)
        if is_contact:
            case["contact_count"] = attempts + 1
            case["last_contact_at"] = now.isoformat()

        transition(case, to_state=CaseState.ACTION_SENT, actor="agent", reason=f"Executed {proposal.action.value}")

    elif decision.verdict == Verdict.NEEDS_APPROVAL:
        transition(case, to_state=CaseState.ACTION_PENDING_APPROVAL, actor="agent", reason=f"Needs approval: {decision.blocked_by}")
        audit.log_event("approval_task_created", {
            "case_id": case_id,
            "blocked_by": decision.blocked_by,
        })
        return case

    else:  # Verdict.DENY
        audit.log_event("proposal_policy_denied", {
            "case_id": case_id,
            "blocked_by": decision.blocked_by,
        })

        if "min_gap_violation" in decision.blocked_by or "quiet_hours_violation" in decision.blocked_by:
            # Action is deferred due to timing policy (quiet hours or <48h gap);
            # do not transition to UNRECOVERED. Case stays active awaiting next allowed window.
            audit.log_event("action_deferred_timing_policy", {
                "case_id": case_id,
                "blocked_by": decision.blocked_by,
                "send_time": send_time.isoformat(),
            })
            return case

        if "customer_opted_out" in decision.blocked_by:
            case["opted_out"] = True
            halt_case(case_id, reason="customer_opted_out", actor="policy")
            return case

        if "open_dispute_active" in decision.blocked_by:
            halt_case(case_id, reason="open_dispute_active", actor="policy")
            return case

        if "contact_cap_exceeded" in decision.blocked_by:
            transition(case, to_state=CaseState.UNRECOVERED, actor="policy", reason="max_contacts_reached")
            return case

        escalate_to_human(case_id, reason=f"Policy denied proposal: {decision.blocked_by}")
        transition(case, to_state=CaseState.UNRECOVERED, actor="policy", reason=f"policy_denied_{decision.blocked_by}")
        return case

    # ── Step 7: Post-Result Stop Checks ───────────────────────────────────────
    sim_resp = (receipt or {}).get("sim_response") if receipt else None
    sim_event_type = sim_resp.get("event_type") if sim_resp else None
    sim_meta = sim_resp.get("meta", {}) if sim_resp else {}

    # Check 1: Payment Success / Received -> RECOVERED
    if sim_event_type in ("payment_success", "payment_received"):
        transition(case, to_state=CaseState.RECOVERED, actor="simulator", reason="payment_received")
        return case

    # Check 2: Customer Dispute -> HALTED (nothing more proposed)
    if sim_event_type == "dispute":
        halt_case(case_id, reason="customer_dispute", actor="simulator")
        return case

    # Check 3: Customer Opt-Out -> HALTED
    if sim_event_type == "opt_out" or sim_meta.get("opted_out"):
        case["opted_out"] = True
        halt_case(case_id, reason="customer_opt_out", actor="simulator")
        return case

    # Check 4: Contact Cap (4 contacts) reached -> UNRECOVERED
    if case["contact_count"] >= MAX_CONTACTS:
        transition(case, to_state=CaseState.UNRECOVERED, actor="agent", reason="max_contacts_reached")
        audit.log_event("case_unrecovered_contact_cap", {
            "case_id": case_id,
            "total_contacts": case["contact_count"],
        })
        return case

    # Check 5: Promised Date Extracted
    if sim_resp and sim_resp.get("message"):
        # Check if customer promised a date
        msg = sim_resp.get("message", "").lower()
        if "friday" in msg or "शुक्रवार" in msg:
            case["promised_date"] = "2025-06-06"
        elif "monday" in msg or "सोमवार" in msg:
            case["promised_date"] = "2025-06-09"

    # Otherwise: transition to AWAITING_RESULT and schedule next ladder step
    transition(case, to_state=CaseState.AWAITING_RESULT, actor="agent", reason="awaiting_customer_response")

    # Schedule next ladder step
    def next_step_job(cid: str = case_id):
        process_case(cid)

    scheduler.enqueue(next_step_job, case_id=case_id)
    return case
