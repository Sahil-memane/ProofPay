"""
Webhook receiver router — /webhooks/paypal and /sim/events endpoints.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, Response

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.ingestion.signature import verify_paypal_signature

log = get_logger(__name__)

router = APIRouter(tags=["ingestion"])


@router.post("/webhooks/paypal")
async def receive_webhook(request: Request) -> Response:
    """
    Receive a PayPal webhook:
    1. Read raw body (needed for signature verification).
    2. Verify PayPal signature — return 400 on failure.
    3. Insert into webhook_events with ON CONFLICT DO NOTHING.
    4. Return 200 immediately (processing is async).
    """
    raw_body = await request.body()

    # Signature verification
    transmission_id = request.headers.get("PAYPAL-TRANSMISSION-ID", "")
    transmission_time = request.headers.get("PAYPAL-TRANSMISSION-TIME", "")
    cert_url = request.headers.get("PAYPAL-CERT-URL", "")
    auth_algo = request.headers.get("PAYPAL-AUTH-ALGO", "")
    transmission_sig = request.headers.get("PAYPAL-TRANSMISSION-SIG", "")

    valid = await verify_paypal_signature(
        transmission_id=transmission_id,
        transmission_time=transmission_time,
        cert_url=cert_url,
        auth_algo=auth_algo,
        transmission_sig=transmission_sig,
        raw_body=raw_body,
    )
    if not valid:
        log.warning("Webhook signature verification FAILED — rejecting")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_id = body.get("id") or str(uuid.uuid4())
    event_type = body.get("event_type", "unknown")

    await _enqueue_event(event_id=event_id, event_type=event_type, source="paypal", payload=body)

    log.info("Webhook received and queued: %s %s", event_type, event_id)
    return Response(status_code=200)


@router.post("/sim/events")
async def receive_sim_event(
    request: Request,
    x_tick_token: str = Header(default=""),
) -> dict[str, Any]:
    """
    Accept a simulated event (no PayPal signature required).
    Only available when DEMO_MODE or SIMULATOR_ENABLED is true.
    Protected by the internal tick token.
    """
    if not (settings.demo_mode or settings.simulator_enabled):
        raise HTTPException(status_code=404, detail="Simulator not enabled")

    if x_tick_token != settings.internal_tick_token:
        raise HTTPException(status_code=401, detail="Invalid tick token")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_id = body.get("id") or body.get("event_id") or str(uuid.uuid4())
    event_type = body.get("event_type") or body.get("event", "sim.event")

    await _enqueue_event(event_id=event_id, event_type=event_type, source="sim", payload=body)

    return {"queued": True, "event_id": event_id, "event_type": event_type}


async def _enqueue_event(
    event_id: str,
    event_type: str,
    source: str,
    payload: dict[str, Any],
) -> None:
    """Insert into webhook_events; ON CONFLICT (event_id) DO NOTHING."""
    try:
        from backend.app.db.session import AsyncSessionLocal
        from backend.app.db.models.webhooks import WebhookEvent
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        async with AsyncSessionLocal() as session:
            stmt = pg_insert(WebhookEvent).values(
                id=str(uuid.uuid4()),
                event_id=event_id,
                event_type=event_type,
                source=source,
                payload=payload,
                status="pending",
            ).on_conflict_do_nothing(index_elements=["event_id"])
            await session.execute(stmt)
            await session.commit()

    except Exception as exc:
        log.error("Failed to enqueue event %s: %s", event_id, exc, exc_info=True)
        raise
