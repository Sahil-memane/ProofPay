"""Recovery case and contact models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class Case(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "cases"

    customer_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # "failed_payment" | "overdue_invoice" | "escrow_funding"
    type: Mapped[str] = mapped_column(String(32), nullable=False, default="failed_payment")
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN", index=True)
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    # Stores trigger payload, invoice_id, subscription_id, etc.
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    contact_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    unrecovered_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # State transition history: [{from_state, to_state, actor, reason, timestamp}]
    history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Diagnosis result stored as JSON
    diagnosis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Dedup key from trigger (event_id)
    trigger_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    # For escrow funding cases
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    milestone_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class Contact(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "contacts"

    case_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
