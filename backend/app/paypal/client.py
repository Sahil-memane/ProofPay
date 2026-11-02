"""
Base async httpx client for PayPal REST API calls.

Features:
- Bearer token injection via auth.get_token()
- PayPal-Request-Id header on every write
- Exponential backoff on 429 and 5xx (max 3 retries)
- No retry on 4xx validation errors
- Secrets redacted from logs
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any

import httpx

from backend.app.core.config import settings
from backend.app.core.errors import PayPalError
from backend.app.core.logging import get_logger, redact
from backend.app.paypal import auth

log = get_logger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 1.5  # seconds


async def _request(
    method: str,
    path: str,
    *,
    request_id: str | None = None,
    json: Any = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Make an authenticated PayPal API call with retry logic.
    Returns the parsed JSON body on success.
    Raises PayPalError on non-2xx after retries.
    """
    url = f"{settings.paypal_base_url}{path}"
    req_id = request_id or str(uuid.uuid4())

    for attempt in range(_MAX_RETRIES):
        token = await auth.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        if method.upper() in ("POST", "PUT", "PATCH"):
            headers["PayPal-Request-Id"] = req_id

        log.info(
            "PayPal %s %s attempt=%d request_id=%s",
            method.upper(), path, attempt + 1, req_id,
        )

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.request(
                method, url, headers=headers, json=json, params=params
            )

        log.info("PayPal response: status=%d path=%s", resp.status_code, path)

        if resp.status_code == 401 and attempt == 0:
            # Token may be stale — invalidate and retry once
            auth.invalidate()
            continue

        if resp.status_code in (429,) or resp.status_code >= 500:
            if attempt < _MAX_RETRIES - 1:
                delay = _BACKOFF_BASE ** (attempt + 1)
                log.warning(
                    "PayPal %s %d — retrying in %.1fs", path, resp.status_code, delay
                )
                await asyncio.sleep(delay)
                continue
            raise PayPalError(
                f"PayPal {method} {path} failed after {_MAX_RETRIES} attempts: {resp.status_code}",
                paypal_response=_safe_json(resp),
            )

        if resp.status_code >= 400:
            # 4xx validation error — do NOT retry
            raise PayPalError(
                f"PayPal {method} {path} client error: {resp.status_code}",
                paypal_response=_safe_json(resp),
            )

        return _safe_json(resp)

    raise PayPalError(f"PayPal {method} {path}: max retries exceeded")


def _safe_json(resp: httpx.Response) -> dict[str, Any]:
    try:
        return resp.json()
    except Exception:
        return {"raw": redact(resp.text[:500])}


# ── Convenience wrappers ───────────────────────────────────────────────────────

async def get(path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    return await _request("GET", path, params=params)


async def post(path: str, body: Any, request_id: str | None = None) -> dict[str, Any]:
    return await _request("POST", path, json=body, request_id=request_id)


async def patch(path: str, body: Any, request_id: str | None = None) -> dict[str, Any]:
    return await _request("PATCH", path, json=body, request_id=request_id)
