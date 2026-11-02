"""Append-only audit log model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, UUIDPrimaryKey


class AuditLog(UUIDPrimaryKey, Base):
    """
    Insert-only audit log with a SHA-256 tamper-evident hash chain.
    No updated_at — this row must never be changed after insert.
    A DB trigger (added in migration) blocks UPDATE and DELETE.
    """

    __tablename__ = "audit_log"

    # What entity does this row describe?
    subject: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    # Who performed the action: agent | policy | executor | human | system | webhook
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Full structured payload
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Hash chain
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    # Full-text search vector (populated by DB trigger / updated in writer)
    search_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
