"""
Milestone repository — provides database access for project milestones.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.contracts.enums import MilestoneState
from backend.app.db.models.projects import Milestone
from backend.app.db.session import get_sync_session

_in_memory_milestones: dict[str, list[dict[str, Any]]] = {}


class MilestoneRepo:
    def __init__(self, session: Session | None = None) -> None:
        self._session = session
        self._store = _in_memory_milestones

    def create(
        self,
        project_id: str,
        title: str,
        amount: float,
        currency: str = "USD",
        criteria: list[dict[str, Any]] | None = None,
        deadline: Any | None = None,
        sequence: int = 0,
    ) -> dict[str, Any]:
        milestone_id = str(uuid.uuid4())
        record = {
            "id": milestone_id,
            "project_id": project_id,
            "title": title,
            "amount": float(amount),
            "currency": currency,
            "state": MilestoneState.DRAFT.value,
            "criteria": criteria or [],
            "deadline": str(deadline) if deadline else None,
            "sequence": sequence,
            "submission_count": 0,
            "max_submissions": 3,
        }

        try:
            with get_sync_session() as session:
                db_m = Milestone(
                    id=milestone_id,
                    project_id=project_id,
                    title=title,
                    amount=float(amount),
                    currency=currency,
                    state=MilestoneState.DRAFT.value,
                    criteria=criteria or [],
                    sequence=sequence,
                )
                session.add(db_m)
                session.commit()
        except Exception:
            pass

        _in_memory_milestones.setdefault(project_id, []).append(record)
        return record

    def list_for_project(self, project_id: str) -> list[dict[str, Any]]:
        try:
            with get_sync_session() as session:
                stmt = select(Milestone).where(Milestone.project_id == project_id).order_by(Milestone.sequence)
                results = session.execute(stmt).scalars().all()
                if results:
                    return [
                        {
                            "id": m.id,
                            "project_id": m.project_id,
                            "title": m.title,
                            "amount": m.amount,
                            "currency": m.currency,
                            "state": m.state,
                            "criteria": m.criteria or [],
                            "deadline": m.deadline.isoformat() if m.deadline else None,
                            "sequence": m.sequence,
                            "submission_count": m.submission_count,
                            "max_submissions": m.max_submissions,
                        }
                        for m in results
                    ]
        except Exception:
            pass
        return list(_in_memory_milestones.get(project_id, []))

    def get(self, milestone_id: str) -> dict[str, Any] | None:
        try:
            with get_sync_session() as session:
                stmt = select(Milestone).where(Milestone.id == milestone_id)
                m = session.execute(stmt).scalar_one_or_none()
                if m:
                    return {
                        "id": m.id,
                        "project_id": m.project_id,
                        "title": m.title,
                        "amount": m.amount,
                        "currency": m.currency,
                        "state": m.state,
                        "criteria": m.criteria or [],
                        "deadline": m.deadline.isoformat() if m.deadline else None,
                        "sequence": m.sequence,
                        "submission_count": m.submission_count,
                        "max_submissions": m.max_submissions,
                    }
        except Exception:
            pass

        for p_id, ms in _in_memory_milestones.items():
            for m in ms:
                if m["id"] == milestone_id:
                    return m
        return None

    def update(self, milestone_id: str, **fields: Any) -> dict[str, Any]:
        try:
            with get_sync_session() as session:
                stmt = select(Milestone).where(Milestone.id == milestone_id)
                m = session.execute(stmt).scalar_one_or_none()
                if m:
                    for k, v in fields.items():
                        if hasattr(m, k):
                            setattr(m, k, v)
                    session.commit()
        except Exception:
            pass

        for p_id, ms in _in_memory_milestones.items():
            for m in ms:
                if m["id"] == milestone_id:
                    m.update(fields)
                    return m
        raise KeyError(f"Milestone {milestone_id} not found")

    def reset(self) -> None:
        _in_memory_milestones.clear()


milestone_repo = MilestoneRepo()
