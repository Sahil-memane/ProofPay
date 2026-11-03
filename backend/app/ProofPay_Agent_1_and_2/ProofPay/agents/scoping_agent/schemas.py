"""Pydantic schemas for ProofPay Scoping Agent.

These schemas define structured data formats for project inputs,
milestone plans, acceptance criteria, clarification queries, and plan repairs.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class CriterionSchema(BaseModel):
    """Schema for a single acceptance criterion in a milestone."""
    id: str = Field(..., description="Unique criterion ID, e.g. 'c1', 'c2'")
    type: str = Field(..., description="Criterion type from predefined library")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters specific to the criterion type")
    weight: float = Field(..., ge=0.0, le=1.0, description="Criterion weight between 0.0 and 1.0")
    must_pass: bool = Field(True, description="Whether passing this criterion is mandatory for milestone acceptance")


class MilestoneSchema(BaseModel):
    """Schema for a milestone within a project plan."""
    id: str = Field(..., description="Unique milestone ID, e.g. 'm1', 'm2'")
    title: str = Field(..., min_length=3, max_length=150, description="Concise, descriptive title")
    description: str = Field(..., min_length=10, description="Detailed scope of deliverable")
    payment_amount: float = Field(..., gt=0.0, description="Milestone payout amount")
    deadline: str = Field(..., description="Milestone deadline as date (YYYY-MM-DD) or relative day marker")
    acceptance_criteria: List[CriterionSchema] = Field(
        ..., min_length=1, description="List of acceptance criteria for this milestone"
    )


class MilestonePlanSchema(BaseModel):
    """Structured plan returned by LLM milestone generation or repair."""
    milestones: List[MilestoneSchema] = Field(
        ..., min_length=2, max_length=6, description="List of 2 to 6 milestones"
    )
    summary: Optional[str] = Field(None, description="Executive summary of the milestone roadmap")


class ProjectInputSchema(BaseModel):
    """Incoming project submission schema."""
    project_description: str = Field(..., description="Raw project scope or briefing provided by client")
    total_budget: float = Field(..., gt=0.0, description="Total project budget")
    currency: str = Field("USD", min_length=3, max_length=3, description="3-letter currency code, e.g. USD")
    deadline: str = Field(..., description="Project completion deadline, e.g., '30 days' or '2026-12-01'")
    client_id: str = Field(..., description="Identifier of the client user")
    freelancer_id: str = Field(..., description="Identifier of the freelancer user")
    user_provided_config: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Optional client-provided project facts (for example, payment provider) and any "
            "real verification resources already available. Repository/deployment URLs are not "
            "required for Agent 1 milestone scoping."
        ),
    )


class ClarityCheckSchema(BaseModel):
    """Result of project requirements clarity inspection."""
    is_clear: bool = Field(..., description="True if requirements are sufficiently clear to scope milestones")
    reasoning: str = Field(..., description="Explanation of clarity assessment")
    clarification_questions: List[str] = Field(
        default_factory=list,
        description="Targeted clarification questions if requirements are vague (max 3)",
    )


class PlanEditRequestSchema(BaseModel):
    """Request schema for submitting a manual edit to a draft plan."""
    milestones: List[MilestoneSchema] = Field(..., min_length=2, max_length=6)
    editor_id: str = Field(..., description="User ID submitting the edit")


class ApprovalActionSchema(BaseModel):
    """Schema for client or freelancer approval submission."""
    user_id: str = Field(..., description="ID of client or freelancer submitting approval")
    role: str = Field(..., description="'client' or 'freelancer'")
    approved: bool = Field(..., description="True to approve, False to reject")
    comment: Optional[str] = Field(None, description="Optional note or comment")

