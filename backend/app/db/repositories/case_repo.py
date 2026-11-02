"""
Case repository — provides database access for Recovery cases with in-memory fallback.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.app.contracts.enums import CaseState
from backend.app.core.clock import clock
from backend.app.db.models.cases import Case
from backend.app.db.session import AsyncSessionLocal, get_sync_session

# In-memory store for test suite and when DB is offline
_in_memory_cases: dict[str, dict[str, Any]] = {}


class CaseRepo:
    """Repository handling Case persistence."""

    def __init__(self, session: Session | AsyncSession | None = None) -> None:
        self._session = session
        self._store = _in_memory_cases

    def create(
        self,
        customer_id: str,
        amount_usd: float,
        currency: str = "USD",
        payload: dict[str, Any] | None = None,
        type: str = "failed_payment",
    ) -> dict[str, Any]:
        case_id = str(uuid.uuid4())
        created_at_dt = clock.utcnow()
        case_data = {
            "id": case_id,
            "customer_id": customer_id,
            "type": type,
            "amount_usd": float(amount_usd),
            "currency": currency,
            "state": CaseState.OPEN.value if hasattr(CaseState.OPEN, "value") else str(CaseState.OPEN),
            "payload": payload or {},
            "contact_count": 0,
            "last_contact_at": None,
            "priority_score": None,
            "unrecovered_reason": None,
            "history": [],
            "diagnosis": None,
            "created_at": created_at_dt.isoformat() if hasattr(created_at_dt, "isoformat") else str(created_at_dt),
        }

        # Attempt DB insert if sync session available
        try:
            with get_sync_session() as session:
                db_case = Case(
                    id=case_id,
                    customer_id=customer_id,
                    type=type,
                    amount_usd=float(amount_usd),
                    currency=currency,
                    state=CaseState.OPEN.value if hasattr(CaseState.OPEN, "value") else str(CaseState.OPEN),
                    payload=payload or {},
                    contact_count=0,
                    history=[],
                )
                session.add(db_case)
                session.commit()
        except Exception:
            pass

        _in_memory_cases[case_id] = case_data
        return case_data

    def get(self, case_id: str) -> dict[str, Any] | None:
        try:
            with get_sync_session() as session:
                stmt = select(Case).where(Case.id == case_id)
                db_case = session.execute(stmt).scalar_one_or_none()
                if db_case:
                    return {
                        "id": db_case.id,
                        "customer_id": db_case.customer_id,
                        "type": db_case.type,
                        "state": db_case.state,
                        "amount_usd": db_case.amount_usd,
                        "currency": db_case.currency,
                        "payload": db_case.payload or {},
                        "contact_count": db_case.contact_count,
                        "last_contact_at": db_case.last_contact_at.isoformat() if db_case.last_contact_at else None,
                        "priority_score": db_case.priority_score,
                        "unrecovered_reason": db_case.unrecovered_reason,
                        "history": db_case.history or [],
                        "diagnosis": db_case.diagnosis,
                        "created_at": db_case.created_at.isoformat() if db_case.created_at else None,
                    }
        except Exception:
            pass
        return _in_memory_cases.get(case_id)

    def update(self, case_id: str, **fields: Any) -> dict[str, Any]:
        try:
            with get_sync_session() as session:
                stmt = select(Case).where(Case.id == case_id)
                db_case = session.execute(stmt).scalar_one_or_none()
                if db_case:
                    for k, v in fields.items():
                        if hasattr(db_case, k):
                            setattr(db_case, k, v)
                    session.commit()
        except Exception:
            pass

        if case_id in _in_memory_cases:
            _in_memory_cases[case_id].update(fields)
            return _in_memory_cases[case_id]
        if fields:
            _in_memory_cases[case_id] = {"id": case_id, **fields}
            return _in_memory_cases[case_id]
        raise KeyError(f"Case {case_id} not found")

    def list_all(self, status: str | None = None) -> list[dict[str, Any]]:
        try:
            with get_sync_session() as session:
                stmt = select(Case)
                if status:
                    stmt = stmt.where(Case.state == status)
                results = session.execute(stmt).scalars().all()
                if results:
                    return [
                        {
                            "id": c.id,
                            "customer_id": c.customer_id,
                            "type": c.type,
                            "state": c.state,
                            "amount_usd": c.amount_usd,
                            "currency": c.currency,
                            "payload": c.payload or {},
                            "contact_count": c.contact_count,
                            "last_contact_at": c.last_contact_at.isoformat() if c.last_contact_at else None,
                            "priority_score": c.priority_score,
                            "unrecovered_reason": c.unrecovered_reason,
                            "history": c.history or [],
                            "diagnosis": c.diagnosis,
                            "created_at": c.created_at.isoformat() if c.created_at else None,
                        }
                        for c in results
                    ]
        except Exception:
            pass

        cases = list(_in_memory_cases.values())
        if status:
            cases = [c for c in cases if c.get("state") == status]
        return cases

    def reset(self) -> None:
        _in_memory_cases.clear()


# Default singleton
case_repo = CaseRepo()
