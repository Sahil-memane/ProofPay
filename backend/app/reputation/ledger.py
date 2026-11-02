"""
Reputation Ledger.

Tracks positive/negative events affecting customer or freelancer reputation score.
Score starts at 50, clamped between 0 and 100.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from backend.app.db.models.support import ReputationEvent
from backend.app.db.session import get_sync_session

WEIGHTS: dict[str, int] = {
    "on_time_release": 5,
    "on_time_payment": 5,
    "recovered": 3,
    "dispute_lost": -10,
    "missed_deadline": -5,
}

_in_memory_events: dict[str, list[dict[str, Any]]] = {}


def record_event(
    subject: str,
    event_type: str,
    audit_id: str | None = None,
    delta: int | None = None,
) -> int:
    event_delta = delta if delta is not None else WEIGHTS.get(event_type, 0)
    event_id = str(uuid.uuid4())
    record = {
        "id": event_id,
        "subject": subject,
        "event_type": event_type,
        "delta": event_delta,
        "audit_id": audit_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        with get_sync_session() as session:
            db_ev = ReputationEvent(
                id=event_id,
                subject=subject,
                event_type=event_type,
                delta=event_delta,
                audit_id=audit_id,
            )
            session.add(db_ev)
            session.commit()
    except Exception:
        pass

    _in_memory_events.setdefault(subject, []).append(record)
    score_data = get_score(subject)
    return score_data["score"]


def get_score(subject: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []

    try:
        with get_sync_session() as session:
            stmt = select(ReputationEvent).where(ReputationEvent.subject == subject)
            results = session.execute(stmt).scalars().all()
            if results:
                events = [
                    {
                        "id": ev.id,
                        "subject": ev.subject,
                        "event_type": ev.event_type,
                        "delta": ev.delta,
                        "audit_id": ev.audit_id,
                        "created_at": ev.created_at.isoformat() if ev.created_at else None,
                    }
                    for ev in results
                ]
    except Exception:
        pass

    if not events:
        events = _in_memory_events.get(subject, [])

    score = 50
    for ev in events:
        score = max(0, min(100, score + int(ev.get("delta", 0))))

    return {
        "subject": subject,
        "score": score,
        "events": events,
    }


def reset() -> None:
    _in_memory_events.clear()
