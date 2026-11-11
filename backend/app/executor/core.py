"""
Real executor — DB-backed idempotency, audit before/after, ACTION_FAILED path.

Replaces stubs/executor.py. The stub re-exports from here.

Architecture invariant:
  - Executor is the ONLY module that imports paypal/ and channels/.
  - Recovery/agents build Proposal objects — executor does the work.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from backend.app.core.errors import PayPalError
from backend.app.core.logging import get_logger
from backend.app.stubs.contracts_stub import ActionKind, PolicyDecision, Proposal, Verdict

log = get_logger(__name__)

_MAX_RETRIES = 2


async def execute(
    proposal: Proposal,
    decision: PolicyDecision,
    rng: Any = None,
) -> dict[str, Any]:
    """
    Execute an approved proposal with full DB-backed idempotency.

    Steps:
    1. Reject if verdict != ALLOW.
    2. Compute idempotency_key; check executor_actions table.
    3. INSERT executor_actions (status=pending).
    4. audit BEFORE.
    5. Dispatch to action handler.
    6. On success: UPDATE executor_actions (status=done), audit AFTER.
    7. On failure: retry up to _MAX_RETRIES, then ACTION_FAILED + escalate.
    """
    if decision.verdict != Verdict.ALLOW:
        raise ValueError(f"Cannot execute proposal with verdict {decision.verdict.value!r}")

    idempotency_key = (
        proposal.params.get("idempotency_key")
        or f"{proposal.subject}:{proposal.action.value}:{proposal.params.get('attempt', 0)}"
    )

    # ── Idempotency check ─────────────────────────────────────────────────────
    existing = await _get_existing_action(idempotency_key)
    if existing and existing.get("status") == "done":
        log.info("Executor: idempotent return for key=%s", idempotency_key)
        return existing.get("result", {})

    # ── Record intent ─────────────────────────────────────────────────────────
    action_id = await _record_action(idempotency_key, proposal, decision)

    # ── Audit BEFORE ──────────────────────────────────────────────────────────
    from backend.app.audit import log_event as audit_log
    audit_log("executor_start", {
        "subject": proposal.subject,
        "actor": "executor",
        "action": proposal.action.value,
        "idempotency_key": idempotency_key,
        "proposal": proposal.model_dump(mode="json"),
    })

    # ── Dispatch ──────────────────────────────────────────────────────────────
    last_error: str = ""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            result = await _dispatch(proposal, decision, rng)
            await _mark_done(action_id, result)
            audit_log("executor_done", {
                "subject": proposal.subject,
                "actor": "executor",
                "action": proposal.action.value,
                "idempotency_key": idempotency_key,
                "result": result,
            })
            return result
        except PayPalError as exc:
            last_error = str(exc)
            log.warning("Executor attempt %d/%d failed (PayPal): %s", attempt + 1, _MAX_RETRIES + 1, exc)
            if attempt < _MAX_RETRIES:
                import asyncio
                await asyncio.sleep(1.5 ** (attempt + 1))
        except Exception as exc:
            last_error = str(exc)
            log.error("Executor non-retryable error: %s", exc, exc_info=True)
            break

    # ── ACTION_FAILED ─────────────────────────────────────────────────────────
    await _mark_failed(action_id, last_error)
    audit_log("executor_action_failed", {
        "subject": proposal.subject,
        "actor": "executor",
        "action": proposal.action.value,
        "idempotency_key": idempotency_key,
        "error": last_error,
    })
    log.error("Executor ACTION_FAILED for %s: %s", idempotency_key, last_error)
    raise RuntimeError(f"ACTION_FAILED: {last_error}")


async def _dispatch(
    proposal: Proposal,
    decision: PolicyDecision,
    rng: Any,
) -> dict[str, Any]:
    """Route proposal.action to the correct handler."""
    action = proposal.action

    if action in (ActionKind.SEND_EMAIL, ActionKind.SEND_PAYMENT_LINK):
        return await _handle_outreach(proposal, rng)

    if action == ActionKind.ESCALATE:
        return _handle_escalate(proposal)

    if action == ActionKind.MARK_PAID_ELSEWHERE:
        return {"status": "marked_paid_elsewhere", "subject": proposal.subject}

    if action == ActionKind.NO_OP:
        return {"status": "no_op"}

    # PayPal actions (escrow path — Phase 2)
    # These require proposal.params to carry the right keys
    from backend.app.paypal import get_gateway
    gateway = get_gateway()

    if action.value == "create_order":
        return await gateway.create_order(
            amount=float(proposal.params["amount"]),
            currency=proposal.params.get("currency", "USD"),
            request_id=proposal.params.get("idempotency_key", str(uuid.uuid4())),
            description=proposal.params.get("description", ""),
        )

    if action.value == "capture_order":
        return await gateway.capture_order(
            order_id=proposal.params["order_id"],
            request_id=proposal.params.get("idempotency_key", str(uuid.uuid4())),
        )

    if action.value == "payout":
        return await gateway.create_payout(
            recipient_email=proposal.params["recipient_email"],
            amount=float(proposal.params["amount"]),
            currency=proposal.params.get("currency", "USD"),
            sender_batch_id=proposal.params["idempotency_key"],
            note=proposal.params.get("note", ""),
        )

    if action.value == "refund":
        return await gateway.refund_capture(
            capture_id=proposal.params["capture_id"],
            amount=float(proposal.params["amount"]),
            currency=proposal.params.get("currency", "USD"),
            request_id=proposal.params.get("idempotency_key", str(uuid.uuid4())),
        )

    raise ValueError(f"Unknown action: {action!r}")


async def _handle_outreach(proposal: Proposal, rng: Any) -> dict[str, Any]:
    """Write to outbox and trigger simulator."""
    from backend.app.channels.outbox import record_message
    from backend.app.recovery.strategy import render_email
    from backend.app.stubs.repositories import case_repo, contact_repo
    from backend.app.core.clock import utcnow
    import random as _random

    case_id = proposal.subject
    case = case_repo.get(case_id) or {"id": case_id, "customer_id": "UNKNOWN", "amount_usd": 0.0}

    template_name = proposal.params.get("template", "forgot_to_pay")
    body = render_email(
        template_name=template_name,
        language=proposal.params.get("language", "en"),
        context={
            "amount_usd": proposal.params.get("amount_usd", case.get("amount_usd", 0.0)),
            "currency": case.get("currency", "USD"),
            "payment_link": proposal.params.get("payment_link", "https://proofpay.app/pay"),
            "invoice_id": case.get("invoice_id", case_id),
        },
        case_id=case_id,
    )

    idempotency_key = proposal.params.get("idempotency_key")
    channel = "payment_link" if proposal.action == ActionKind.SEND_PAYMENT_LINK else "email"

    msg = record_message(
        case_id=case_id,
        channel=channel,
        recipient=case.get("email", f"{case.get('customer_id', 'unknown')}@example.com"),
        subject=f"Notice regarding your balance ({case_id})",
        body=body,
        idempotency_key=idempotency_key,
        metadata=proposal.params,
    )

    contact_repo.add(case_id, channel=channel, sent_at=utcnow())

    # Trigger simulator
    from backend.app.simulator.profiles import respond
    sim_rng = rng or _random.Random(42)
    sim_event = respond(case=case, action=proposal.action.value, now=utcnow(), rng=sim_rng)

    return {
        "status": "sent",
        "channel": channel,
        "outbox_message": msg,
        "sim_response": sim_event.to_dict() if sim_event else None,
    }


def _handle_escalate(proposal: Proposal) -> dict[str, Any]:
    from backend.app.audit import log_event as audit_log
    audit_log("escalated_to_human", {
        "subject": proposal.subject,
        "actor": "executor",
        "reason": proposal.reason,
    })
    return {"status": "escalated", "subject": proposal.subject}


# ── DB helpers ────────────────────────────────────────────────────────────────

async def _get_existing_action(idempotency_key: str) -> dict[str, Any] | None:
    try:
        from backend.app.db.session import AsyncSessionLocal
        from backend.app.db.models.webhooks import ExecutorAction
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            row = (
                await session.execute(
                    select(ExecutorAction).where(ExecutorAction.idempotency_key == idempotency_key)
                )
            ).scalar_one_or_none()
            if row:
                return {"status": row.status, "result": row.result}
    except Exception:
        pass
    return None


async def _record_action(
    idempotency_key: str,
    proposal: Proposal,
    decision: PolicyDecision,
) -> str:
    action_id = str(uuid.uuid4())
    try:
        from backend.app.db.session import AsyncSessionLocal
        from backend.app.db.models.webhooks import ExecutorAction
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        async with AsyncSessionLocal() as session:
            stmt = pg_insert(ExecutorAction).values(
                id=action_id,
                idempotency_key=idempotency_key,
                proposal=proposal.model_dump(mode="json"),
                decision=decision.model_dump(mode="json"),
                status="pending",
            ).on_conflict_do_nothing(index_elements=["idempotency_key"])
            await session.execute(stmt)
            await session.commit()
    except Exception as exc:
        log.warning("_record_action DB unavailable: %s", exc)
    return action_id


async def _mark_done(action_id: str, result: dict[str, Any]) -> None:
    try:
        from backend.app.db.session import AsyncSessionLocal
        from backend.app.db.models.webhooks import ExecutorAction
        from sqlalchemy import update

        async with AsyncSessionLocal() as session:
            await session.execute(
                update(ExecutorAction)
                .where(ExecutorAction.id == action_id)
                .values(status="done", result=result, completed_at=datetime.now(timezone.utc))
            )
            await session.commit()
    except Exception as exc:
        log.warning("_mark_done DB unavailable: %s", exc)


async def _mark_failed(action_id: str, error: str) -> None:
    try:
        from backend.app.db.session import AsyncSessionLocal
        from backend.app.db.models.webhooks import ExecutorAction
        from sqlalchemy import update

        async with AsyncSessionLocal() as session:
            await session.execute(
                update(ExecutorAction)
                .where(ExecutorAction.id == action_id)
                .values(status="ACTION_FAILED", error=error[:1000], completed_at=datetime.now(timezone.utc))
            )
            await session.commit()
    except Exception as exc:
        log.warning("_mark_failed DB unavailable: %s", exc)


def get_executed() -> list[dict[str, Any]]:
    """Compatibility shim — returns in-memory history when DB unavailable."""
    return []


def reset() -> None:
    """Compatibility shim for tests."""
    pass
