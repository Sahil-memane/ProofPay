"""
Handler: PAYMENT.CAPTURE.COMPLETED

Source of truth for escrow funding.
Writes the FUNDING ledger entry, moves all milestones to FUNDED,
and moves the project to FUNDED — all in one transaction.
"""
from __future__ import annotations

from typing import Any

from backend.app.core.logging import get_logger
from backend.app.ingestion.handlers import register

log = get_logger(__name__)


@register("capture_completed")
def handle(event: dict[str, Any]) -> None:
    resource = event.get("payload", {}).get("resource", {})
    capture_id = resource.get("id", "")
    amount_val = resource.get("amount", {}).get("value", "0")
    currency = resource.get("amount", {}).get("currency_code", "USD")
    order_id = resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id") or resource.get("order_id", "")

    try:
        amount = float(amount_val)
    except ValueError:
        amount = 0.0

    log.info("capture_completed: capture_id=%s order_id=%s amount=%s %s",
             capture_id, order_id, amount, currency)

    try:
        from backend.app.db.session import get_sync_session
        from backend.app.db.models.projects import Project, Milestone, LedgerEntry
        from backend.app.audit import log_event as audit_log
        from sqlalchemy import select
        import uuid
        from datetime import datetime, timezone

        with get_sync_session() as session:
            # Find project by order_id
            project = session.execute(
                select(Project).where(Project.paypal_order_id == order_id)
            ).scalar_one_or_none()

            if not project:
                log.warning("capture_completed: no project found for order_id=%s — queuing for later", order_id)
                return

            # Idempotency: already funded?
            if project.state == "FUNDED":
                log.info("capture_completed: project %s already FUNDED — skipping", project.id)
                return

            # Write FUNDING ledger entry (INSERT-ONLY)
            entry = LedgerEntry(
                id=str(uuid.uuid4()),
                type="FUNDING",
                subject_id=project.id,
                amount=amount,
                currency=currency,
                paypal_id=capture_id,
                note=f"Escrow funded via PayPal capture {capture_id}",
            )
            session.add(entry)

            # Move milestones to FUNDED
            milestones = session.execute(
                select(Milestone).where(Milestone.project_id == project.id)
            ).scalars().all()
            for m in milestones:
                m.state = "FUNDED"

            # Move project to FUNDED
            project.state = "FUNDED"
            project.paypal_capture_id = capture_id

            session.commit()

        audit_log("capture_completed", {
            "subject": project.id,
            "actor": "webhook",
            "capture_id": capture_id,
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
        })
        log.info("capture_completed: project %s → FUNDED", project.id)

    except Exception as exc:
        log.error("capture_completed handler error: %s", exc, exc_info=True)
        raise
