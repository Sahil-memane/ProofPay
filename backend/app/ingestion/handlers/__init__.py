"""
Webhook event handlers.

Each handler receives the normalised event dict and a sync DB session.
Handlers are dispatched by event_type from the worker loop.

Handlers must be idempotent — the worker guarantees at-least-once delivery.
"""
from __future__ import annotations

from typing import Any, Callable

from backend.app.core.logging import get_logger

log = get_logger(__name__)

# Registry: internal event_type → handler function
_REGISTRY: dict[str, Callable[[dict[str, Any]], None]] = {}


def register(event_type: str) -> Callable:
    """Decorator to register a handler for a given internal event type."""
    def decorator(fn: Callable) -> Callable:
        _REGISTRY[event_type] = fn
        return fn
    return decorator


def dispatch(event: dict[str, Any]) -> None:
    """Dispatch a normalised event to its registered handler (if any)."""
    event_type = event.get("event_type", "unknown")
    handler = _REGISTRY.get(event_type)
    if handler:
        log.info("Dispatching event: %s (id=%s)", event_type, event.get("event_id"))
        handler(event)
    else:
        log.info("No handler registered for event_type=%s — skipping", event_type)


# ── Import handlers to trigger @register decorators ───────────────────────────
# This must stay at the bottom to avoid circular imports.
from backend.app.ingestion.handlers import (  # noqa: E402, F401
    capture_completed,
    capture_denied,
    invoice_events,
    payout_events,
    subscription_failed,
)
