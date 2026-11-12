"""
Settings & Policy Config API — serves workspace settings and policy rules.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlalchemy import select

from backend.app.db.models.support import PolicyConfig
from backend.app.db.models.users import User
from backend.app.db.session import get_sync_session

router = APIRouter(tags=["settings"])


@router.get("/settings/policy")
def get_policy_config() -> list[dict[str, Any]]:
    """Return all policy configuration values from DB."""
    try:
        with get_sync_session() as session:
            stmt = select(PolicyConfig).order_by(PolicyConfig.key)
            results = session.execute(stmt).scalars().all()
            return [
                {
                    "key": r.key,
                    "value": r.value,
                    "description": r.description,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in results
            ]
    except Exception:
        return []


@router.get("/settings/users")
def list_workspace_users() -> list[dict[str, Any]]:
    """Return all registered users for workspace team view."""
    try:
        with get_sync_session() as session:
            stmt = select(User).where(User.is_active == True).order_by(User.created_at)
            results = session.execute(stmt).scalars().all()
            return [
                {
                    "id": str(u.id),
                    "name": u.name,
                    "email": u.email,
                    "role": u.role,
                    "is_active": u.is_active,
                }
                for u in results
            ]
    except Exception:
        return []

