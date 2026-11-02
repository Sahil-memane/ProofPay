"""
Contact repository — provides persistence for customer contacts.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.clock import clock
from backend.app.db.models.cases import Contact
from backend.app.db.session import get_sync_session

_in_memory_contacts: dict[str, list[dict[str, Any]]] = {}


class ContactRepo:
    def __init__(self, session: Session | None = None) -> None:
        self._session = session
        self._store = _in_memory_contacts

    def add(
        self,
        case_id: str,
        channel: str,
        sent_at: datetime | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        dt = sent_at or clock.utcnow()
        record = {
            "id": str(uuid.uuid4()),
            "case_id": case_id,
            "channel": channel,
            "sent_at": dt.isoformat() if hasattr(dt, "isoformat") else str(dt),
            "idempotency_key": idempotency_key,
        }

        try:
            with get_sync_session() as session:
                db_contact = Contact(
                    id=record["id"],
                    case_id=case_id,
                    channel=channel,
                    sent_at=dt if isinstance(dt, datetime) else datetime.now(timezone.utc),
                    idempotency_key=idempotency_key,
                )
                session.add(db_contact)
                session.commit()
        except Exception:
            pass

        _in_memory_contacts.setdefault(case_id, []).append(record)
        return record

    def list_for_case(self, case_id: str) -> list[dict[str, Any]]:
        try:
            with get_sync_session() as session:
                stmt = select(Contact).where(Contact.case_id == case_id)
                results = session.execute(stmt).scalars().all()
                if results:
                    return [
                        {
                            "id": c.id,
                            "case_id": c.case_id,
                            "channel": c.channel,
                            "sent_at": c.sent_at.isoformat() if c.sent_at else None,
                            "idempotency_key": c.idempotency_key,
                        }
                        for c in results
                    ]
        except Exception:
            pass
        return list(_in_memory_contacts.get(case_id, []))

    def reset(self) -> None:
        _in_memory_contacts.clear()


# Default singleton
contact_repo = ContactRepo()
