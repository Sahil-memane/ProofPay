"""
Auth dependency for user-scoped data access.

Parses the Authorization: Bearer mock-token-{email} header,
looks up the user in the DB (or falls back to known admins),
and returns a dict with {id, email, role, customer_id}.

Rules:
  - admin/risk_officer → customer_id=None → sees ALL data
  - client/freelancer  → customer_id=CUST-XXXXX → sees only their projects/milestones
  - merchant           → customer_id=CUST-XXXXX → sees only their invoices/sales/cases
"""
from __future__ import annotations

from fastapi import Header, HTTPException, status

from sqlalchemy import select
from backend.app.db.session import get_sync_session
from backend.app.db.models.users import User

# Fallback mapping for when DB is unreachable or token belongs to unknown user.
# Maps email → (role, customer_id)
_FALLBACK_USERS: dict[str, tuple[str, str | None]] = {
    "admin@example.com":       ("admin",      None),
    "risk@example.com":        ("admin",      None),
    "client@example.com":      ("client",     "CUST-00010"),
    "client2@example.com":     ("client",     "CUST-00068"),
    "client3@example.com":     ("client",     "CUST-00089"),
    "freelancer@example.com":  ("freelancer", "CUST-00081"),
    "freelancer2@example.com": ("freelancer", "CUST-00041"),
    "freelancer3@example.com": ("freelancer", "CUST-00005"),
    "merchant@example.com":    ("merchant",   "CUST-00002"),
    "merchant2@example.com":   ("merchant",   "CUST-00003"),
    "merchant3@example.com":   ("merchant",   "CUST-00004"),
}


def get_current_user(authorization: str = Header(default="")) -> dict:
    """
    Extract user from Authorization: Bearer mock-token-{email} header.
    Returns a dict with keys: email, role, customer_id.
    If no / invalid header, returns a default guest-admin view to avoid
    breaking the existing anonymous frontend usage.
    """
    token = ""
    if authorization.startswith("Bearer "):
        token = authorization[len("Bearer "):]

    # Parse email from token
    email: str | None = None
    if token.startswith("mock-token-"):
        email = token[len("mock-token-"):]

    if not email:
        # No auth header sent — treat as anonymous admin so existing
        # pages that don't yet send headers don't break.
        return {"email": None, "role": "admin", "customer_id": None}

    # 1. Try DB lookup
    try:
        with get_sync_session() as session:
            db_user = session.execute(
                select(User).where(User.email == email)
            ).scalar_one_or_none()
        if db_user:
            return {
                "id": db_user.id,
                "email": db_user.email,
                "role": db_user.role,
                "customer_id": db_user.customer_id,
            }
    except Exception:
        pass

    # 2. Fallback to static map
    if email in _FALLBACK_USERS:
        role, customer_id = _FALLBACK_USERS[email]
        return {"email": email, "role": role, "customer_id": customer_id}

    # 3. Unknown user — treat as restricted client with no visible data
    return {"email": email, "role": "client", "customer_id": None}


def is_admin(user: dict) -> bool:
    return user.get("role") in ("admin", "risk_officer")

