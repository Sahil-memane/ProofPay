"""
PayPal webhook signature verification.

Uses PayPal's /v1/notifications/verify-webhook-signature API.
Returns True on valid, False on invalid.
Logs the result; the receiver returns 400 on failure (never silent 200).
"""
from __future__ import annotations

import httpx

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.paypal import auth

log = get_logger(__name__)


async def verify_paypal_signature(
    transmission_id: str,
    transmission_time: str,
    cert_url: str,
    auth_algo: str,
    transmission_sig: str,
    raw_body: bytes,
) -> bool:
    """
    Calls PayPal's verify-webhook-signature endpoint.
    Returns True if the signature is valid.
    """
    if not settings.paypal_webhook_id:
        log.warning("PAYPAL_WEBHOOK_ID not set — skipping signature verification (dev mode)")
        return True

    token = await auth.get_token()
    url = f"{settings.paypal_base_url}/v1/notifications/verify-webhook-signature"
    payload = {
        "auth_algo": auth_algo,
        "cert_url": cert_url,
        "transmission_id": transmission_id,
        "transmission_sig": transmission_sig,
        "transmission_time": transmission_time,
        "webhook_id": settings.paypal_webhook_id,
        "webhook_event": raw_body.decode("utf-8", errors="replace"),
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code == 200:
            result = resp.json()
            valid = result.get("verification_status") == "SUCCESS"
            log.info("Webhook signature verification: %s", result.get("verification_status"))
            return valid

        log.warning("Signature verification API returned %d", resp.status_code)
        return False

    except Exception as exc:
        log.error("Signature verification failed with exception: %s", exc)
        return False
