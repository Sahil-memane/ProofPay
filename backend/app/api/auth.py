from __future__ import annotations

import hashlib
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from backend.app.db.session import get_sync_session
from backend.app.db.models.users import User

router = APIRouter(prefix="/auth", tags=["auth"])

MOCK_USERS = {
    # Originals
    "client@example.com":      {"name": "Acme Global Solutions", "role": "client"},
    "freelancer@example.com":  {"name": "Rahul Sharma",          "role": "freelancer"},
    "merchant@example.com":    {"name": "Sahil",                 "role": "merchant"},
    "admin@example.com":       {"name": "Risk Officer",          "role": "admin"},
    # Additional users
    "client2@example.com":     {"name": "Nexus Corp",            "role": "client"},
    "client3@example.com":     {"name": "Global Trade Ltd",      "role": "client"},
    "freelancer2@example.com": {"name": "Sarah Jenkins",         "role": "freelancer"},
    "freelancer3@example.com": {"name": "David Chen",            "role": "freelancer"},
    "merchant2@example.com":   {"name": "TechBazaar",            "role": "merchant"},
    "merchant3@example.com":   {"name": "MegaShop",              "role": "merchant"},
    "risk@example.com":        {"name": "Risk Officer 2",        "role": "admin"},
}

_registered_users: dict[str, dict] = {}


def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


class LoginRequest(BaseModel):
    email: str
    password: str
    remember: Optional[bool] = True


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    confirm_password: Optional[str] = None
    role: str = "client"
    invite_code: Optional[str] = None


@router.post("/login")
async def login(req: LoginRequest) -> dict:
    email = req.email.lower()
    hashed = _hash_pw(req.password)

    # 1. Try querying PostgreSQL users table
    db_user: User | None = None
    try:
        with get_sync_session() as session:
            db_user = session.execute(
                select(User).where(User.email == email)
            ).scalar_one_or_none()
    except Exception:
        db_user = None

    if db_user:
        # Check password hash or demo override
        if db_user.password_hash and db_user.password_hash != hashed and req.password != "ProofPay@2026":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email or password is incorrect. Check both and try again.",
            )
        return {
            "access_token": f"mock-token-{email}",
            "token_type": "bearer",
            "role": db_user.role,
            "user": {
                "id": db_user.id,
                "email": db_user.email,
                "name": db_user.name,
                "role": db_user.role,
                "customer_id": db_user.customer_id,
            },
        }

    # 2. Fallback to mock / memory users
    user_info = MOCK_USERS.get(email) or _registered_users.get(email)
    if not user_info:
        if req.password == "ProofPay@2026":
            name = email.split("@")[0].title()
            return {
                "access_token": f"mock-token-{email}",
                "token_type": "bearer",
                "role": "client",
                "user": {"email": email, "name": name, "role": "client", "customer_id": None},
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect. Check both and try again.",
        )

    return {
        "access_token": f"mock-token-{email}",
        "token_type": "bearer",
        "role": user_info["role"],
        "user": {
            "email": email,
            "name": user_info["name"],
            "role": user_info["role"],
            "customer_id": user_info.get("customer_id"),
        },
    }


@router.post("/register")
async def register(req: RegisterRequest) -> dict:
    email = req.email.lower()

    if req.role == "admin" and not req.invite_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin invitation code is required for admin accounts.",
        )

    # Check Postgres DB
    try:
        with get_sync_session() as session:
            existing = session.execute(
                select(User).where(User.email == email)
            ).scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An account with this email already exists. Sign in instead.",
                )

            # Insert into Postgres users table
            new_user = User(
                email=email,
                name=req.name,
                role=req.role,
                password_hash=_hash_pw(req.password),
                is_active=True,
            )
            session.add(new_user)
            session.commit()
            user_id = new_user.id
    except HTTPException:
        raise
    except Exception:
        # Fallback to in-memory registration if DB is offline
        if email in MOCK_USERS or email in _registered_users:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists. Sign in instead.",
            )
        user_id = f"mem-{email}"

    user = {
        "id": user_id,
        "email": email,
        "name": req.name,
        "role": req.role,
    }
    _registered_users[email] = user

    return {
        "access_token": f"mock-token-{email}",
        "token_type": "bearer",
        "role": req.role,
        "user": user,
    }


@router.get("/users")
async def list_users() -> list[dict]:
    """Admin/Dev endpoint to list registered users from database."""
    try:
        with get_sync_session() as session:
            users = session.execute(select(User)).scalars().all()
            if users:
                return [
                    {
                        "id": u.id,
                        "email": u.email,
                        "name": u.name,
                        "role": u.role,
                        "customer_id": u.customer_id,
                        "is_active": u.is_active,
                        "created_at": u.created_at.isoformat() if u.created_at else None,
                    }
                    for u in users
                ]
    except Exception:
        pass

    return [
        {"email": k, "name": v["name"], "role": v["role"], "is_active": True}
        for k, v in MOCK_USERS.items()
    ]
