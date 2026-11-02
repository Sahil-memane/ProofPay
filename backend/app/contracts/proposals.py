"""
ProofPay Proposal and PolicyDecision contracts.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.app.contracts.enums import ActionKind, Verdict


class Proposal(BaseModel):
    """An agent's proposed action. The policy decides; the executor executes."""
    agent: str
    subject: str  # case_id, project_id, or milestone reference
    action: ActionKind
    params: dict[str, Any] = Field(default_factory=dict)
    reason: str
    inputs_used: list[str] = Field(default_factory=list)
    llm_used: bool = False
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    milestone_id: str | None = None
    project_id: str | None = None
    idempotency_key: str | None = None


class PolicyDecision(BaseModel):
    """Result of policy evaluation on a Proposal."""
    verdict: Verdict
    checks: dict[str, bool] = Field(default_factory=dict)
    blocked_by: list[str] = Field(default_factory=list)
    signed_at: datetime | None = None
    signing_key_id: str | None = None
