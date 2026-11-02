"""
Escrow State Machine.

Enforces allowed transitions for Projects and Milestones:
  Project: DRAFT -> PLAN_APPROVED -> FUNDED -> COMPLETED | CANCELLED
  Milestone: DRAFT -> FUNDED -> SUBMITTED -> VERIFYING -> IN_REVIEW | RELEASED | REFUNDED | DISPUTED

Audits transitions and writes to DB repositories.
"""
from __future__ import annotations

from typing import Any

from backend.app.audit.writer import log_event
from backend.app.contracts.enums import MilestoneState, ProjectState

PROJECT_TRANSITIONS: dict[ProjectState, set[ProjectState]] = {
    ProjectState.DRAFT: {ProjectState.PLAN_APPROVED, ProjectState.CANCELLED},
    ProjectState.PLAN_APPROVED: {ProjectState.FUNDED, ProjectState.CANCELLED},
    ProjectState.FUNDED: {ProjectState.COMPLETED, ProjectState.CANCELLED},
    ProjectState.COMPLETED: set(),
    ProjectState.CANCELLED: set(),
}

MILESTONE_TRANSITIONS: dict[MilestoneState, set[MilestoneState]] = {
    MilestoneState.DRAFT: {MilestoneState.FUNDED},
    MilestoneState.FUNDED: {MilestoneState.SUBMITTED, MilestoneState.REFUNDED, MilestoneState.DISPUTED},
    MilestoneState.SUBMITTED: {MilestoneState.VERIFYING, MilestoneState.IN_REVIEW, MilestoneState.DISPUTED},
    MilestoneState.VERIFYING: {MilestoneState.RELEASED, MilestoneState.IN_REVIEW, MilestoneState.DISPUTED},
    MilestoneState.IN_REVIEW: {MilestoneState.RELEASED, MilestoneState.SUBMITTED, MilestoneState.REFUNDED, MilestoneState.DISPUTED},
    MilestoneState.RELEASED: set(),
    MilestoneState.REFUNDED: set(),
    MilestoneState.DISPUTED: {MilestoneState.RELEASED, MilestoneState.REFUNDED},
}


class InvalidEscrowTransitionError(ValueError):
    """Raised when an illegal transition is attempted on project or milestone."""
    pass


def can_transition_project(current: ProjectState | str, target: ProjectState | str) -> bool:
    curr = ProjectState(current) if isinstance(current, str) else current
    tgt = ProjectState(target) if isinstance(target, str) else target
    return tgt in PROJECT_TRANSITIONS.get(curr, set())


def can_transition_milestone(current: MilestoneState | str, target: MilestoneState | str) -> bool:
    curr = MilestoneState(current) if isinstance(current, str) else current
    tgt = MilestoneState(target) if isinstance(target, str) else target
    return tgt in MILESTONE_TRANSITIONS.get(curr, set())


def transition_project(
    project_id: str,
    target: ProjectState | str,
    actor: str = "system",
    reason: str = "",
    current: ProjectState | str = ProjectState.DRAFT,
) -> ProjectState:
    curr = ProjectState(current) if isinstance(current, str) else current
    tgt = ProjectState(target) if isinstance(target, str) else target

    if not can_transition_project(curr, tgt):
        raise InvalidEscrowTransitionError(
            f"Cannot transition project {project_id} from {curr.value} to {tgt.value}"
        )

    log_event(
        "project_state_transition",
        {
            "project_id": project_id,
            "from_state": curr.value,
            "to_state": tgt.value,
            "actor": actor,
            "reason": reason,
        },
    )
    return tgt


def transition_milestone(
    milestone_id: str,
    target: MilestoneState | str,
    actor: str = "system",
    reason: str = "",
    current: MilestoneState | str = MilestoneState.DRAFT,
) -> MilestoneState:
    curr = MilestoneState(current) if isinstance(current, str) else current
    tgt = MilestoneState(target) if isinstance(target, str) else target

    if not can_transition_milestone(curr, tgt):
        raise InvalidEscrowTransitionError(
            f"Cannot transition milestone {milestone_id} from {curr.value} to {tgt.value}"
        )

    log_event(
        "milestone_state_transition",
        {
            "milestone_id": milestone_id,
            "from_state": curr.value,
            "to_state": tgt.value,
            "actor": actor,
            "reason": reason,
        },
    )
    return tgt
