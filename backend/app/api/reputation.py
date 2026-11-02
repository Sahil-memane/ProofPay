"""
Reputation API Router.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.app.reputation.ledger import get_score

router = APIRouter(tags=["reputation"])


@router.get("/reputation/{subject}")
def get_reputation(subject: str) -> dict[str, Any]:
    """Return current reputation score and contributing event history."""
    return get_score(subject)
