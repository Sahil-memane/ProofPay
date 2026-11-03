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
    """
    Wire payout success → milestone RELEASED.

    Idempotency key convention (set by executor):
        sender_batch_id = f"{milestone_id}:{attempt}"
    We split on ':' to recover the milestone_id.
    """
    resource = event.get("payload", {}).get("resource", {})
    payout_item_id = resource.get("payout_item_id", "")
    sender_batch_id = resource.get("sender_batch_id", "")
    log.info(
        "payout_item_succeeded: payout_item_id=%s sender_batch_id=%s",
        payout_item_id,
        sender_batch_id,
    )

    try:
        from backend.app.audit import log_event as audit_log
        from backend.app.api.projects import _PROJECTS, _MILESTONES  # in-memory store

        # Derive milestone_id from idempotency key  "milestone_id:attempt"
        milestone_id = sender_batch_id.split(":")[0] if ":" in sender_batch_id else sender_batch_id

        # Find the milestone across all projects
        milestone_found: dict[str, Any] | None = None
        project_found: dict[str, Any] | None = None

        for project_id, milestones in _MILESTONES.items():
            for m in milestones:
                if m.get("id") == milestone_id:
                    milestone_found = m
                    project_found = _PROJECTS.get(project_id)
                    break
            if milestone_found:
                break

        if milestone_found is None:
            log.warning(
                "payout_item_succeeded: milestone not found for sender_batch_id=%s — audit only",
                sender_batch_id,
            )
            audit_log("payout_item_succeeded", {
                "subject": sender_batch_id,
                "actor": "webhook",
                "payout_item_id": payout_item_id,
                "sender_batch_id": sender_batch_id,
                "milestone_id": milestone_id,
                "warning": "milestone_not_found",
            })
            return

        # Idempotent: only transition if currently in SUBMITTED / CLIENT_APPROVED
        current_state = milestone_found.get("state", "")
        if current_state == "RELEASED":
            log.info("payout_item_succeeded: milestone %s already RELEASED — skipping", milestone_id)
            return

        # Transition milestone → RELEASED
        milestone_found["state"] = "RELEASED"
        milestone_found["payout_item_id"] = payout_item_id

        freelancer_id = (project_found or {}).get("freelancer_id", "")

        audit_log("milestone_released", {
            "subject": milestone_id,
            "actor": "webhook",
            "event": "payout_item_succeeded",
            "payout_item_id": payout_item_id,
            "sender_batch_id": sender_batch_id,
            "milestone_id": milestone_id,
            "freelancer_id": freelancer_id,
            "ledger_entry": {
                "type": "RELEASE",
                "amount": milestone_found.get("amount", 0),
                "currency": milestone_found.get("currency", "USD"),
                "milestone_id": milestone_id,
            },
        })

        # Stub reputation event — will be wired to real rep module in Phase 3
        log.info(
            "rep_event(freelancer=%s, event=on_time_release) — stub, wired Phase 3",
            freelancer_id,
        )

        log.info("payout_item_succeeded: milestone %s -> RELEASED", milestone_id)

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
