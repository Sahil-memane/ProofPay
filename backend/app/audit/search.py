"""
Audit search and retrieval.

Full-text search uses Postgres tsvector GIN index.
Falls back to in-memory events from writer._fallback_events when DB is unavailable.
"""
from __future__ import annotations

from typing import Any

from backend.app.core.logging import get_logger

log = get_logger(__name__)


def get_events(case_id: str | None = None) -> list[dict[str, Any]]:
    """
    Return audit events. Filters by case_id in payload if provided.
    Merges DB rows with any fallback in-memory events.
    """
    from backend.app.audit.writer import _fallback_events

    results: list[dict[str, Any]] = []

    try:
        from backend.app.db.session import get_sync_session
        from backend.app.db.models.audit_log import AuditLog
        from sqlalchemy import select, desc

        with get_sync_session() as session:
            stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(500)
            rows = session.execute(stmt).scalars().all()
        for r in rows:
            entry = {
                "id": r.id,
                "subject": r.subject,
                "actor": r.actor,
                "event_type": r.event_type,
                "payload": r.payload,
                "row_hash": r.row_hash,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            if isinstance(r.payload, dict):
                entry.update(r.payload)
            results.append(entry)
    except Exception:
        results = []
        for e in _fallback_events:
            entry = dict(e)
            if isinstance(e.get("payload"), dict):
                entry.update(e["payload"])
            results.append(entry)

    if case_id:
        results = [
            e for e in results
            if str(e.get("case_id", "")) == str(case_id)
            or str(e.get("subject", "")) == str(case_id)
        ]

    return results


def search(query: str, subject: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Full-text search over audit_log using Postgres tsvector."""
    try:
        from backend.app.db.session import get_sync_session
        from backend.app.db.models.audit_log import AuditLog
        from sqlalchemy import select, desc, text

        with get_sync_session() as session:
            fts_expr = text(
                "to_tsvector('english', COALESCE(search_text, '')) @@ plainto_tsquery('english', :q)"
            )
            stmt = (
                select(AuditLog)
                .where(fts_expr.bindparams(q=query))
                .order_by(desc(AuditLog.created_at))
                .limit(limit)
            )
            if subject:
                stmt = stmt.where(AuditLog.subject == subject)

            rows = session.execute(stmt).scalars().all()
            return [
                {
                    "id": r.id,
                    "subject": r.subject,
                    "actor": r.actor,
                    "event_type": r.event_type,
                    "payload": r.payload,
                    "row_hash": r.row_hash,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
    except Exception as exc:
        log.warning("audit.search failed: %s", exc)
        return []


def clear() -> None:
    """Clear in-memory fallback events (for test isolation only)."""
    from backend.app.audit.writer import _fallback_events
    _fallback_events.clear()
