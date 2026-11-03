"""
Escrow scheduler jobs — milestone deadline reminders and stale review pings.
Appended to handlers.py; does NOT modify existing recovery job handlers.
"""
from __future__ import annotations

from typing import Any

from backend.app import audit as _audit
from backend.app.core import clock as _clock


def submission_deadline_reminder(milestone_id: str) -> dict[str, Any]:
    """
    Remind the freelancer N days before a milestone's deadline.
    Only fires if the milestone is still FUNDED or SUBMITTED (not yet delivered).
    """
    from backend.app.api.projects import _MILESTONES, _PROJECTS

    milestone: dict[str, Any] | None = None
    project: dict[str, Any] | None = None

    for pid, milestones in _MILESTONES.items():
        for m in milestones:
            if m.get("id") == milestone_id:
                milestone = m
                project = _PROJECTS.get(pid)
                break
        if milestone:
            break

    if not milestone or milestone.get("state") not in ("FUNDED", "SUBMITTED"):
        return {"status": "skipped", "milestone_id": milestone_id}

    freelancer_id = (project or {}).get("freelancer_id", "")
    title = milestone.get("title", milestone_id)

    # Enqueue notification via outbox (channels module)
    try:
        from backend.app.channels.outbox import record_message
        record_message(
            case_id=milestone_id,
            channel="email",
            to=freelancer_id,
            subject=f"Reminder: '{title}' submission due soon",
            body=f"Please submit your evidence for '{title}' before the deadline.",
        )
    except Exception:
        pass  # outbox is best-effort

    _audit.log_event("submission_deadline_reminder_sent", {
        "subject": milestone_id,
        "actor": "scheduler",
        "freelancer_id": freelancer_id,
        "timestamp": _clock.utcnow().isoformat(),
    })
    return {"status": "reminder_sent", "milestone_id": milestone_id}


def stale_review_reminder(milestone_id: str) -> dict[str, Any]:
    """
    Ping the client when a milestone has been IN_REVIEW for > 48 h.
    """
    from backend.app.api.projects import _MILESTONES, _PROJECTS

    milestone = None
    project = None

    for pid, milestones in _MILESTONES.items():
        for m in milestones:
            if m.get("id") == milestone_id:
                milestone = m
                project = _PROJECTS.get(pid)
                break
        if milestone:
            break

    if not milestone or milestone.get("state") != "IN_REVIEW":
        return {"status": "skipped", "milestone_id": milestone_id}

    client_id = (project or {}).get("client_id", "")
    title = milestone.get("title", milestone_id)

    try:
        from backend.app.channels.outbox import record_message
        record_message(
            case_id=milestone_id,
            channel="email",
            to=client_id,
            subject=f"Action needed: review '{title}'",
            body="A milestone is waiting for your review in ProofPay. Please log in to approve or reject.",
        )
    except Exception:
        pass

    _audit.log_event("stale_review_reminder_sent", {
        "subject": milestone_id,
        "actor": "scheduler",
        "client_id": client_id,
        "timestamp": _clock.utcnow().isoformat(),
    })
    return {"status": "reminder_sent", "milestone_id": milestone_id}


def stale_escrow_reminder(project_id: str) -> dict[str, Any]:
    """
    Alert both parties when a project has been funded but has no submitted milestones
    for > 7 days (funds sitting idle in escrow).
    """
    from backend.app.api.projects import _MILESTONES, _PROJECTS

    project = _PROJECTS.get(project_id)
    if not project or project.get("state") != "FUNDED":
        return {"status": "skipped", "project_id": project_id}

    milestones = _MILESTONES.get(project_id, [])
    any_active = any(
        m.get("state") not in ("DRAFT", "FUNDED")
        for m in milestones
    )
    if any_active:
        return {"status": "skipped", "reason": "has_active_milestones", "project_id": project_id}

    client_id = project.get("client_id", "")
    freelancer_id = project.get("freelancer_id", "")

    try:
        from backend.app.channels.outbox import record_message
        for party_id, role in ((freelancer_id, "freelancer"), (client_id, "client")):
            record_message(
                case_id=project_id,
                channel="email",
                to=party_id,
                subject="ProofPay: escrow funds are waiting",
                body=(
                    "Your ProofPay project has funded escrow but no milestones have been submitted. "
                    "Please log in to review the milestone plan and begin work."
                ),
            )
    except Exception:
        pass

    _audit.log_event("stale_escrow_reminder_sent", {
        "subject": project_id,
        "actor": "scheduler",
        "client_id": client_id,
        "freelancer_id": freelancer_id,
        "timestamp": _clock.utcnow().isoformat(),
    })
    return {"status": "reminder_sent", "project_id": project_id}

