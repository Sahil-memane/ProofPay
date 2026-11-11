"""
Real audit writer.

Every write is immutable:
  - A DB trigger blocks UPDATE/DELETE on audit_log.
  - prev_hash + row_hash form a tamper-evident SHA-256 chain.

The sync `log_event()` helper is designed to be used from anywhere in the
codebase without threading issues, falling back to in-memory if the DB is
not yet available (e.g. during startup migrations).
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.app.core.logging import get_logger

log = get_logger(__name__)

# In-memory fallback (used before DB is ready, and in tests using stubs)
_fallback_events: list[dict[str, Any]] = []
_db_available: bool = False


def _compute_hash(prev_hash: str | None, payload: dict[str, Any]) -> str:
    content = (prev_hash or "") + json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()


def _get_prev_hash(subject: str) -> str | None:
    """Get the hash of the most recent audit row for a subject."""
    try:
        from backend.app.db.session import get_sync_session
        from backend.app.db.models.audit_log import AuditLog
        from sqlalchemy import select, desc

        with get_sync_session() as session:
            stmt = (
                select(AuditLog.row_hash)
                .where(AuditLog.subject == subject)
                .order_by(desc(AuditLog.created_at))
                .limit(1)
            )
            result = session.execute(stmt).scalar_one_or_none()
            return result
    except Exception:
        return None


def write(
    subject: str,
    actor: str,
    event_type: str,
    payload: dict[str, Any],
    search_text: str | None = None,
) -> dict[str, Any]:
    """
    Write an immutable audit row.
    Returns the row dict (regardless of whether it went to DB or fallback).
    """
    prev_hash = _get_prev_hash(subject)
    row_hash = _compute_hash(prev_hash, payload)
    row_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    record: dict[str, Any] = {
        "id": row_id,
        "subject": subject,
        "actor": actor,
        "event_type": event_type,
        "payload": payload,
        "prev_hash": prev_hash,
        "row_hash": row_hash,
        "search_text": search_text or f"{subject} {event_type} {json.dumps(payload, default=str)}",
        "created_at": now.isoformat(),
    }

    _fallback_events.append(record)
    if len(_fallback_events) > 500:
        _fallback_events.pop(0)

    try:
        from backend.app.db.session import get_sync_session
        from backend.app.db.models.audit_log import AuditLog

        with get_sync_session() as session:
            row = AuditLog(
                id=row_id,
                subject=subject,
                actor=actor,
                event_type=event_type,
                payload=payload,
                prev_hash=prev_hash,
                row_hash=row_hash,
                search_text=record["search_text"],
                created_at=now,
            )
            session.add(row)
            session.commit()
    except Exception as exc:
        log.warning("audit.write DB unavailable, using fallback: %s", exc)

    return record


def log_event(event_type: str, payload: dict[str, Any]) -> None:
    """
    Convenience wrapper matching the stub interface.
    Subject defaults to payload["case_id"] or "system".
    """
    subject = str(payload.get("case_id") or payload.get("subject") or "system")
    actor = str(payload.get("actor") or "system")
    write(subject=subject, actor=actor, event_type=event_type, payload=payload)
