"""
Handlers: PAYMENT.PAYOUTS-ITEM.SUCCEEDED / DENIED / FAILED
"""
from __future__ import annotations

from typing import Any

from backend.app.core.logging import get_logger
from backend.app.ingestion.handlers import register

log = get_logger(__name__)


@register("payout_item_succeeded")
def handle_succeeded(event: dict[str, Any]) -> None:
    resource = event.get("payload", {}).get("resource", {})
    payout_item_id = resource.get("payout_item_id", "")
    sender_batch_id = resource.get("sender_batch_id", "")
    log.info("payout_item_succeeded: payout_item_id=%s sender_batch_id=%s",
             payout_item_id, sender_batch_id)

    try:
        from backend.app.audit import log_event as audit_log
        # The executor_action idempotency_key is the sender_batch_id
        # Milestone state update happens via executor confirmation — audit it here
        audit_log("payout_item_succeeded", {
            "subject": sender_batch_id,
            "actor": "webhook",
            "payout_item_id": payout_item_id,
            "sender_batch_id": sender_batch_id,
        })
        # TODO (Phase 2): look up milestone by sender_batch_id → set state=RELEASED,
        # write RELEASE ledger entry, stub reputation event
        log.info("payout_item_succeeded: audited — milestone release to be wired in Phase 2")
    except Exception as exc:
        log.error("payout_item_succeeded handler error: %s", exc, exc_info=True)
        raise


@register("payout_item_denied")
def handle_denied(event: dict[str, Any]) -> None:
    resource = event.get("payload", {}).get("resource", {})
    payout_item_id = resource.get("payout_item_id", "")
    log.warning("payout_item_denied: payout_item_id=%s", payout_item_id)

    try:
        from backend.app.audit import log_event as audit_log
        audit_log("payout_item_denied", {
            "subject": payout_item_id,
            "actor": "webhook",
            "payout_item_id": payout_item_id,
            "payload": resource,
        })
    except Exception as exc:
        log.error("payout_item_denied handler error: %s", exc, exc_info=True)


@register("payout_item_failed")
def handle_failed(event: dict[str, Any]) -> None:
    handle_denied(event)
