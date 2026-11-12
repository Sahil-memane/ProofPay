"""
Projects API router.

Endpoints:
  POST   /projects                       - Create project + stub scoping (single milestone)
  GET    /projects/{id}                  - Get project + milestones
  PATCH  /projects/{id}/milestones/{mid} - Edit milestone (reruns validators, no LLM)
  POST   /projects/{id}/approve          - Per-party approval; locks plan on both
  POST   /projects/{id}/fund             - Create PayPal order (both approved + hash guard)
  POST   /projects/{id}/capture          - Capture PayPal order (optimistic; webhook is truth)
  GET    /projects                       - List projects
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.deps import get_current_user, is_admin

from backend.app.audit import log_event as audit_log
from backend.app.core.errors import ConflictError, NotFoundError, ValidationError
from backend.app.core.logging import get_logger
from backend.app.escrow.plan_hash import compute_plan_hash
from backend.app.paypal import get_gateway

log = get_logger(__name__)
router = APIRouter(tags=["projects"])

# ── In-memory store (replaced by DB repos in Phase 2 full wiring) ────────────
# Using a simple dict for Phase 1 so the API works without full repo wiring
_PROJECTS: dict[str, dict[str, Any]] = {}
_MILESTONES: dict[str, list[dict[str, Any]]] = {}  # project_id → milestones


# ── Request / Response schemas ────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    job_description: str = Field(..., min_length=10)
    total_amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    client_id: str = Field(default="client-1")
    freelancer_id: str = Field(default="freelancer-1")
    deadline: str | None = None  # ISO date string


class EditMilestoneRequest(BaseModel):
    title: str | None = None
    amount: float | None = None
    criteria: list[dict[str, Any]] | None = None
    deadline: str | None = None


class ApproveRequest(BaseModel):
    party: str = Field(..., description="'client' or 'freelancer'")


class FundRequest(BaseModel):
    plan_hash: str = Field(..., description="Must match stored plan_hash")


class CaptureRequest(BaseModel):
    order_id: str


# ── Validators ────────────────────────────────────────────────────────────────

def _validate_milestones(milestones: list[dict[str, Any]], total: float) -> list[str]:
    errors: list[str] = []
    if not milestones:
        errors.append("At least one milestone required")
        return errors

    total_milestone = round(sum(m.get("amount", 0) for m in milestones), 2)
    if abs(total_milestone - round(total, 2)) > 0.01:
        errors.append(
            f"Milestone amounts ({total_milestone}) do not sum to project total ({round(total, 2)})"
        )
    return errors


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/projects", status_code=201)
async def create_project(req: CreateProjectRequest) -> dict[str, Any]:
    """
    Create a project. Calls the Scoping Agent (Dev 2) to generate a
    milestone plan. Falls back to a single-milestone stub if the agent
    is unavailable (langgraph not installed or agent error).
    """
    import asyncio
    from backend.app.agents.scoping import run_scoping

    project_id = str(uuid.uuid4())

    # In fake/demo mode call scoping synchronously -- the stub returns instantly.
    # In rest mode use executor to keep event loop responsive.
    import os as _os
    if _os.environ.get('PAYPAL_EXEC_MODE', 'fake') == 'fake':
        scoping_result = run_scoping(
            project_id=project_id,
            job_description=req.job_description,
            total_amount=req.total_amount,
            currency=req.currency,
            client_id=req.client_id,
            freelancer_id=req.freelancer_id,
            deadline=req.deadline,
        )
    else:
        loop = asyncio.get_event_loop()
        scoping_result = await loop.run_in_executor(
            None,
            lambda: run_scoping(
                project_id=project_id,
                job_description=req.job_description,
                total_amount=req.total_amount,
                currency=req.currency,
                client_id=req.client_id,
                freelancer_id=req.freelancer_id,
                deadline=req.deadline,
            ),
        )

    project: dict[str, Any] = {
        "id": project_id,
        "state": "DRAFT",
        "plan_hash": None,
        "total_amount": req.total_amount,
        "currency": req.currency,
        "client_id": req.client_id,
        "freelancer_id": req.freelancer_id,
        "client_approved": False,
        "freelancer_approved": False,
        "paypal_order_id": None,
        "paypal_capture_id": None,
        "job_description": req.job_description,
        "deadline": req.deadline,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scoping_status": scoping_result.status,
        "clarification_questions": scoping_result.clarification_questions,
    }

    _PROJECTS[project_id] = project
    _MILESTONES[project_id] = scoping_result.milestones

    audit_log("project_created", {
        "subject": project_id,
        "actor": "system",
        "project_id": project_id,
        "total_amount": req.total_amount,
        "currency": req.currency,
        "scoping_status": scoping_result.status,
        "milestone_count": len(scoping_result.milestones),
    })

    return {
        "project": project,
        "milestones": scoping_result.milestones,
        "scoping_status": scoping_result.status,
        "clarification_questions": scoping_result.clarification_questions,
    }


@router.get("/projects")
async def list_projects(
    current_user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    projects_map = {}
    try:
        from backend.app.db.repositories.project_repo import project_repo
        for p in project_repo.list_all():
            projects_map[p["id"]] = p
    except Exception:
        pass
    for pid, p in _PROJECTS.items():
        projects_map[pid] = p

    all_projects = list(projects_map.values())
    if is_admin(current_user):
        return all_projects

    cid = current_user.get("customer_id")
    if not cid:
        return []

    return [
        p for p in all_projects
        if p.get("client_id") == cid or p.get("freelancer_id") == cid
    ]


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    project = _PROJECTS.get(project_id)
    milestones = _MILESTONES.get(project_id, [])
    if not project:
        try:
            from backend.app.db.repositories.project_repo import project_repo
            project = project_repo.get(project_id)
            if project:
                from backend.app.db.repositories.milestone_repo import milestone_repo
                milestones = milestone_repo.list_for_project(project_id)
        except Exception:
            pass
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    if not is_admin(current_user):
        cid = current_user.get("customer_id")
        if not cid or (project.get("client_id") != cid and project.get("freelancer_id") != cid):
            raise HTTPException(status_code=403, detail="Not authorized to view this project")

    return {"project": project, "milestones": milestones}


@router.patch("/projects/{project_id}/milestones/{milestone_id}")
async def edit_milestone(
    project_id: str,
    milestone_id: str,
    req: EditMilestoneRequest,
) -> dict[str, Any]:
    project = _PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.get("state") not in ("DRAFT",):
        raise HTTPException(status_code=409, detail="Cannot edit milestone after plan approval")

    milestones = _MILESTONES.get(project_id, [])
    milestone = next((m for m in milestones if m["id"] == milestone_id), None)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    if req.title is not None:
        milestone["title"] = req.title
    if req.amount is not None:
        milestone["amount"] = req.amount
    if req.criteria is not None:
        milestone["criteria"] = req.criteria
    if req.deadline is not None:
        milestone["deadline"] = req.deadline

    # Rerun validators
    errors = _validate_milestones(milestones, project["total_amount"])
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    # Reset approvals — plan changed
    project["client_approved"] = False
    project["freelancer_approved"] = False
    project["plan_hash"] = None

    return {"milestone": milestone, "validation_errors": []}


@router.post("/projects/{project_id}/approve")
async def approve_project(project_id: str, req: ApproveRequest) -> dict[str, Any]:
    project = _PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.get("state") not in ("DRAFT", "PLAN_APPROVED"):
        raise HTTPException(status_code=409, detail="Project not in approvable state")

    milestones = _MILESTONES.get(project_id, [])
    errors = _validate_milestones(milestones, project["total_amount"])
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    if req.party == "client":
        project["client_approved"] = True
    elif req.party == "freelancer":
        project["freelancer_approved"] = True
    else:
        raise HTTPException(status_code=400, detail="party must be 'client' or 'freelancer'")

    # Both approved → lock the plan
    if project["client_approved"] and project["freelancer_approved"]:
        plan_hash = compute_plan_hash(milestones)
        project["plan_hash"] = plan_hash
        project["state"] = "PLAN_APPROVED"
        audit_log("plan_approved", {
            "subject": project_id,
            "actor": req.party,
            "plan_hash": plan_hash,
        })

    return {"project": project, "plan_hash": project.get("plan_hash")}


@router.post("/projects/{project_id}/fund")
async def fund_project(project_id: str, req: FundRequest) -> dict[str, Any]:
    """
    Guard: both approvals must exist and plan_hash must match.
    Creates a PayPal Orders v2 order; returns order_id for JS SDK.
    """
    project = _PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.get("state") != "PLAN_APPROVED":
        raise HTTPException(status_code=409, detail="Project must be in PLAN_APPROVED state to fund")

    if not (project.get("client_approved") and project.get("freelancer_approved")):
        raise HTTPException(status_code=403, detail="Both parties must approve before funding")

    stored_hash = project.get("plan_hash")
    if stored_hash != req.plan_hash:
        raise HTTPException(
            status_code=403,
            detail=f"plan_hash mismatch — expected {stored_hash!r}, got {req.plan_hash!r}",
        )

    gateway = get_gateway()
    request_id = f"fund-{project_id}"

    try:
        order = await gateway.create_order(
            amount=project["total_amount"],
            currency=project.get("currency", "USD"),
            request_id=request_id,
            description=f"ProofPay escrow for project {project_id}",
        )
    except Exception as exc:
        log.error("PayPal create_order failed for project %s: %s", project_id, exc)
        raise HTTPException(status_code=502, detail=f"PayPal error: {exc}")

    order_id = order.get("id", "")
    project["paypal_order_id"] = order_id

    audit_log("escrow_order_created", {
        "subject": project_id,
        "actor": "system",
        "order_id": order_id,
        "amount": project["total_amount"],
    })

    return {
        "order_id": order_id,
        "project_id": project_id,
        "approval_url": next(
            (lnk["href"] for lnk in order.get("links", []) if lnk.get("rel") == "approve"),
            None,
        ),
    }


@router.post("/projects/{project_id}/capture")
async def capture_project(project_id: str, req: CaptureRequest) -> dict[str, Any]:
    """
    Optimistic capture — calls PayPal capture and returns immediately.
    The FUNDED state transition is driven by the capture webhook (source of truth).
    """
    project = _PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    gateway = get_gateway()
    request_id = f"capture-{project_id}"

    try:
        capture = await gateway.capture_order(
            order_id=req.order_id,
            request_id=request_id,
        )
    except Exception as exc:
        log.error("PayPal capture_order failed for project %s: %s", project_id, exc)
        raise HTTPException(status_code=502, detail=f"PayPal error: {exc}")

    audit_log("capture_requested", {
        "subject": project_id,
        "actor": "client",
        "order_id": req.order_id,
        "capture_id": capture.get("id"),
    })

    return {
        "capture_id": capture.get("id"),
        "status": capture.get("status"),
        "project_id": project_id,
        "note": "Project will move to FUNDED once the capture webhook is received and verified.",
    }
