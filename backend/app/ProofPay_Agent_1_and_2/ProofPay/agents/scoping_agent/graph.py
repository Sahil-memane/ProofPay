"""LangGraph StateGraph orchestration for ProofPay Scoping Agent.

Implements all 15 required nodes, conditional edges, human-in-the-loop checkpointing,
and approval workflows.
"""

from typing import Any, Dict, List, Optional
import logging
import sqlite3
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:  # MemorySaver remains a safe test/development fallback.
    SqliteSaver = None

from ProofPay.agents.scoping_agent.state import (
    ScopingState,
    STATUS_RECEIVED,
    STATUS_ERROR,
    STATUS_DRAFT,
    STATUS_PLAN_APPROVED,
)
from ProofPay.agents.scoping_agent.nodes import (
    receive_project,
    pre_validate,
    check_clarity,
    generate_questions,
    handle_vague_clarification,
    update_project,
    generate_milestones,
    validate_plan,
    repair_plan,
    template_fallback,
    save_draft,
    collect_approvals,
    validate_edit,
    lock_plan,
    emit_approved_event,
    return_error,
)
from ProofPay.agents.scoping_agent.validators import (
    compute_plan_hash,
    validate_and_correct_milestone_plan,
)
from ProofPay.services.database import get_database_path
from ProofPay.agents.scoping_agent.conditions import (
    route_after_pre_validate,
    route_after_check_clarity,
    route_after_generate_questions,
    route_after_validate_plan,
    route_after_repair_plan,
    route_after_collect_approvals,
    route_after_validate_edit,
    route_after_lock_plan,
)


def route_entry_point(state: ScopingState) -> str:
    """Intelligent entry router for new runs, edits, clarifications, and approval resumes."""
    # 1. If an edit is pending, route directly to deterministic validator
    if state.get("pending_edit"):
        return "validate_edit"

    # 2. If clarification answers are submitted, route to update_project
    if state.get("clarification_answers"):
        return "update_project"

    # 3. An explicit approval action (including rejection) routes to approval evaluation.
    if state.get("milestones") and state.get("approval_update"):
        return "collect_approvals"

    # Backward-compatible path for persisted states with an existing approval flag.
    if state.get("milestones") and (state.get("client_approved") or state.get("freelancer_approved")):
        return "collect_approvals"

    # 4. Standard new project flow: proceed to pre_validate
    return "pre_validate"


def create_scoping_graph(checkpointer: Optional[Any] = None) -> Any:
    """Build, wire, and compile the ProofPay Scoping Agent StateGraph."""
    builder = StateGraph(ScopingState)

    # -------------------------------------------------------------------------
    # Register all 15 Nodes + vague clarification handler
    # -------------------------------------------------------------------------
    builder.add_node("receive_project", receive_project)
    builder.add_node("pre_validate", pre_validate)
    builder.add_node("check_clarity", check_clarity)
    builder.add_node("generate_questions", generate_questions)
    builder.add_node("handle_vague_clarification", handle_vague_clarification)
    builder.add_node("update_project", update_project)
    builder.add_node("generate_milestones", generate_milestones)
    builder.add_node("validate_plan", validate_plan)
    builder.add_node("repair_plan", repair_plan)
    builder.add_node("template_fallback", template_fallback)
    builder.add_node("save_draft", save_draft)
    builder.add_node("collect_approvals", collect_approvals)
    builder.add_node("validate_edit", validate_edit)
    builder.add_node("lock_plan", lock_plan)
    builder.add_node("emit_approved_event", emit_approved_event)
    builder.add_node("return_error", return_error)

    # -------------------------------------------------------------------------
    # Define Edges and Conditional Edges
    # -------------------------------------------------------------------------

    # START -> receive_project
    builder.add_edge(START, "receive_project")

    # receive_project -> route_entry_point
    builder.add_conditional_edges(
        "receive_project",
        route_entry_point,
        {
            "validate_edit": "validate_edit",
            "update_project": "update_project",
            "collect_approvals": "collect_approvals",
            "pre_validate": "pre_validate",
        },
    )

    # Conditional Edge A: After pre_validate
    builder.add_conditional_edges(
        "pre_validate",
        route_after_pre_validate,
        {
            "return_error": "return_error",
            "check_clarity": "check_clarity",
        },
    )

    # Terminal error node
    builder.add_edge("return_error", END)

    # Conditional Edge B: After check_clarity
    builder.add_conditional_edges(
        "check_clarity",
        route_after_check_clarity,
        {
            "generate_milestones": "generate_milestones",
            "generate_questions": "generate_questions",
            "handle_vague_clarification": "handle_vague_clarification",
        },
    )

    # Terminal vague clarification
    builder.add_edge("handle_vague_clarification", END)

    # After generate_questions
    builder.add_conditional_edges(
        "generate_questions",
        route_after_generate_questions,
        {
            "update_project": "update_project",
            "pause_for_clarification": END,
        },
    )

    # update_project -> check_clarity (re-verify clarity with new info)
    builder.add_edge("update_project", "check_clarity")

    # generate_milestones -> validate_plan
    builder.add_edge("generate_milestones", "validate_plan")

    # Conditional Edge C: After validate_plan
    builder.add_conditional_edges(
        "validate_plan",
        route_after_validate_plan,
        {
            "save_draft": "save_draft",
            "repair_plan": "repair_plan",
            "template_fallback": "template_fallback",
        },
    )

    # Conditional Edge D: After repair_plan
    builder.add_conditional_edges(
        "repair_plan",
        route_after_repair_plan,
        {
            "save_draft": "save_draft",
            "template_fallback": "template_fallback",
        },
    )

    # Conditional Edge E: template_fallback -> save_draft
    builder.add_edge("template_fallback", "save_draft")

    # save_draft -> collect_approvals
    builder.add_edge("save_draft", "collect_approvals")

    # Conditional Edge F: After collect_approvals
    builder.add_conditional_edges(
        "collect_approvals",
        route_after_collect_approvals,
        {
            "lock_plan": "lock_plan",
            "keep_pending": END,
        },
    )

    # Conditional Edge G: After validate_edit
    builder.add_conditional_edges(
        "validate_edit",
        route_after_validate_edit,
        {
            "save_draft": "save_draft",
            "keep_pending": END,
        },
    )

    # Conditional Edge H: After lock_plan
    builder.add_conditional_edges(
        "lock_plan",
        route_after_lock_plan,
        {
            "emit_approved_event": "emit_approved_event",
            "stop": END,
        },
    )
    builder.add_edge("emit_approved_event", END)

    # Compile with memory saver checkpointing
    return builder.compile(checkpointer=checkpointer)


