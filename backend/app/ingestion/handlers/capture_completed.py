"""
Handler: PAYMENT.CAPTURE.COMPLETED

Source of truth for escrow funding.
Writes the FUNDING ledger entry, moves all milestones to FUNDED,
and moves the project to FUNDED — supporting both in-memory and DB stores.
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

    project_found = None
    # 1. Update in-memory store
    try:
        from backend.app.api.projects import _PROJECTS, _MILESTONES
        for pid, p in _PROJECTS.items():
            if p.get("paypal_order_id") == order_id or pid == order_id:
                p["state"] = "FUNDED"
                p["paypal_capture_id"] = capture_id
                project_found = p
                for m in _MILESTONES.get(pid, []):
                    m["state"] = "FUNDED"
                log.info("capture_completed: in-memory project %s -> FUNDED", pid)
                break
    except Exception as mem_exc:
        log.warning("in-memory capture_completed update failed: %s", mem_exc)

    # 2. Update DB (if available)
    try:
        from backend.app.db.session import get_sync_session
        from backend.app.db.models.projects import Project, Milestone, LedgerEntry
        from sqlalchemy import select
        import uuid

        with get_sync_session() as session:
            project = session.execute(
                select(Project).where(Project.paypal_order_id == order_id)
            ).scalar_one_or_none()

            if project:
                if project.state != "FUNDED":
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
                    milestones = session.execute(
                        select(Milestone).where(Milestone.project_id == project.id)
                    ).scalars().all()
                    for m in milestones:
                        m.state = "FUNDED"
                    project.state = "FUNDED"
                    project.paypal_capture_id = capture_id
                    session.commit()
    except Exception as db_exc:
        log.warning("capture_completed DB update skipped/failed: %s", db_exc)

    # 3. Audit log
    try:
        from backend.app.audit import log_event as audit_log
        pid = (project_found or {}).get("id") or order_id
        audit_log("capture_completed", {
            "subject": pid,
            "actor": "webhook",
            "capture_id": capture_id,
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
        })
    except Exception as a_exc:
        log.warning("capture_completed audit log failed: %s", a_exc)
