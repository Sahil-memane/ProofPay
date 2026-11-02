# TEMP: replaced by contracts/
"""Stub contracts: Proposal, PolicyDecision, and shared enums."""
from __future__ import annotations
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


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


class Channel(str, Enum):
    EMAIL = "email"
    PAYMENT_LINK = "payment_link"


class Proposal(BaseModel):
    """An agent's proposed action. The policy decides; the executor executes."""
    agent: str
    subject: str                        # case_id or entity reference
    action: ActionKind
    params: dict[str, Any] = Field(default_factory=dict)
    reason: str
    inputs_used: list[str] = Field(default_factory=list)
    llm_used: bool = False
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class PolicyDecision(BaseModel):
    """Result of policy evaluation on a Proposal."""
    verdict: Verdict
    checks: dict[str, bool] = Field(default_factory=dict)
    blocked_by: list[str] = Field(default_factory=list)
