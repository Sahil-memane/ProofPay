"""
Recovery Agent Tools.

Follows the fundamental architecture:
  - The Agent proposes (via Proposal objects)
  - The Policy decides
  - The Code executes

Recovery code NEVER imports PayPal or email code; it only builds Proposal objects.
"""
from __future__ import annotations

from typing import Any

from backend.app.reconciliation.matcher import check_already_paid as _check_already_paid
from backend.app.stubs import audit
from backend.app.stubs.contracts_stub import ActionKind, Proposal
from backend.app.stubs.repositories import case_repo, contact_repo


def make_idempotency_key(case_id: str, ladder_step: str | int = 0, attempt: int = 0) -> str:
    """Generate canonical idempotency key: case_id:ladder_step:attempt."""
    return f"{case_id}:{ladder_step}:{attempt}"


# ── Read Tools ────────────────────────────────────────────────────────────────

def get_case(case_id: str) -> dict[str, Any] | None:
    """Read tool: fetch case record by ID."""
    return case_repo.get(case_id)


def get_customer_history(customer_id: str) -> list[dict[str, Any]]:
    """Read tool: list past contacts and records for a customer."""
    history = []
    for case in case_repo.list_all():
        if case.get("customer_id") == customer_id:
            contacts = contact_repo.list_for_case(case.get("id", ""))
            history.extend(contacts)
    return history


def check_already_paid(case: dict[str, Any]) -> str:
    """Read tool: consult reconciliation engine to see if already paid."""
    return _check_already_paid(case)


# ── Write Tools (Return Proposal objects only, never execute) ─────────────────

def schedule_retry(
    case_id: str,
    run_at: str,
    ladder_step: str | int = 0,
    attempt: int = 0,
    params: dict[str, Any] | None = None,
    reason: str = "Schedule automatic payment retry",
) -> Proposal:
    """Write tool: propose scheduling a payment retry."""
    idempotency_key = make_idempotency_key(case_id, ladder_step, attempt)
    p_params = dict(params or {})
    p_params.update({"run_at": run_at, "idempotency_key": idempotency_key})

    return Proposal(
        agent="recovery_agent",
        subject=case_id,
        action=ActionKind.SEND_EMAIL,  # Standard channel action for scheduled retry outreach
        params=p_params,
        reason=reason,
        inputs_used=["case_id", "run_at"],
        llm_used=False,
        confidence=1.0,
    )


def send_invoice_reminder(
    case_id: str,
    template_name: str = "forgot_to_pay",
    channel: str = "email",
    ladder_step: str | int = 0,
    attempt: int = 0,
    params: dict[str, Any] | None = None,
    reason: str = "Send invoice reminder notice",
) -> Proposal:
    """Write tool: propose sending an email reminder."""
    idempotency_key = make_idempotency_key(case_id, ladder_step, attempt)
    p_params = dict(params or {})
    p_params.update({
        "template": template_name,
        "channel": channel,
        "idempotency_key": idempotency_key,
    })

    return Proposal(
        agent="recovery_agent",
        subject=case_id,
        action=ActionKind.SEND_EMAIL,
        params=p_params,
        reason=reason,
        inputs_used=["case_id", "template"],
        llm_used=False,
        confidence=1.0,
    )


def create_payment_link(
    case_id: str,
    amount_usd: float,
    ladder_step: str | int = 1,
    attempt: int = 0,
    params: dict[str, Any] | None = None,
    reason: str = "Generate direct payment link",
) -> Proposal:
    """Write tool: propose generating and dispatching a payment link."""
    idempotency_key = make_idempotency_key(case_id, ladder_step, attempt)
    p_params = dict(params or {})
    p_params.update({
        "amount_usd": amount_usd,
        "channel": "payment_link",
        "idempotency_key": idempotency_key,
    })

    return Proposal(
        agent="recovery_agent",
        subject=case_id,
        action=ActionKind.SEND_PAYMENT_LINK,
        params=p_params,
        reason=reason,
        inputs_used=["case_id", "amount_usd"],
        llm_used=False,
        confidence=1.0,
    )


def offer_split_payment(
    case_id: str,
    installments: int = 2,
    ladder_step: str | int = 2,
    attempt: int = 0,
    params: dict[str, Any] | None = None,
    reason: str = "Offer split payment plan",
) -> Proposal:
    """Write tool: propose offering an installment / split payment arrangement."""
    idempotency_key = make_idempotency_key(case_id, ladder_step, attempt)
    p_params = dict(params or {})
    p_params.update({
        "installments": installments,
        "template": "split_offer",
        "channel": "email",
        "idempotency_key": idempotency_key,
    })

    return Proposal(
        agent="recovery_agent",
        subject=case_id,
        action=ActionKind.SEND_EMAIL,
        params=p_params,
        reason=reason,
        inputs_used=["case_id", "installments"],
        llm_used=False,
        confidence=1.0,
    )


def log_promise_to_pay(
    case_id: str,
    promised_date: str,
    ladder_step: str | int = 0,
    attempt: int = 0,
    params: dict[str, Any] | None = None,
    reason: str = "Log customer promise to pay",
) -> Proposal:
    """Write tool: propose recording customer promise to pay and pausing ladder."""
    idempotency_key = make_idempotency_key(case_id, ladder_step, attempt)
    p_params = dict(params or {})
    p_params.update({
        "promised_date": promised_date,
        "idempotency_key": idempotency_key,
    })

    return Proposal(
        agent="recovery_agent",
        subject=case_id,
        action=ActionKind.NO_OP,
        params=p_params,
        reason=reason,
        inputs_used=["case_id", "promised_date"],
        llm_used=False,
        confidence=1.0,
    )


def escalate_to_human(
    case_id: str,
    reason: str = "Manual review required",
) -> Proposal:
    """
    Write tool: propose escalating case to human.
    Creates a review task and an audit row immediately.
    """
    # Create review task record in audit
    audit.log_event("human_review_task_created", {
        "case_id": case_id,
        "reason": reason,
        "task_status": "pending_ops_review",
    })

    return Proposal(
        agent="recovery_agent",
        subject=case_id,
        action=ActionKind.ESCALATE,
        params={"case_id": case_id, "escalated": True},
        reason=reason,
        inputs_used=["case_id"],
        llm_used=False,
        confidence=1.0,
    )

