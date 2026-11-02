"""
Handler: BILLING.SUBSCRIPTION.PAYMENT.FAILED
"""
from __future__ import annotations

from typing import Any

from backend.app.core.logging import get_logger
from backend.app.ingestion.handlers import register

log = get_logger(__name__)


@register("subscription_payment_failed")
def handle(event: dict[str, Any]) -> None:
    resource = event.get("payload", {}).get("resource", {})
    event_id = event.get("event_id", "")
    subscriber = resource.get("subscriber", {})
    customer_id = subscriber.get("email_address", "") or subscriber.get("payer_id", "unknown")

    billing_info = resource.get("billing_info", {})
    last_failed = billing_info.get("last_failed_payment", {})
    amount = float(last_failed.get("amount", {}).get("value", 0))
    currency = last_failed.get("amount", {}).get("currency_code", "USD")
    failure_code = last_failed.get("reason_code", "subscription_payment_failed")

    log.info("subscription_payment_failed: customer=%s amount=%s %s", customer_id, amount, currency)

    try:
        from backend.app.scheduler.jobs.handlers import subscription_payment_failed
        subscription_payment_failed(
            event_id=event_id,
            payload={
                "customer_id": customer_id,
                "failure_code": failure_code,
                "amount_usd": amount,
                "currency": currency,
                "subscription_id": resource.get("id", ""),
            },
        )
    except Exception as exc:
        log.error("subscription_payment_failed handler error: %s", exc, exc_info=True)
        raise