# -----------------------------------------------------------------------------
# Runtime Controller & Helper API
# -----------------------------------------------------------------------------

class ScopingAgentRunner:
    """Helper manager to execute and manage conversational state for Scoping Agent."""

    def __init__(self, checkpointer: Optional[Any] = None):
        self._checkpoint_connection = None
        if checkpointer is not None:
            self.checkpointer = checkpointer
        elif SqliteSaver is not None:
            # Persist graph state (including pending clarification and approvals)
            # in the same SQLite file as project records.
            checkpoint_path = get_database_path()
            self._checkpoint_connection = sqlite3.connect(
                checkpoint_path, check_same_thread=False, timeout=30
            )
            self.checkpointer = SqliteSaver(self._checkpoint_connection)
            self.checkpointer.setup()
        else:
            logging.getLogger("ProofPay").warning(
                "langgraph-checkpoint-sqlite is not installed; graph checkpoints are in-memory only. "
                "Install requirements.txt for restart-safe workflows."
            )
            self.checkpointer = MemorySaver()
        self.graph = create_scoping_graph(checkpointer=self.checkpointer)

    def start_project(self, project_data: Dict[str, Any], thread_id: str = "default") -> ScopingState:
        """Start a new scoping workflow with initial project details."""
        config = {"configurable": {"thread_id": thread_id}}
        final_state = self.graph.invoke(project_data, config=config)
        return final_state

    def submit_clarification(
        self,
        thread_id: str,
        clarification_answers: Dict[str, str],
    ) -> ScopingState:
        """Submit answers to clarification questions and resume workflow."""
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.graph.get_state(config)
        current_state = snapshot.values if snapshot else {}
        questions = current_state.get("clarification_questions") or []

        if current_state.get("project_status") != "CLARIFICATION_REQUESTED" or not questions:
            raise ValueError("This project has no pending clarification questions.")

        if not isinstance(clarification_answers, dict):
            raise ValueError("Clarification answers must be a question-to-answer dictionary.")

        expected = {str(question) for question in questions}
        supplied = {str(question) for question in clarification_answers}
        unknown = supplied - expected
        missing = expected - supplied
        blank = [
            question for question, answer in clarification_answers.items()
            if answer is None or not str(answer).strip()
        ]
        if unknown:
            raise ValueError(f"Answers were supplied for unknown questions: {sorted(unknown)}")
        if missing or blank:
            raise ValueError(
                "Please answer every pending clarification question. "
                f"Missing: {sorted(missing | set(map(str, blank)))}"
            )

        input_data = {
            "clarification_answers": {
                str(question): str(answer).strip()
                for question, answer in clarification_answers.items()
            }
        }
        return self.graph.invoke(input_data, config=config)

    def submit_edit(
        self,
        thread_id: str,
        edited_milestones: List[Dict[str, Any]],
    ) -> ScopingState:
        """Submit a manual edit for deterministic validation without calling the LLM."""
        config = {"configurable": {"thread_id": thread_id}}
        input_data = {"pending_edit": edited_milestones}
        return self.graph.invoke(input_data, config=config)

    def submit_approval(
        self,
        thread_id: str,
        user_id: str,
        role: str,
        approved: bool = True,
        comment: Optional[str] = None,
    ) -> ScopingState:
        """Submit approval only for the matching project participant and a valid draft."""
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.graph.get_state(config)
        current_state = snapshot.values if snapshot else {}

        milestones = current_state.get("milestones", [])
        if not milestones:
            return {
                **current_state,
                "error_message": "Cannot submit approval: No milestone plan exists yet.",
            }

        normalized_role = (role or "").strip().lower()
        if normalized_role == "client":
            expected_user_id = current_state.get("client_id")
        elif normalized_role == "freelancer":
            expected_user_id = current_state.get("freelancer_id")
        else:
            raise ValueError("Unknown role. Must be 'client' or 'freelancer'.")

        if not user_id or user_id != expected_user_id:
            return {
                **current_state,
                "error_message": f"Approval rejected: user identity does not match the project's {normalized_role}.",
            }

        if current_state.get("project_status") not in (STATUS_DRAFT, "PENDING_APPROVAL"):
            return {
                **current_state,
                "error_message": (
                    "Approval rejected: the project is not in an approvable draft state "
                    f"(current status: {current_state.get('project_status')})."
                ),
            }

        if (
            current_state.get("needs_human_edit")
            or current_state.get("validation_errors")
            or current_state.get("unresolved_parameters")
        ):
            return {
                **current_state,
                "error_message": "Approval rejected: the milestone plan has unresolved or blocking validation issues.",
            }

        is_valid, errors, _, unresolved = validate_and_correct_milestone_plan(
            milestones=milestones,
            total_budget=current_state.get("total_budget", 0.0),
            project_deadline=current_state.get("deadline", ""),
            user_provided_config=current_state.get("user_provided_config") or {},
            enforce_provenance=True,
        )
        if not is_valid or unresolved:
            return {
                **current_state,
                "error_message": "Approval rejected: plan validation failed. " + "; ".join(errors + unresolved),
            }

        try:
            current_plan_hash = compute_plan_hash(
                milestones=milestones,
                total_budget=current_state.get("total_budget", 0.0),
                currency=current_state.get("currency", "USD"),
                project_id=current_state.get("project_id"),
            )
        except Exception as e:
            return {
                **current_state,
                "error_message": f"Cannot submit approval: Failed to compute plan hash: {str(e)}",
            }

        update_payload: Dict[str, Any] = {}
        if normalized_role == "client":
            update_payload["client_approved"] = bool(approved)
            update_payload["client_approved_hash"] = current_plan_hash if approved else None
        else:
            update_payload["freelancer_approved"] = bool(approved)
            update_payload["freelancer_approved_hash"] = current_plan_hash if approved else None
        update_payload["approval_update"] = {
            "role": normalized_role,
            "user_id": user_id,
            "approved": bool(approved),
            "comment": (comment or "").strip(),
        }

        merged = {**current_state, **update_payload}
        return self.graph.invoke(merged, config=config)

    def simulate_both_approvals(self, thread_id: str) -> ScopingState:
        """Simulate client and freelancer approving the plan to trigger locking."""
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.graph.get_state(config)
        current_state = snapshot.values if snapshot else {}

        milestones = current_state.get("milestones", [])
        if not milestones:
            return {
                **current_state,
                "error_message": "Cannot simulate approvals: No milestone plan exists yet.",
            }

        if (
            current_state.get("project_status") not in (STATUS_DRAFT, "PENDING_APPROVAL")
            or current_state.get("needs_human_edit")
            or current_state.get("validation_errors")
            or current_state.get("unresolved_parameters")
        ):
            return {
                **current_state,
                "error_message": "Cannot simulate approvals: plan is not a fully validated draft.",
            }

        is_valid, errors, _, unresolved = validate_and_correct_milestone_plan(
            milestones=milestones,
            total_budget=current_state.get("total_budget", 0.0),
            project_deadline=current_state.get("deadline", ""),
            user_provided_config=current_state.get("user_provided_config") or {},
            enforce_provenance=True,
        )
        if not is_valid or unresolved:
            return {
                **current_state,
                "error_message": "Cannot simulate approvals: plan validation failed. " + "; ".join(errors + unresolved),
            }

        current_plan_hash = compute_plan_hash(
            milestones=milestones,
            total_budget=current_state.get("total_budget", 0.0),
            currency=current_state.get("currency", "USD"),
            project_id=current_state.get("project_id"),
        )
        merged = {
            **current_state,
            "client_approved": True,
            "client_approved_hash": current_plan_hash,
            "freelancer_approved": True,
            "freelancer_approved_hash": current_plan_hash,
            "approval_update": {"role": "demo", "approved": True},
        }
        return self.graph.invoke(merged, config=config)

    def get_state(self, thread_id: str) -> Optional[ScopingState]:
        """Fetch current state snapshot for a thread."""
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.graph.get_state(config)
        return snapshot.values if snapshot else None

    def close(self) -> None:
        """Close the runner's SQLite checkpoint connection when one is owned."""
        if self._checkpoint_connection is not None:
            self._checkpoint_connection.close()
            self._checkpoint_connection = None

