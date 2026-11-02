"""Scheduler, policy config, reputation, reconciliation, and eval models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class ScheduledAction(UUIDPrimaryKey, Base):
    """
    DB-backed scheduled job queue.
    APScheduler reads this table — restarts and free-tier sleeps lose nothing.
    """

    __tablename__ = "scheduled_actions"

    func_name: Mapped[str] = mapped_column(String(128), nullable=False)
    kwargs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    # pending | running | done | failed | cancelled
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    case_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PolicyConfig(Base):
    """Key-value store for all runtime-adjustable policy limits."""

    __tablename__ = "policy_config"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ReputationEvent(UUIDPrimaryKey, Base):
    """One event contributing to a subject's reputation score."""

    __tablename__ = "reputation_events"

    subject: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    audit_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReconRecord(UUIDPrimaryKey, Base):
    """Normalised record from any of the three reconciliation sources."""

    __tablename__ = "reconciliation_records"

    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    customer_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReconMatch(UUIDPrimaryKey, Base):
    """Result of matching a reconciliation record against a case."""

    __tablename__ = "reconciliation_matches"

    record_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # auto_match | human_review | exception
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    anomalies: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EvalRun(UUIDPrimaryKey, Base):
    """Stores one evaluation harness run (agent vs baseline)."""

    __tablename__ = "eval_runs"

    strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ApprovalTask(UUIDPrimaryKey, TimestampMixin, Base):
    """Human approval task created when policy returns NEEDS_APPROVAL."""

    __tablename__ = "approval_tasks"

    subject: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    proposal: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    decision: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # pending | approved | rejected
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    actor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
