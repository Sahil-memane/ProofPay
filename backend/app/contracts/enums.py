"""
ProofPay Shared Enums.
Defines verdicts, states, action kinds, and actors across both recovery and escrow modules.
"""
from __future__ import annotations

from enum import Enum


class Verdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    NEEDS_APPROVAL = "needs_approval"


class CaseState(str, Enum):
    OPEN = "OPEN"
    RECONCILING = "RECONCILING"
    DIAGNOSED = "DIAGNOSED"
    ACTION_PENDING_APPROVAL = "ACTION_PENDING_APPROVAL"
    ACTION_SENT = "ACTION_SENT"
    AWAITING_RESULT = "AWAITING_RESULT"
    RECOVERED = "RECOVERED"
    HALTED = "HALTED"
    UNRECOVERED = "UNRECOVERED"
    PAID_ELSEWHERE = "PAID_ELSEWHERE"


FINAL_STATES = {
    CaseState.RECOVERED,
    CaseState.HALTED,
    CaseState.UNRECOVERED,
    CaseState.PAID_ELSEWHERE,
}


class ActionKind(str, Enum):
    SEND_EMAIL = "send_email"
    SEND_PAYMENT_LINK = "send_payment_link"
    ESCALATE = "escalate"
    MARK_PAID_ELSEWHERE = "mark_paid_elsewhere"
    NO_OP = "no_op"
    # Escrow & PayPal actions
    CREATE_ORDER = "create_order"
    CAPTURE_ORDER = "capture_order"
    PAYOUT = "payout"
    REFUND = "refund"
    RETRY = "retry"
    REMINDER = "reminder"
    PAYMENT_LINK = "payment_link"


class Channel(str, Enum):
    EMAIL = "email"
    PAYMENT_LINK = "payment_link"


class MilestoneState(str, Enum):
    DRAFT = "DRAFT"
    FUNDED = "FUNDED"
    SUBMITTED = "SUBMITTED"
    VERIFYING = "VERIFYING"
    IN_REVIEW = "IN_REVIEW"
    RELEASED = "RELEASED"
    REFUNDED = "REFUNDED"
    DISPUTED = "DISPUTED"


class ProjectState(str, Enum):
    DRAFT = "DRAFT"
    PLAN_APPROVED = "PLAN_APPROVED"
    FUNDED = "FUNDED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ActorType(str, Enum):
    agent = "agent"
    policy = "policy"
    executor = "executor"
    human = "human"
    system = "system"
    webhook = "webhook"


class ActionType(str, Enum):
    create_order = "create_order"
    capture_order = "capture_order"
    payout = "payout"
    refund = "refund"
    retry = "retry"
    reminder = "reminder"
    payment_link = "payment_link"
