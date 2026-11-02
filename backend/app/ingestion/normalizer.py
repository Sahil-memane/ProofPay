"""
Webhook event normalizer.

Maps raw PayPal event shapes to our internal NormalizedEvent format.
Unknown event types are passed through with event_type="unknown".
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from backend.app.core.logging import get_logger

log = get_logger(__name__)

# Maps PayPal event_type string → our internal event_type key
_EVENT_MAP: dict[str, str] = {
    "PAYMENT.CAPTURE.COMPLETED": "capture_completed",
    "PAYMENT.CAPTURE.DENIED": "capture_denied",
    "PAYMENT.CAPTURE.REFUNDED": "capture_refunded",
    "PAYMENT.PAYOUTS-ITEM.SUCCEEDED": "payout_item_succeeded",
    "PAYMENT.PAYOUTS-ITEM.DENIED": "payout_item_denied",
    "PAYMENT.PAYOUTS-ITEM.FAILED": "payout_item_failed",
    "BILLING.SUBSCRIPTION.PAYMENT.FAILED": "subscription_payment_failed",
    "BILLING.SUBSCRIPTION.CANCELLED": "subscription_cancelled",
    "INVOICING.INVOICE.PAID": "invoice_paid",
    "INVOICING.INVOICE.CANCELLED": "invoice_cancelled",
    "CUSTOMER.DISPUTE.CREATED": "dispute_created",
    "CUSTOMER.DISPUTE.UPDATED": "dispute_updated",
    "CUSTOMER.DISPUTE.RESOLVED": "dispute_resolved",
    # Internal / sim events
    "funding.failed": "funding_failed",
    "instalment.failed": "instalment_failed",
}


def normalize(raw_event: dict[str, Any], source: str = "paypal") -> dict[str, Any]:
    """
    Convert a raw PayPal (or sim) event dict to our normalised shape.
    Returns a plain dict matching the NormalizedEvent contract.
    """
    paypal_event_type = raw_event.get("event_type", raw_event.get("event", "unknown"))
    internal_type = _EVENT_MAP.get(paypal_event_type, paypal_event_type)

    event_id = (
        raw_event.get("id")
        or raw_event.get("event_id")
        or str(uuid.uuid4())
    )

    return {
        "event_id": event_id,
        "event_type": internal_type,
        "paypal_event_type": paypal_event_type,
        "source": source,
        "payload": raw_event,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
