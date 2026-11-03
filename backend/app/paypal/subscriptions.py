"""
PayPal Subscriptions v1 API wrapper.

Provides functions to query and manage subscriptions for the recovery
agent (subscription_failed webhook path) and the dashboard.

Import boundary: this module is imported by executor and ingestion only.
Agents MUST NOT import from this module.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


async def get_subscription(
    subscription_id: str,
    *,
    access_token: str | None = None,
) -> dict[str, Any]:
    """
    GET /v1/billing/subscriptions/{id}
    Returns subscription detail including status, billing_info, subscriber.
    """
    from backend.app.paypal import get_gateway
    gateway = get_gateway()

    try:
        result = await gateway._request(  # type: ignore[attr-defined]
            "GET",
            f"/v1/billing/subscriptions/{subscription_id}",
            access_token=access_token,
        )
        log.debug("get_subscription %s → status=%s", subscription_id, result.get("status"))
        return result
    except AttributeError:
        # FakePayPal stub path — return synthetic record
        return {
            "id": subscription_id,
            "status": "ACTIVE",
            "plan_id": "fake-plan-id",
            "subscriber": {"email_address": "subscriber@example.com"},
            "billing_info": {"outstanding_balance": {"value": "0.00", "currency_code": "USD"}},
        }


async def cancel_subscription(
    subscription_id: str,
    reason: str = "Cancelled by ProofPay",
    *,
    access_token: str | None = None,
) -> dict[str, Any]:
    """
    POST /v1/billing/subscriptions/{id}/cancel
    Returns 204 No Content on success; we return a status dict.
    """
    from backend.app.paypal import get_gateway
    gateway = get_gateway()

    try:
        await gateway._request(  # type: ignore[attr-defined]
            "POST",
            f"/v1/billing/subscriptions/{subscription_id}/cancel",
            json={"reason": reason},
            access_token=access_token,
        )
        log.info("cancel_subscription %s — succeeded", subscription_id)
        return {"subscription_id": subscription_id, "status": "CANCELLED"}
    except AttributeError:
        return {"subscription_id": subscription_id, "status": "CANCELLED_FAKE"}


async def capture_outstanding_balance(
    subscription_id: str,
    note: str = "Outstanding balance capture",
    *,
    access_token: str | None = None,
) -> dict[str, Any]:
    """
    POST /v1/billing/subscriptions/{id}/capture
    Captures any unpaid balance on the subscription.
    """
    from backend.app.paypal import get_gateway
    gateway = get_gateway()

    try:
        result = await gateway._request(  # type: ignore[attr-defined]
            "POST",
            f"/v1/billing/subscriptions/{subscription_id}/capture",
            json={"note": note, "capture_type": "OUTSTANDING_BALANCE"},
            access_token=access_token,
        )
        log.info("capture_outstanding_balance %s → %s", subscription_id, result)
        return result
    except AttributeError:
        return {
            "subscription_id": subscription_id,
            "status": "COMPLETED_FAKE",
            "amount": {"value": "0.00", "currency_code": "USD"},
        }


async def list_transactions(
    subscription_id: str,
    start_time: str | None = None,
    end_time: str | None = None,
    *,
    access_token: str | None = None,
) -> list[dict[str, Any]]:
    """
    GET /v1/billing/subscriptions/{id}/transactions
    Returns list of transaction records for the subscription.
    """
    from backend.app.paypal import get_gateway
    gateway = get_gateway()

    params: dict[str, str] = {}
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time

    try:
        result = await gateway._request(  # type: ignore[attr-defined]
            "GET",
            f"/v1/billing/subscriptions/{subscription_id}/transactions",
            params=params,
            access_token=access_token,
        )
        return result.get("transactions", [])
    except AttributeError:
        return []
