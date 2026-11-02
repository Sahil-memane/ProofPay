# TEMP: replaced by db/
"""Stub in-memory repositories for cases, transactions, and contacts."""
from __future__ import annotations
from typing import Any
from datetime import datetime, timezone
import uuid

from backend.app.stubs.contracts_stub import CaseState
from backend.app.stubs.clock import clock


class CaseRepo:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def create(self, customer_id: str, amount_usd: float, currency: str = "USD") -> dict[str, Any]:
        case_id = str(uuid.uuid4())
        case = {
            "id": case_id,
            "customer_id": customer_id,
            "amount_usd": amount_usd,
            "currency": currency,
            "state": CaseState.OPEN,
            "contact_count": 0,
            "last_contact_at": None,
            "created_at": clock.utcnow().isoformat(),
            "history": [],
        }
        self._store[case_id] = case
        return case

    def get(self, case_id: str) -> dict[str, Any] | None:
        return self._store.get(case_id)

    def update(self, case_id: str, **fields: Any) -> dict[str, Any]:
        if case_id not in self._store:
            raise KeyError(f"Case {case_id} not found")
        self._store[case_id].update(fields)
        return self._store[case_id]

    def list_all(self) -> list[dict[str, Any]]:
        return list(self._store.values())

    def reset(self) -> None:
        self._store.clear()


class ContactRepo:
    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, Any]]] = {}  # case_id → contacts

    def add(self, case_id: str, channel: str, sent_at: datetime | None = None) -> dict[str, Any]:
        record = {
            "case_id": case_id,
            "channel": channel,
            "sent_at": (sent_at or clock.utcnow()).isoformat(),
        }
        self._store.setdefault(case_id, []).append(record)
        return record

    def list_for_case(self, case_id: str) -> list[dict[str, Any]]:
        return list(self._store.get(case_id, []))

    def reset(self) -> None:
        self._store.clear()


# Module-level singletons
case_repo = CaseRepo()
contact_repo = ContactRepo()
