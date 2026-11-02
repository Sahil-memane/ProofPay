"""
PayPal OAuth client-credentials token cache.

Fetches a Bearer token on first call. Automatically refreshes 60s before expiry.
Retries once on 401 by fetching a fresh token.
"""
from __future__ import annotations

import base64
import time
from datetime import datetime, timezone

import httpx

from backend.app.core.config import settings
from backend.app.core.errors import PayPalError
from backend.app.core.logging import get_logger

log = get_logger(__name__)

_token: str | None = None
_expires_at: float = 0.0  # Unix timestamp


def _basic_auth() -> str:
    creds = f"{settings.paypal_client_id}:{settings.paypal_client_secret}"
    return "Basic " + base64.b64encode(creds.encode()).decode()


async def get_token() -> str:
    """Return a valid Bearer token, refreshing if within 60s of expiry."""
    global _token, _expires_at

    now = time.time()
    if _token and now < _expires_at - 60:
        return _token

    return await _refresh_token()


async def _refresh_token() -> str:
    global _token, _expires_at

    url = f"{settings.paypal_base_url}/v1/oauth2/token"
    headers = {
        "Authorization": _basic_auth(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "client_credentials"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, headers=headers, data=data)

    if resp.status_code != 200:
        raise PayPalError(
            f"PayPal token fetch failed: {resp.status_code}",
            paypal_response=resp.json() if resp.content else {},
        )

    body = resp.json()
    _token = body["access_token"]
    _expires_at = time.time() + int(body.get("expires_in", 3600))
    log.info("PayPal token refreshed, expires_in=%s", body.get("expires_in"))
    return _token


def invalidate() -> None:
    """Force a token refresh on the next call (called after 401)."""
    global _token, _expires_at
    _token = None
    _expires_at = 0.0
