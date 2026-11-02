"""
Customer event simulator and event dispatcher.

Handles event definitions, callback delivery (e.g. to /sim/events),
and simulator response models.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.simulator.profiles import CustomerProfile

logger = logging.getLogger(__name__)


# ── Canonical Event Types for Customer Simulator ─────────────────────────────

class SimulatorEventType(str, Enum):
    PAYMENT_SUCCESS = "payment_success"
    FREE_TEXT_REPLY = "free_text_reply"
    DISPUTE = "dispute"
    OPT_OUT = "opt_out"
    NOTHING = "nothing"


# Backward compatibility alias
class EventKind(str, Enum):
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_SUCCESS = "payment_success"
    NO_RESPONSE = "no_response"
    NOTHING = "nothing"
    OPT_OUT = "opt_out"
    BOUNCE = "bounce"
    PARTIAL_PAYMENT = "partial_payment"
    DISPUTE = "dispute"
    PAID_ELSEWHERE = "paid_elsewhere"
    FREE_TEXT_REPLY = "free_text_reply"


@dataclass
class SimulatorEvent:
    """An event emitted by the customer simulator in response to an action."""
    event_type: SimulatorEventType
    customer_id: str
    case_id: str
    timestamp: datetime
    amount: float | None = None
    message: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def kind(self) -> EventKind:
        """Compatibility property mapping SimulatorEventType to EventKind."""
        mapping = {
            SimulatorEventType.PAYMENT_SUCCESS: EventKind.PAYMENT_SUCCESS,
            SimulatorEventType.FREE_TEXT_REPLY: EventKind.FREE_TEXT_REPLY,
            SimulatorEventType.DISPUTE: EventKind.DISPUTE,
            SimulatorEventType.OPT_OUT: EventKind.OPT_OUT,
            SimulatorEventType.NOTHING: EventKind.NOTHING,
        }
        return mapping.get(self.event_type, EventKind.NOTHING)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "customer_id": self.customer_id,
            "case_id": self.case_id,
            "timestamp": self.timestamp.isoformat(),
            "amount": self.amount,
            "message": self.message,
            "meta": self.meta,
        }


# Backward compatibility class
@dataclass
class SimEvent:
    kind: EventKind
    customer_id: str
    case_id: str
    amount: float | None
    timestamp: datetime
    meta: dict[str, Any] = field(default_factory=dict)


# ── Callback Dispatcher ───────────────────────────────────────────────────────

_EVENT_CALLBACKS: list[Callable[[SimulatorEvent], Any]] = []
_CALLBACK_URL: str | None = None


def register_event_callback(fn: Callable[[SimulatorEvent], Any]) -> None:
    """Register an in-process callback function to receive posted events."""
    if fn not in _EVENT_CALLBACKS:
        _EVENT_CALLBACKS.append(fn)


def clear_event_callbacks() -> None:
    """Clear registered in-process callbacks."""
    _EVENT_CALLBACKS.clear()


def set_callback_url(url: str | None) -> None:
    """Configure external HTTP callback URL (e.g. /sim/events)."""
    global _CALLBACK_URL
    _CALLBACK_URL = url


def post_event(
    event: SimulatorEvent,
    callback_url: str | None = None,
    callback_fn: Callable[[SimulatorEvent], Any] | None = None,
) -> bool:
    """
    Post an event to a callback (HTTP endpoint or in-process listeners).
    Returns True if successfully delivered to at least one subscriber or endpoint.
    """
    delivered = False

    # 1. Direct callback function if provided
    if callback_fn:
        try:
            callback_fn(event)
            delivered = True
        except Exception as e:
            logger.warning("Error invoking direct callback_fn: %s", e)

    # 2. Registered in-process callbacks
    for cb in _EVENT_CALLBACKS:
        try:
            cb(event)
            delivered = True
        except Exception as e:
            logger.warning("Error invoking registered callback %s: %s", cb, e)

    # 3. HTTP callback URL if specified
    target_url = callback_url or _CALLBACK_URL
    if target_url:
        try:
            import httpx
            with httpx.Client(timeout=2.0) as client:
                resp = client.post(target_url, json=event.to_dict())
                delivered = resp.is_success or delivered
        except Exception as e:
            logger.info("HTTP callback to %s failed (endpoint may be offline): %s", target_url, e)

    return delivered


# ── Quiet Hours and Legacy Simulators (Preserved for compatibility) ───────────

def _local_hour(utc_time: datetime, utc_offset_hours: float) -> float:
    """Return local hour (0-23.99) for a UTC time given an offset."""
    return (utc_time.hour + utc_offset_hours) % 24


def is_quiet_hours(utc_time: datetime, timezone_name: str) -> bool:
    """Return True if local time is in quiet window (21:00–08:00)."""
    from backend.app.simulator.profiles import get_utc_offset
    offset = get_utc_offset(timezone_name)
    local_h = _local_hour(utc_time, offset)
    return local_h >= 21.0 or local_h < 8.0


def simulate_response(
    profile: CustomerProfile,
    case_id: str,
    amount_owed: float,
    contact_time: datetime,
    rng: Any | None = None,
) -> SimEvent:
    """Legacy helper for backward compatibility."""
    import random
    rng = rng or random.Random()

    if profile.opted_out:
        return SimEvent(
            kind=EventKind.OPT_OUT,
            customer_id=profile.customer_id,
            case_id=case_id,
            amount=None,
            timestamp=contact_time + timedelta(minutes=1),
        )

    roll = rng.random()

    if roll < profile.payment_reliability:
        delay_h = rng.uniform(1.0, profile.avg_payment_delay_hours)
        paid_amount = amount_owed if rng.random() > 0.1 else round(amount_owed * rng.uniform(0.3, 0.9), 2)
        kind = EventKind.PAYMENT_RECEIVED if paid_amount >= amount_owed * 0.99 else EventKind.PARTIAL_PAYMENT
        return SimEvent(
            kind=kind,
            customer_id=profile.customer_id,
            case_id=case_id,
            amount=paid_amount,
            timestamp=contact_time + timedelta(hours=delay_h),
            meta={"full": kind == EventKind.PAYMENT_RECEIVED},
        )
    elif roll < profile.payment_reliability + 0.05:
        return SimEvent(
            kind=EventKind.PAID_ELSEWHERE,
            customer_id=profile.customer_id,
            case_id=case_id,
            amount=amount_owed,
            timestamp=contact_time + timedelta(hours=rng.uniform(2, 24)),
        )
    elif roll < profile.payment_reliability + 0.08:
        return SimEvent(
            kind=EventKind.BOUNCE,
            customer_id=profile.customer_id,
            case_id=case_id,
            amount=None,
            timestamp=contact_time + timedelta(minutes=5),
        )
    else:
        return SimEvent(
            kind=EventKind.NO_RESPONSE,
            customer_id=profile.customer_id,
            case_id=case_id,
            amount=None,
            timestamp=contact_time + timedelta(hours=rng.uniform(24, 72)),
        )
