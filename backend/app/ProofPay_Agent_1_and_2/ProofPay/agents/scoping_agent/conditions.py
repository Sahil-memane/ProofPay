"""Conditional edge routing functions for ProofPay Scoping Agent LangGraph.

All routing decisions are deterministic and inspect state variables.
"""

from typing import Literal
from ProofPay.agents.scoping_agent.state import (
    ScopingState,
    STATUS_ERROR,
    STATUS_NEEDS_CLARIFICATION,
)


def route_after_pre_validate(state: ScopingState) -> Literal["return_error", "check_clarity"]:
    """Conditional Edge A:
    - If input is invalid -> return_error
    - If input is valid -> check_clarity
    """
    if state.get("validation_errors") or state.get("project_status") == STATUS_ERROR:
        return "return_error"
    return "check_clarity"


def route_after_check_clarity(
    state: ScopingState,
) -> Literal["generate_milestones", "generate_questions", "handle_vague_clarification"]:
    """Conditional Edge B:
    - If requirements are clear -> generate_milestones
    - If requirements are vague and clarification has not been requested -> generate_questions
    - If requirements remain vague after the single clarification round -> handle_vague_clarification
    """
    clarification_count = state.get("clarification_count", 0)
    questions = state.get("clarification_questions", [])

    # If there are no questions or it's clear
    if not questions:
        return "generate_milestones"

    if clarification_count == 0:
        return "generate_questions"

    # Already had one clarification round and still vague
    return "handle_vague_clarification"


def route_after_generate_questions(
    state: ScopingState,
) -> Literal["update_project", "pause_for_clarification"]:
    """If clarification answers are already supplied in state, proceed to update_project.
    Otherwise pause for human input.
    """
    answers = state.get("clarification_answers")
    if answers:
        return "update_project"
    return "pause_for_clarification"


def route_after_validate_plan(
    state: ScopingState,
) -> Literal["save_draft", "repair_plan", "template_fallback"]:
    """Conditional Edge C:
    - If plan is valid -> save_draft
    - If plan is invalid and repair has not been attempted -> repair_plan
    - If plan is invalid and repair was already attempted -> template_fallback
    """
    errors = state.get("validation_errors", [])
    unresolved = state.get("unresolved_parameters", [])
    if not errors and not unresolved and not state.get("needs_human_edit", False):
        return "save_draft"

    repair_attempt = state.get("repair_attempt", 0)
    if repair_attempt == 0:
        return "repair_plan"

    return "template_fallback"


def route_after_repair_plan(
    state: ScopingState,
) -> Literal["save_draft", "template_fallback"]:
    """Conditional Edge D:
    - If repaired plan is valid -> save_draft
    - If still invalid -> template_fallback
    """
    errors = state.get("validation_errors", [])
    unresolved = state.get("unresolved_parameters", [])
    if not errors and not unresolved and not state.get("needs_human_edit", False):
        return "save_draft"
    return "template_fallback"


def route_after_collect_approvals(
    state: ScopingState,
) -> Literal["lock_plan", "keep_pending"]:
    """Conditional Edge F:
    - If valid plan exists, no validation errors, and both client and freelancer
      have approved the exact same plan -> lock_plan
    - Otherwise -> keep the plan pending approval
    """
    milestones = state.get("milestones", [])
    errors = state.get("validation_errors", [])
    unresolved = state.get("unresolved_parameters", [])
    if not milestones or len(milestones) < 2 or errors or state.get("needs_human_edit") or unresolved:
        return "keep_pending"

    client_appr = bool(state.get("client_approved", False))
    free_appr = bool(state.get("freelancer_approved", False))
    if not (client_appr and free_appr):
        return "keep_pending"

    c_hash = state.get("client_approved_hash")
    f_hash = state.get("freelancer_approved_hash")
    if not c_hash or not f_hash or c_hash != f_hash:
        return "keep_pending"

    return "lock_plan"


def route_after_validate_edit(
    state: ScopingState,
) -> Literal["save_draft", "keep_pending"]:
    """Conditional Edge G:
    When an edit is submitted:
    - If valid -> save_draft
    - If invalid -> keep_pending (with validation_errors populated)
    """
    errors = state.get("validation_errors", [])
    unresolved = state.get("unresolved_parameters", [])
    if not errors and not unresolved and not state.get("needs_human_edit", False):
        return "save_draft"
    return "keep_pending"




def route_after_lock_plan(state: ScopingState) -> Literal["emit_approved_event", "stop"]:
    """Emit the domain event only after lock_plan actually succeeded."""
    if (
        state.get("project_status") == "PLAN_APPROVED"
        and state.get("plan_hash")
        and state.get("approved_at")
    ):
        return "emit_approved_event"
    return "stop"
