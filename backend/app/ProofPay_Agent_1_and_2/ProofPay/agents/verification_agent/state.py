from typing import Any, Dict, List, TypedDict


class VerificationState(TypedDict, total=False):
    submission_id: str
    project_id: str
    milestone_id: str
    freelancer_id: str
    submission: Dict[str, Any]
    project: Dict[str, Any]
    milestone: Dict[str, Any]
    criterion_results: List[Dict[str, Any]]
    verification_score: float
    decision: str
    explanation: str
    error: str
