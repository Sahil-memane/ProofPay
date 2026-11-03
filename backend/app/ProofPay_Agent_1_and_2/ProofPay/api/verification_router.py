"""REST API for ProofPay Agent 2 milestone verification."""
from uuid import uuid4
from fastapi import APIRouter, HTTPException
from ProofPay.agents.verification_agent.schemas import MilestoneSubmissionSchema
from ProofPay.agents.verification_agent.graph import verification_runner
from ProofPay.services.database import db

router = APIRouter(prefix="/api/v1/verification", tags=["ProofPay Verification Agent"])


@router.post("/projects/{project_id}/milestones/{milestone_id}/submissions",
             summary="Submit milestone work for Agent 2 verification")
def submit_milestone_submission(project_id: str, milestone_id: str, payload: MilestoneSubmissionSchema):
    project = db.get_project(project_id)
    if not project or project.get("status") != "PLAN_APPROVED":
        raise HTTPException(status_code=409, detail="Agent 1 must approve and lock the plan before milestone verification.")
    if payload.freelancer_id != project.get("freelancer_id"):
        raise HTTPException(status_code=403, detail="Only the assigned freelancer may submit milestone work.")
    if not any(m.get("id") == milestone_id for m in project.get("milestones", [])):
        raise HTTPException(status_code=404, detail="Milestone not found in the locked plan.")
    submission_id = f"sub_{uuid4().hex}"
    state = verification_runner.submit({
        "submission_id": submission_id,
        "project_id": project_id,
        "milestone_id": milestone_id,
        "freelancer_id": payload.freelancer_id,
        "submission": payload.model_dump(mode="json"),
    })
    if state.get("decision") == "BLOCKED":
        raise HTTPException(status_code=409, detail=state.get("explanation", "Verification blocked."))
    return {"submission_id": submission_id, "verification": state.get("verification_result", {
        "decision": state.get("decision"),
        "verification_score": state.get("verification_score"),
        "criterion_results": state.get("criterion_results", []),
        "explanation": state.get("explanation"),
    })}


@router.get("/projects/{project_id}/milestones/{milestone_id}/submissions",
            summary="List milestone verification submissions")
def list_milestone_submissions(project_id: str, milestone_id: str):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if not any(m.get("id") == milestone_id for m in project.get("milestones", [])):
        raise HTTPException(status_code=404, detail="Milestone not found in project.")
    return {"project_id": project_id, "milestone_id": milestone_id,
            "submissions": db.list_verification_submissions(project_id, milestone_id)}
