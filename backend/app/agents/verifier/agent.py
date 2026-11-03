"""
Verifier Agent adapter.

Wraps Dev 2's VerificationAgentRunner (ProofPay_Agent_1_and_2) so it can
be called from our submissions API without import boundary violations.

The Dev2 verifier calls ProofPay.services.database.db — we inject a thin
shim so it reads from our in-memory / DB project store instead.

Import invariant: NO imports from paypal/ or executor/ here.
"""
from __future__ import annotations

import logging
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ── Make the Dev2 package importable ─────────────────────────────────────────
_DEV2_ROOT = Path(__file__).resolve().parents[3] / "ProofPay_Agent_1_and_2"
if str(_DEV2_ROOT) not in sys.path:
    sys.path.insert(0, str(_DEV2_ROOT))


@dataclass
class VerificationResult:
    """Structured output from the verifier agent."""

    submission_id: str
    project_id: str
    milestone_id: str
    decision: str          # RELEASE_PROPOSAL | CLIENT_REVIEW_REQUIRED | RESUBMISSION_REQUIRED | BLOCKED
    score: float           # 0.0 – 1.0
    explanation: str
    criterion_results: list[dict[str, Any]] = field(default_factory=list)
    plan_hash: str | None = None
    error: str | None = None


class _ProjectDBShim:
    """
    Thin shim that satisfies the interface expected by Dev2's
    ``ProofPay.services.database.db``.

    Dev2 nodes call:
        db.get_project(project_id)
        db.get_emitted_events(event_type)
        db.save_verification_submission(...)

    We satisfy these using our in-memory project store (projects.py) and
    our audit writer.
    """

    def __init__(
        self,
        project: dict[str, Any],
        milestones: list[dict[str, Any]],
        plan_hash: str | None,
    ) -> None:
        self._project = project
        self._milestones = milestones
        self._plan_hash = plan_hash

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        if self._project.get("id") != project_id:
            return None
        # Dev2 expects 'status' not 'state', and milestones embedded
        p = dict(self._project)
        p["status"] = p.get("state", "DRAFT")
        p["plan_hash"] = self._plan_hash or p.get("plan_hash")
        p["milestones"] = self._milestones
        # Dev2 checks freelancer_id on project
        return p

    def get_emitted_events(self, event_type: str) -> list[dict[str, Any]]:  # noqa: ARG002
        """Return a synthetic plan.approved event so the verifier unlocks."""
        if self._plan_hash:
            return [
                {
                    "payload": {
                        "project_id": self._project.get("id"),
                        "plan_hash": self._plan_hash,
                    }
                }
            ]
        return []

    def save_verification_submission(  # noqa: PLR0913
        self,
        submission_id: str,
        project_id: str,
        milestone_id: str,
        freelancer_id: str,
        decision: str,
        result: dict[str, Any],
    ) -> None:
        """Delegate persistence to our audit log."""
        try:
            from backend.app.audit import log_event as audit_log
            audit_log("milestone_verified", {
                "subject": milestone_id,
                "actor": "verification_agent",
                "submission_id": submission_id,
                "project_id": project_id,
                "milestone_id": milestone_id,
                "freelancer_id": freelancer_id,
                "decision": decision,
                "score": result.get("verification_score"),
            })
        except Exception as exc:  # pragma: no cover
            log.warning("audit log failed in verifier shim: %s", exc)


class _AuditServiceShim:
    """Satisfies ProofPay.services.audit_service.audit_service.record_event."""

    def record_event(self, *, project_id: str, event_type: str, actor: str, details: Any) -> None:
        try:
            from backend.app.audit import log_event as audit_log
            audit_log(event_type.lower(), {
                "subject": project_id,
                "actor": actor,
                "details": details,
            })
        except Exception as exc:  # pragma: no cover
            log.warning("audit_service shim error: %s", exc)


def run_verification(
    *,
    submission_id: str,
    project_id: str,
    milestone_id: str,
    freelancer_id: str,
    submission: dict[str, Any],
    project: dict[str, Any],
    milestones: list[dict[str, Any]],
    plan_hash: str | None = None,
) -> VerificationResult:
    """
    Run the verification agent for a milestone submission.

    Falls back to a permissive stub (CLIENT_REVIEW_REQUIRED) if the
    agent package is unavailable.
    """
    try:
        import ProofPay.services.database as _db_module  # type: ignore[import]
        import ProofPay.services.audit_service as _audit_module  # type: ignore[import]

        # Inject shims so Dev2 nodes read our data
        _db_module.db = _ProjectDBShim(project, milestones, plan_hash)
        _audit_module.audit_service = _AuditServiceShim()

        from ProofPay.agents.verification_agent.graph import VerificationAgentRunner  # type: ignore[import]

        runner = VerificationAgentRunner()
        payload: dict[str, Any] = {
            "submission_id": submission_id,
            "project_id": project_id,
            "milestone_id": milestone_id,
            "freelancer_id": freelancer_id,
            "submission": submission,
        }
        state = runner.submit(payload)

        return VerificationResult(
            submission_id=submission_id,
            project_id=project_id,
            milestone_id=milestone_id,
            decision=state.get("decision", "CLIENT_REVIEW_REQUIRED"),
            score=float(state.get("verification_score", 0.0)),
            explanation=state.get("explanation", ""),
            criterion_results=state.get("criterion_results", []),
            plan_hash=plan_hash,
            error=state.get("error"),
        )

    except ImportError as exc:
        log.warning("Verifier agent not available (%s) — using stub fallback", exc)
        return _stub_verification(submission_id, project_id, milestone_id)
    except Exception as exc:
        log.error("Verifier agent failed: %s", exc, exc_info=True)
        return _stub_verification(submission_id, project_id, milestone_id, error=str(exc))


def _stub_verification(
    submission_id: str,
    project_id: str,
    milestone_id: str,
    error: str | None = None,
) -> VerificationResult:
    """Stub verifier: flags everything for human review."""
    return VerificationResult(
        submission_id=submission_id,
        project_id=project_id,
        milestone_id=milestone_id,
        decision="CLIENT_REVIEW_REQUIRED",
        score=0.0,
        explanation="Verification agent unavailable — flagged for manual client review.",
        error=error,
    )

