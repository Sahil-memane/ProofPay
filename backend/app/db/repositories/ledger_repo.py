"""
Ledger repository — provides append-only financial ledger operations.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models.projects import LedgerEntry
from backend.app.db.session import get_sync_session

_in_memory_ledger: list[dict[str, Any]] = []


class LedgerRepo:
    def __init__(self, session: Session | None = None) -> None:
        self._session = session
        self._store = _in_memory_ledger

    def record_entry(
        self,
        entry_type: str,
        subject_id: str,
        amount: float,
        currency: str = "USD",
        paypal_id: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        entry_id = str(uuid.uuid4())
        record = {
            "id": entry_id,
            "type": entry_type,
            "subject_id": subject_id,
            "amount": float(amount),
            "currency": currency,
            "paypal_id": paypal_id,
            "note": note,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            with get_sync_session() as session:
                db_e = LedgerEntry(
                    id=entry_id,
                    type=entry_type,
                    subject_id=subject_id,
                    amount=float(amount),
                    currency=currency,
                    paypal_id=paypal_id,
                    note=note,
                )
                session.add(db_e)
                session.commit()
        except Exception:
            pass

        _in_memory_ledger.append(record)
        return record

    def list_for_subject(self, subject_id: str) -> list[dict[str, Any]]:
        try:
            with get_sync_session() as session:
                stmt = select(LedgerEntry).where(LedgerEntry.subject_id == subject_id)
                results = session.execute(stmt).scalars().all()
                if results:
                    return [
                        {
                            "id": e.id,
                            "type": e.type,
                            "subject_id": e.subject_id,
                            "amount": e.amount,
                            "currency": e.currency,
                            "paypal_id": e.paypal_id,
                            "note": e.note,
                            "created_at": e.created_at.isoformat() if e.created_at else None,
                        }
                        for e in results
                    ]
        except Exception:
            pass
        return [e for e in _in_memory_ledger if e["subject_id"] == subject_id]

    def get_balance(self, subject_id: str) -> float:
        entries = self.list_for_subject(subject_id)
        balance = 0.0
        for e in entries:
            t = e["type"].upper()
            amt = float(e["amount"])
            if t in ("FUNDING", "HOLD"):
                balance += amt
            elif t in ("RELEASE", "REFUND"):
                balance -= amt
        return round(balance, 2)

    def reset(self) -> None:
        _in_memory_ledger.clear()


ledger_repo = LedgerRepo()
