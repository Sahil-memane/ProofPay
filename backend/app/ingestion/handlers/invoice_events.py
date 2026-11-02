"""
Handlers: INVOICING.INVOICE.PAID / CANCELLED
"""
from __future__ import annotations

from typing import Any

from backend.app.core.logging import get_logger
from backend.app.ingestion.handlers import register

log = get_logger(__name__)


@register("invoice_paid")
def handle_paid(event: dict[str, Any]) -> None:
    resource = event.get("payload", {}).get("resource", {})
    invoice_id = resource.get("id", "")
    amount = float(resource.get("primary_recipients", [{}])[0]
                   .get("billing_info", {})
                   .get("amount_due", {})
                   .get("value", 0) or 0)
    log.info("invoice_paid: invoice_id=%s amount=%s", invoice_id, amount)

    try:
        from backend.app.scheduler.jobs.handlers import invoice_paid
        invoice_paid(invoice_id=invoice_id, amount=amount)
    except Exception as exc:
        log.error("invoice_paid handler error: %s", exc, exc_info=True)
        raise


@register("invoice_cancelled")
def handle_cancelled(event: dict[str, Any]) -> None:
    resource = event.get("payload", {}).get("resource", {})
    invoice_id = resource.get("id", "")
    log.info("invoice_cancelled: invoice_id=%s", invoice_id)

    try:
        from backend.app.scheduler.jobs.handlers import invoice_cancelled
        invoice_cancelled(invoice_id=invoice_id, reason="paypal_invoice_cancelled")
    except Exception as exc:
        log.error("invoice_cancelled handler error: %s", exc, exc_info=True)
        raise
