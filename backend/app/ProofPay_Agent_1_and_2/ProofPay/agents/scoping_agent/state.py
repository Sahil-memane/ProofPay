"""LangGraph State definition for ProofPay Scoping Agent.

Follows Section 7 of the specification: TypedDict state passed between graph nodes.
"""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class ScopingState(TypedDict, total=False):
    """Shared state dictionary tracked and updated across the LangGraph orchestration.

    Mandatory fields specified by ProofPay design:
    - project_description: Raw or updated client project description
    - total_budget: Agreed total project budget amount
    - currency: 3-letter currency code (e.g., 'USD')
    - deadline: Project completion deadline string (e.g. '30 days', '2026-12-01')
    - client_id: Unique identifier of the client
    - freelancer_id: Unique identifier of the freelancer
    - clarification_count: Number of clarification loops attempted (max 1)
    - clarification_questions: List of questions generated when input is vague
    - milestones: List of milestone dictionaries containing criteria
    - validation_errors: List of error strings returned by deterministic validators
    - repair_attempt: Integer counter of LLM repair attempts (0 or 1)
    - llm_call_count: Counter of LLM calls made (max 2)
    - plan_source: Origin of current plan ('llm_generated', 'llm_repaired', 'template_fallback', 'human_edited')
    - needs_human_edit: Flag indicating the plan requires human review/adjustment
    - client_approved: Approval status from client
    - freelancer_approved: Approval status from freelancer
    - project_status: Current lifecycle status of the scoping workflow
    - plan_hash: SHA-256 fingerprint computed when the plan is locked
    - error_message: Error description if a fatal failure occurs

    Additional coordination fields:
    - clarification_answers: Question-to-answer mapping provided by the user
    - needs_human_edit_reasons: Explicit blocking reasons requiring human correction
    - approval_update: The latest explicit approval action, including a rejection
    - pending_edit: Candidate milestone plan submitted for validation
    - audit_log: Ordered trail of system events, actions, and decisions
    - approved_at: Timestamp when both parties approved and plan was locked
    """

    project_id: str
    project_description: str
    total_budget: float
    currency: str
    deadline: str
    client_id: str
    freelancer_id: str

    # Information provenance & configuration tracking
    user_provided_config: Dict[str, Any]
    unresolved_parameters: List[str]
    configuration_status: Dict[str, str]

    clarification_count: int
    clarification_questions: List[str]
    clarification_answers: Optional[Dict[str, str]]

    milestones: List[Dict[str, Any]]
    validation_errors: List[str]
    repair_attempt: int
    llm_call_count: int
    llm_calls_attempted: int
    llm_calls_succeeded: int
    llm_calls_failed: int
    plan_source: str
    needs_human_edit: bool

    client_approved: bool
    freelancer_approved: bool
    approval_update: Optional[Dict[str, Any]]
    needs_human_edit_reasons: List[str]
    client_approved_hash: Optional[str]
    freelancer_approved_hash: Optional[str]
    project_status: str
    plan_hash: Optional[str]
    error_message: Optional[str]

    pending_edit: Optional[List[Dict[str, Any]]]
    audit_log: List[Dict[str, Any]]
    approved_at: Optional[str]


# Lifecycle project status constants
STATUS_RECEIVED = "RECEIVED"
STATUS_PRE_VALIDATED = "PRE_VALIDATED"
STATUS_NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
STATUS_CLARIFICATION_REQUESTED = "CLARIFICATION_REQUESTED"
STATUS_DRAFT = "DRAFT"
STATUS_NEEDS_HUMAN_EDIT = "NEEDS_HUMAN_EDIT"
STATUS_PENDING_APPROVAL = "PENDING_APPROVAL"
STATUS_PLAN_APPROVED = "PLAN_APPROVED"
STATUS_ERROR = "ERROR"

