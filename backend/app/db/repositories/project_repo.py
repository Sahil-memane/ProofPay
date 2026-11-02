"""
Project repository — provides database access for Escrow projects with in-memory fallback.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.contracts.enums import ProjectState
from backend.app.db.models.projects import Project
from backend.app.db.session import get_sync_session

_in_memory_projects: dict[str, dict[str, Any]] = {}


class ProjectRepo:
    def __init__(self, session: Session | None = None) -> None:
        self._session = session
        self._store = _in_memory_projects

    def create(
        self,
        job_description: str,
        total_amount: float,
        currency: str = "USD",
        client_id: str | None = None,
        freelancer_id: str | None = None,
        deadline: Any | None = None,
    ) -> dict[str, Any]:
        project_id = str(uuid.uuid4())
        record = {
            "id": project_id,
            "job_description": job_description,
            "total_amount": float(total_amount),
            "currency": currency,
            "state": ProjectState.DRAFT.value,
            "plan_hash": None,
            "client_id": client_id or "client-1",
            "freelancer_id": freelancer_id or "freelancer-1",
            "client_approved": False,
            "freelancer_approved": False,
            "paypal_order_id": None,
            "paypal_capture_id": None,
            "deadline": str(deadline) if deadline else None,
        }

        try:
            with get_sync_session() as session:
                db_p = Project(
                    id=project_id,
                    job_description=job_description,
                    total_amount=float(total_amount),
                    currency=currency,
                    state=ProjectState.DRAFT.value,
                    client_id=client_id or "client-1",
                    freelancer_id=freelancer_id or "freelancer-1",
                )
                session.add(db_p)
                session.commit()
        except Exception:
            pass

        _in_memory_projects[project_id] = record
        return record

    def get(self, project_id: str) -> dict[str, Any] | None:
        try:
            with get_sync_session() as session:
                stmt = select(Project).where(Project.id == project_id)
                db_p = session.execute(stmt).scalar_one_or_none()
                if db_p:
                    return {
                        "id": db_p.id,
                        "job_description": db_p.job_description,
                        "total_amount": db_p.total_amount,
                        "currency": db_p.currency,
                        "state": db_p.state,
                        "plan_hash": db_p.plan_hash,
                        "client_id": db_p.client_id,
                        "freelancer_id": db_p.freelancer_id,
                        "client_approved": db_p.client_approved,
                        "freelancer_approved": db_p.freelancer_approved,
                        "paypal_order_id": db_p.paypal_order_id,
                        "paypal_capture_id": db_p.paypal_capture_id,
                        "deadline": db_p.deadline.isoformat() if db_p.deadline else None,
                    }
        except Exception:
            pass
        return _in_memory_projects.get(project_id)

    def update(self, project_id: str, **fields: Any) -> dict[str, Any]:
        try:
            with get_sync_session() as session:
                stmt = select(Project).where(Project.id == project_id)
                db_p = session.execute(stmt).scalar_one_or_none()
                if db_p:
                    for k, v in fields.items():
                        if hasattr(db_p, k):
                            setattr(db_p, k, v)
                    session.commit()
        except Exception:
            pass

        if project_id in _in_memory_projects:
            _in_memory_projects[project_id].update(fields)
            return _in_memory_projects[project_id]
        if fields:
            _in_memory_projects[project_id] = {"id": project_id, **fields}
            return _in_memory_projects[project_id]
        raise KeyError(f"Project {project_id} not found")

    def list_all(self) -> list[dict[str, Any]]:
        try:
            with get_sync_session() as session:
                stmt = select(Project)
                results = session.execute(stmt).scalars().all()
                if results:
                    return [
                        {
                            "id": p.id,
                            "job_description": p.job_description,
                            "total_amount": p.total_amount,
                            "currency": p.currency,
                            "state": p.state,
                            "plan_hash": p.plan_hash,
                            "client_id": p.client_id,
                            "freelancer_id": p.freelancer_id,
                            "client_approved": p.client_approved,
                            "freelancer_approved": p.freelancer_approved,
                            "paypal_order_id": p.paypal_order_id,
                            "paypal_capture_id": p.paypal_capture_id,
                            "deadline": p.deadline.isoformat() if p.deadline else None,
                        }
                        for p in results
                    ]
        except Exception:
            pass
        return list(_in_memory_projects.values())

    def reset(self) -> None:
        _in_memory_projects.clear()


project_repo = ProjectRepo()
