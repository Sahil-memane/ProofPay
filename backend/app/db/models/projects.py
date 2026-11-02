"""Escrow project and milestone models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class Project(UUIDPrimaryKey, TimestampMixin, Base):
    """Escrow project (one freelancer engagement)."""

    __tablename__ = "projects"

    # DRAFT | PLAN_APPROVED | FUNDED | COMPLETED | CANCELLED
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True)
    plan_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    # Party IDs
    client_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    freelancer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Approval tracking
    client_approved: Mapped[bool] = mapped_column(default=False, nullable=False)
    freelancer_approved: Mapped[bool] = mapped_column(default=False, nullable=False)
    # PayPal order ID (set on /fund)
    paypal_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # PayPal capture ID (set on capture webhook)
    paypal_capture_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Source job description
    job_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Milestone(UUIDPrimaryKey, TimestampMixin, Base):
    """A single verifiable milestone within a project."""

    __tablename__ = "milestones"

    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # DRAFT | FUNDED | SUBMITTED | VERIFYING | IN_REVIEW | RELEASED | REFUNDED | DISPUTED
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    # List of criterion objects: [{id, type, params, weight, must_pass}]
    criteria: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sequence: Mapped[int] = mapped_column(default=0, nullable=False)
    # Submission tracking
    submission_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_submissions: Mapped[int] = mapped_column(default=3, nullable=False)


class LedgerEntry(UUIDPrimaryKey, Base):
    """
    Append-only financial ledger.
    Types: FUNDING | HOLD | RELEASE | REFUND
    INSERT-ONLY enforced by revoking UPDATE/DELETE in migration.
    """

    __tablename__ = "ledger_entries"

    # FUNDING | HOLD | RELEASE | REFUND
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # project_id or milestone_id
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    paypal_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    from sqlalchemy import DateTime, func
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
