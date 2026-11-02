"""Webhook events and executor actions models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, UUIDPrimaryKey


class WebhookEvent(UUIDPrimaryKey, Base):
    """
    Stores every inbound webhook.
    event_id is UNIQUE — duplicate deliveries are silently ignored
    via ON CONFLICT DO NOTHING in the ingestion receiver.
    """

    __tablename__ = "webhook_events"

    # PayPal's own event ID (used for dedup)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    # "paypal" | "sim" | "internal"
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="paypal")
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # pending | processing | done | dead_letter
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExecutorAction(UUIDPrimaryKey, Base):
    """
    Records every executor invocation for idempotency.
    idempotency_key is UNIQUE — same key twice returns the stored receipt.
    """

    __tablename__ = "executor_actions"

    idempotency_key: Mapped[str] = mapped_column(
        String(256), nullable=False, unique=True, index=True
    )
    proposal: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    decision: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # pending | done | ACTION_FAILED
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
