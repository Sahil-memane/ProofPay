"""Initial schema — all ProofPay tables.

Revision ID: 001
Revises:
Create Date: 2026-11-03
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── cases ─────────────────────────────────────────────────────────────────
    op.create_table(
        "cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.String(64), nullable=False),
        sa.Column("type", sa.String(32), nullable=False, server_default="failed_payment"),
        sa.Column("state", sa.String(32), nullable=False, server_default="OPEN"),
        sa.Column("amount_usd", sa.Float, nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("contact_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_contact_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority_score", sa.Float, nullable=True),
        sa.Column("unrecovered_reason", sa.Text, nullable=True),
        sa.Column("history", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("diagnosis", postgresql.JSONB, nullable=True),
        sa.Column("trigger_event_id", sa.String(128), nullable=True),
        sa.Column("project_id", sa.String(36), nullable=True),
        sa.Column("milestone_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_cases_customer_id", "cases", ["customer_id"])
    op.create_index("ix_cases_state", "cases", ["state"])
    op.create_index("ix_cases_project_id", "cases", ["project_id"])
    op.create_unique_constraint("uq_cases_trigger_event_id", "cases", ["trigger_event_id"])

    # ── contacts ──────────────────────────────────────────────────────────────
    op.create_table(
        "contacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_contacts_case_id", "contacts", ["case_id"])
    op.create_unique_constraint("uq_contacts_idempotency_key", "contacts", ["idempotency_key"])

    # ── audit_log (INSERT-ONLY) ───────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("subject", sa.String(128), nullable=False),
        sa.Column("actor", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("prev_hash", sa.String(64), nullable=True),
        sa.Column("row_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("search_text", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_subject", "audit_log", ["subject"])
    op.create_index("ix_audit_log_event_type", "audit_log", ["event_type"])
    # Full-text search GIN index on search_text
    op.execute(
        "CREATE INDEX ix_audit_log_fts ON audit_log USING GIN (to_tsvector('english', COALESCE(search_text, '')))"
    )
    # Trigger: block UPDATE and DELETE on audit_log
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_log_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log rows are immutable';
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER audit_log_no_update
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION audit_log_immutable();
    """)

    # ── outbox_messages ───────────────────────────────────────────────────────
    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("recipient", sa.String(256), nullable=False),
        sa.Column("subject", sa.String(512), nullable=False, server_default=""),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_outbox_case_id", "outbox_messages", ["case_id"])
    op.create_unique_constraint("uq_outbox_idempotency_key", "outbox_messages", ["idempotency_key"])

    # ── webhook_events ────────────────────────────────────────────────────────
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="paypal"),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_webhook_events_event_id", "webhook_events", ["event_id"])
    op.create_index("ix_webhook_events_event_id", "webhook_events", ["event_id"])
    op.create_index("ix_webhook_events_status", "webhook_events", ["status"])
    op.create_index("ix_webhook_events_event_type", "webhook_events", ["event_type"])

    # ── executor_actions ──────────────────────────────────────────────────────
    op.create_table(
        "executor_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("idempotency_key", sa.String(256), nullable=False),
        sa.Column("proposal", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("decision", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("result", postgresql.JSONB, nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_executor_actions_key", "executor_actions", ["idempotency_key"])
    op.create_index("ix_executor_actions_key", "executor_actions", ["idempotency_key"])

    # ── projects ──────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("state", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("plan_hash", sa.String(64), nullable=True),
        sa.Column("total_amount", sa.Float, nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("client_id", sa.String(64), nullable=True),
        sa.Column("freelancer_id", sa.String(64), nullable=True),
        sa.Column("client_approved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("freelancer_approved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("paypal_order_id", sa.String(64), nullable=True),
        sa.Column("paypal_capture_id", sa.String(64), nullable=True),
        sa.Column("job_description", sa.Text, nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_projects_state", "projects", ["state"])

    # ── milestones ────────────────────────────────────────────────────────────
    op.create_table(
        "milestones",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("state", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("title", sa.String(256), nullable=False, server_default=""),
        sa.Column("amount", sa.Float, nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("criteria", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sequence", sa.Integer, nullable=False, server_default="0"),
        sa.Column("submission_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_submissions", sa.Integer, nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.create_index("ix_milestones_project_id", "milestones", ["project_id"])
    op.create_index("ix_milestones_state", "milestones", ["state"])

    # ── ledger_entries (INSERT-ONLY) ──────────────────────────────────────────
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("paypal_id", sa.String(128), nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ledger_entries_type", "ledger_entries", ["type"])
    op.create_index("ix_ledger_entries_subject_id", "ledger_entries", ["subject_id"])

    # ── scheduled_actions ─────────────────────────────────────────────────────
    op.create_table(
        "scheduled_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("func_name", sa.String(128), nullable=False),
        sa.Column("kwargs", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("case_id", sa.String(36), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_scheduled_actions_due_at", "scheduled_actions", ["due_at"])
    op.create_index("ix_scheduled_actions_status", "scheduled_actions", ["status"])
    op.create_index("ix_scheduled_actions_case_id", "scheduled_actions", ["case_id"])

    # ── policy_config ─────────────────────────────────────────────────────────
    op.create_table(
        "policy_config",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # Seed default policy values
    op.execute("""
        INSERT INTO policy_config (key, value, description) VALUES
        ('auto_action_limit_usd',   '200',   'Max amount for auto-action without approval'),
        ('contact_cap',             '4',     'Max contacts per recovery case'),
        ('min_gap_hours',           '48',    'Minimum hours between contacts'),
        ('quiet_hours_start',       '21',    'Quiet hours start (customer local hour)'),
        ('quiet_hours_end',         '8',     'Quiet hours end (customer local hour)'),
        ('daily_action_cap',        '50',    'Max actions dispatched per day'),
        ('max_release_amount_usd',  '50000', 'Max single payout amount'),
        ('max_project_total_usd',   '500000','Max total project escrow value'),
        ('llm_daily_cap',           '100',   'Max LLM calls per day'),
        ('recon_auto_match_threshold', '0.90', 'Reconciliation auto-match score threshold'),
        ('recon_human_review_threshold', '0.60', 'Reconciliation human-review score threshold'),
        ('verifier_auto_release_threshold', '0.90', 'Verifier score for auto-release'),
        ('verifier_in_review_threshold', '0.60', 'Verifier score for in-review routing')
        ON CONFLICT (key) DO NOTHING;
    """)

    # ── reputation_events ─────────────────────────────────────────────────────
    op.create_table(
        "reputation_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("subject", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("delta", sa.Integer, nullable=False, server_default="0"),
        sa.Column("audit_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reputation_events_subject", "reputation_events", ["subject"])

    # ── reconciliation_records ────────────────────────────────────────────────
    op.create_table(
        "reconciliation_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("customer_ref", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_recon_records_source", "reconciliation_records", ["source"])
    op.create_index("ix_recon_records_external_id", "reconciliation_records", ["external_id"])

    # ── reconciliation_matches ────────────────────────────────────────────────
    op.create_table(
        "reconciliation_matches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("record_id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("score", sa.Float, nullable=False, server_default="0"),
        sa.Column("verdict", sa.String(32), nullable=False),
        sa.Column("anomalies", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_recon_matches_record_id", "reconciliation_matches", ["record_id"])
    op.create_index("ix_recon_matches_case_id", "reconciliation_matches", ["case_id"])

    # ── eval_runs ─────────────────────────────────────────────────────────────
    op.create_table(
        "eval_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("strategy", sa.String(64), nullable=False),
        sa.Column("metrics", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── approval_tasks ────────────────────────────────────────────────────────
    op.create_table(
        "approval_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("subject", sa.String(128), nullable=False),
        sa.Column("proposal", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("decision", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("actor", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_approval_tasks_subject", "approval_tasks", ["subject"])
    op.create_index("ix_approval_tasks_status", "approval_tasks", ["status"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("approval_tasks")
    op.drop_table("eval_runs")
    op.drop_table("reconciliation_matches")
    op.drop_table("reconciliation_records")
    op.drop_table("reputation_events")
    op.drop_table("policy_config")
    op.drop_table("scheduled_actions")
    op.drop_table("ledger_entries")
    op.drop_table("milestones")
    op.drop_table("projects")
    op.drop_table("executor_actions")
    op.drop_table("webhook_events")
    op.drop_table("outbox_messages")
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_update ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS audit_log_immutable()")
    op.drop_table("audit_log")
    op.drop_table("contacts")
    op.drop_table("cases")
