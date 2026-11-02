"""
Webhook ingestion worker.

Runs as a background asyncio task inside the FastAPI process.
Claims pending webhook_events rows with FOR UPDATE SKIP LOCKED,
normalizes, dispatches to registered handlers, and marks done/dead_letter.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from backend.app.core.logging import get_logger
from backend.app.ingestion.normalizer import normalize

log = get_logger(__name__)

_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = [2, 5, 15]  # per attempt
_BATCH_SIZE = 10
_POLL_INTERVAL = 2.0  # seconds


async def run_worker_loop() -> None:
    """Entry point — started from FastAPI lifespan as asyncio.create_task."""
    log.info("Webhook worker started")
    while True:
        try:
            await _process_batch()
        except Exception as exc:
            log.error("Worker loop error: %s", exc, exc_info=True)
        await asyncio.sleep(_POLL_INTERVAL)


async def _process_batch() -> None:
    """Claim and process up to _BATCH_SIZE pending events."""
    try:
        from sqlalchemy.ext.asyncio import AsyncSession
        from backend.app.db.session import AsyncSessionLocal
        from backend.app.db.models.webhooks import WebhookEvent
        from sqlalchemy import select, update

        async with AsyncSessionLocal() as session:
            # FOR UPDATE SKIP LOCKED — only one worker claims each row
            stmt = (
                select(WebhookEvent)
                .where(
                    WebhookEvent.status == "pending",
                    WebhookEvent.attempts < _MAX_ATTEMPTS,
                )
                .order_by(WebhookEvent.created_at)
                .limit(_BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            rows = (await session.execute(stmt)).scalars().all()

            for row in rows:
                row.status = "processing"
                row.attempts += 1

            await session.commit()

            for row in rows:
                await _handle_row(row.id, row.event_id, row.event_type,
                                  row.source, row.payload, row.attempts)

    except Exception as exc:
        log.debug("Worker batch skipped (DB may not be ready): %s", exc)


async def _handle_row(
    row_id: str,
    event_id: str,
    event_type: str,
    source: str,
    payload: dict[str, Any],
    attempt: int,
) -> None:
    """Process one event row — dispatch handler, mark done or dead_letter."""
    from backend.app.db.session import AsyncSessionLocal
    from backend.app.db.models.webhooks import WebhookEvent
    from sqlalchemy import update

    try:
        normalized = normalize(payload, source=source)
        normalized["event_id"] = event_id
        normalized["event_type"] = normalized.get("event_type", event_type)

        # Run handler in a thread pool so sync handlers don't block the loop
        await asyncio.get_event_loop().run_in_executor(
            None, _dispatch_sync, normalized
        )
        status = "done"
        error = None
        log.info("Event %s (%s) processed OK", event_id, event_type)

    except Exception as exc:
        error = str(exc)[:1000]
        status = "dead_letter" if attempt >= _MAX_ATTEMPTS else "pending"
        log.warning("Event %s attempt %d failed: %s", event_id, attempt, exc)

        if status == "dead_letter":
            from backend.app.audit import log_event as audit_log
            audit_log("webhook_dead_letter", {
                "event_id": event_id,
                "event_type": event_type,
                "error": error,
                "attempts": attempt,
            })

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(WebhookEvent)
            .where(WebhookEvent.id == row_id)
            .values(
                status=status,
                error=error,
                processed_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()


def _dispatch_sync(normalized: dict[str, Any]) -> None:
    """Synchronous dispatch — called in executor thread."""
    from backend.app.ingestion.handlers import dispatch
    dispatch(normalized)
