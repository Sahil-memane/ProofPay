"""
Handler: PAYMENT.CAPTURE.DENIED / PAYMENT.CAPTURE.REFUNDED
"""
from __future__ import annotations

from typing import Any

from backend.app.core.logging import get_logger
from backend.app.ingestion.handlers import register

log = get_logger(__name__)


@register("capture_denied")
def handle_denied(event: dict[str, Any]) -> None:
    resource = event.get("payload", {}).get("resource", {})
    order_id = resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id", "")
    log.warning("capture_denied: order_id=%s — opening recovery case", order_id)

    try:
        from backend.app.recovery.bridges import handle_funding_failed
        handle_funding_failed(
            project_id=order_id,
            client_id="unknown",
            amount_usd=float(resource.get("amount", {}).get("value", 0)),
            failure_code="capture_denied",
        )
    except Exception as exc:
        log.error("capture_denied handler error: %s", exc, exc_info=True)
        raise


@register("capture_refunded")
def handle_refunded(event: dict[str, Any]) -> None:
    resource = event.get("payload", {}).get("resource", {})
    refund_id = resource.get("id", "")
    log.info("capture_refunded: refund_id=%s", refund_id)

    try:
        from backend.app.audit import log_event as audit_log
        audit_log("capture_refunded", {
            "subject": refund_id,
            "actor": "webhook",
            "refund_id": refund_id,
            "payload": resource,
        })
    except Exception as exc:
        log.error("capture_refunded handler error: %s", exc, exc_info=True)
