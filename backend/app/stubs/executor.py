"""
Stub executor — wraps execution for Dev 3 recovery tests with sync compatibility,
outbox recording, customer simulation, and idempotency tracking.
"""
from __future__ import annotations

import random
from typing import Any

from backend.app.channels.outbox import record_message
from backend.app.recovery.strategy import render_email
from backend.app.simulator.profiles import respond
from backend.app.stubs import clock
from backend.app.stubs.contracts_stub import ActionKind, PolicyDecision, Proposal, Verdict
from backend.app.stubs.repositories import case_repo, contact_repo

_executed: list[dict[str, Any]] = []
_EXECUTED_KEYS: dict[str, dict[str, Any]] = {}


def execute(
    proposal: Proposal,
    decision: PolicyDecision,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Execute an approved proposal with sync compatibility."""
    if decision.verdict != Verdict.ALLOW:
        raise ValueError(f"Cannot execute proposal with verdict {decision.verdict.value}")

    idempotency_key = proposal.params.get("idempotency_key")
    if idempotency_key and idempotency_key in _EXECUTED_KEYS:
        return _EXECUTED_KEYS[idempotency_key]

    case_id = proposal.subject
    case = case_repo.get(case_id) or {"id": case_id, "customer_id": "CUST-00000", "amount_usd": 100.0}

    msg_record = None
    if proposal.action in (ActionKind.SEND_EMAIL, ActionKind.SEND_PAYMENT_LINK):
        template_name = proposal.params.get("template", "forgot_to_pay")
        body = render_email(
            template_name=template_name,
            language=proposal.params.get("language", "en"),
            context={
                "amount_usd": proposal.params.get("amount_usd", case.get("amount_usd", 100.0)),
                "currency": case.get("currency", "USD"),
                "payment_link": proposal.params.get("payment_link", "https://proofpay.invalid/pay"),
                "invoice_id": case.get("invoice_id", case_id),
            },
            case_id=case_id,
        )
        channel = "email" if proposal.action == ActionKind.SEND_EMAIL else "payment_link"
        msg_record = record_message(
            case_id=case_id,
            channel=channel,
            recipient=case.get("email", f"{case.get('customer_id')}@example.com"),
            subject=f"Notice regarding your balance ({case_id})",
            body=body,
            idempotency_key=idempotency_key,
            metadata=proposal.params,
        )
        contact_repo.add(
            case_id,
            channel=channel,
            sent_at=clock.utcnow(),
        )

    sim_event = None
    if proposal.action in (ActionKind.SEND_EMAIL, ActionKind.SEND_PAYMENT_LINK):
        sim_rng = rng or random.Random(42)
        sim_event = respond(
            case=case,
            action=proposal.action.value,
            now=clock.utcnow(),
            rng=sim_rng,
        )

    receipt = {
        "receipt_id": f"exec-{len(_executed):04d}",
        "proposal": proposal.model_dump(),
        "status": "sent",
        "outbox_message": msg_record,
        "sim_response": sim_event.to_dict() if sim_event else None,
        "executed_at": clock.utcnow().isoformat(),
    }

    _executed.append(receipt)
    if idempotency_key:
        _EXECUTED_KEYS[idempotency_key] = receipt

    return receipt


def get_executed() -> list[dict[str, Any]]:
    return list(_executed)


def reset() -> None:
    _executed.clear()
    _EXECUTED_KEYS.clear()
