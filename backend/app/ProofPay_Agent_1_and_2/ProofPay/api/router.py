"""Modular FastAPI Router for ProofPay Scoping Agent.

Exposes REST endpoints for project intake, clarification submission,
deterministic plan edits, approval collection, and audit query.
"""

from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ProofPay.agents.scoping_agent.graph import ScopingAgentRunner
from ProofPay.agents.scoping_agent.schemas import (
    ProjectInputSchema,
    PlanEditRequestSchema,
    ApprovalActionSchema,
)
from ProofPay.agents.scoping_agent.criteria_library import CRITERIA_REGISTRY
from ProofPay.services.audit_service import audit_service
from ProofPay.services.database import db

router = APIRouter(prefix="/api/v1/scoping", tags=["ProofPay Scoping Agent"])

# Global runner uses SQLite checkpoints when the optional SQLite checkpointer is installed.
scoping_runner = ScopingAgentRunner()


class ClarificationInputSchema(BaseModel):
    answers: Dict[str, str] = Field(
        ...,
        description="Map each exact pending clarification question to its own answer.",
    )


@router.get("/criteria", summary="List Predefined Criteria Library")
def list_criteria():
    """Return all predefined acceptance criteria available to the platform."""
    return {
        "criteria": [
            {
                "type": c.type_name,
                "description": c.description,
                "is_hard": c.is_hard,
                "required_params": sorted(c.required_params),
                "example_params": c.example_params,
            }
            for c in CRITERIA_REGISTRY.values()
        ]
    }


@router.post("/projects", summary="Submit Project for Scoping")
def submit_project(payload: ProjectInputSchema, thread_id: Optional[str] = None):
    """Ingest client project details, run pre-validation, clarity check, and generate milestones."""
    t_id = thread_id or f"proj_{uuid.uuid4().hex}"
    try:
        state = scoping_runner.start_project(payload.model_dump(), thread_id=t_id)
        return {"thread_id": t_id, "state": state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{thread_id}/clarification", summary="Submit Clarification Answers")
def submit_clarification(thread_id: str, payload: ClarificationInputSchema):
    """Provide answers to clarification questions and resume milestone generation."""
    try:
        state = scoping_runner.submit_clarification(thread_id=thread_id, clarification_answers=payload.answers)
        return {"thread_id": thread_id, "state": state}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{thread_id}/edit", summary="Submit Plan Edit (Deterministic)")
def submit_plan_edit(thread_id: str, payload: PlanEditRequestSchema):
    """Submit a manual edit. Uses deterministic Python validation only (NO LLM CALL)."""
    try:
        current = scoping_runner.get_state(thread_id=thread_id)
        if not current:
            raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found.")
        if payload.editor_id not in (current.get("client_id"), current.get("freelancer_id")):
            raise HTTPException(status_code=403, detail="Editor is not a participant in this project.")
        milestones_raw = [m.model_dump() for m in payload.milestones]
        state = scoping_runner.submit_edit(thread_id=thread_id, edited_milestones=milestones_raw)
        return {"thread_id": thread_id, "state": state}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{thread_id}/approval", summary="Submit Client or Freelancer Approval")
def submit_approval(thread_id: str, payload: ApprovalActionSchema):
    """Record an independent approval. If both client and freelancer approve, locks the plan."""
    try:
        state = scoping_runner.submit_approval(
            thread_id=thread_id,
            user_id=payload.user_id,
            role=payload.role,
            approved=payload.approved,
            comment=payload.comment,
        )
        if state.get("error_message"):
            message = state["error_message"]
            status_code = 403 if "identity does not match" in message.lower() else 409
            raise HTTPException(status_code=status_code, detail=message)
        return {"thread_id": thread_id, "state": state}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{thread_id}", summary="Get Project Scoping State")
def get_project_state(thread_id: str):
    """Fetch current state snapshot for a given scoping thread."""
    state = scoping_runner.get_state(thread_id=thread_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found.")
    project_record = db.get_project(state.get("project_id")) if state.get("project_id") else None
    return {"thread_id": thread_id, "state": state, "persisted_project": project_record}


@router.get("/projects/{thread_id}/audit", summary="Get Project Audit Trail")
def get_project_audit(thread_id: str):
    """Retrieve immutable audit history for a workflow thread's actual project ID."""
    state = scoping_runner.get_state(thread_id=thread_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found.")
    project_id = state.get("project_id")
    events = audit_service.get_events(project_id=project_id)
    return {"thread_id": thread_id, "project_id": project_id, "audit_events": events}


