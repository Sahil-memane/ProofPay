"""
Audit repository — provides access to AuditLog rows.
"""
from __future__ import annotations

from typing import Any

from backend.app.audit.search import get_events, search
from backend.app.audit.writer import log_event, write


class AuditRepo:
    def write(
        self,
        subject: str,
        actor: str,
        event_type: str,
        payload: dict[str, Any],
        search_text: str | None = None,
    ) -> dict[str, Any]:
        return write(subject, actor, event_type, payload, search_text)

    def search(self, query: str, subject: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        return search(query, subject, limit)

    def get_for_subject(self, subject: str) -> list[dict[str, Any]]:
        return get_events(subject)

    def log(self, event_type: str, payload: dict[str, Any]) -> None:
        log_event(event_type, payload)


audit_repo = AuditRepo()
