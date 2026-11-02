"""
Escrow Funding Flow.

Coordinates:
  1. Validates project state == PLAN_APPROVED and approvals
  2. Verifies plan_hash matches stored canonical hash
  3. Evaluates proposal against Policy Engine
  4. Calls PayPal gateway to create order
  5. Records intent and returns order_id for client SDK
"""
from __future__ import annotations

import uuid
from typing import Any

from backend.app.audit.writer import log_event
from backend.app.contracts.enums import ActionKind, ProjectState, Verdict
from backend.app.contracts.proposals import Proposal
from backend.app.core.errors import ConflictError, NotFoundError, PolicyViolationError
from backend.app.db.repositories.project_repo import project_repo
from backend.app.paypal.gateway import PayPalGateway
from backend.app.policy.engine import evaluate


async def fund_project(
    project_id: str,
    gateway: PayPalGateway,
    expected_plan_hash: str,
) -> dict[str, Any]:
    project = project_repo.get(project_id)
    if not project:
        raise NotFoundError(f"Project {project_id} not found")

    if project.get("state") != ProjectState.PLAN_APPROVED.value:
        raise ConflictError(
            f"Project must be in PLAN_APPROVED state to fund, currently {project.get('state')}"
        )

    stored_hash = project.get("plan_hash")
    if not stored_hash or stored_hash != expected_plan_hash:
        raise ConflictError(
            f"Plan hash mismatch. Guard check failed (expected {stored_hash}, got {expected_plan_hash})"
        )

    # Policy evaluation
    total_amount = float(project.get("total_amount", 0.0))
    proposal = Proposal(
        agent="escrow",
        subject=project_id,
        action=ActionKind.CREATE_ORDER,
        reason=f"Fund project {project_id}",
        params={
            "amount": total_amount,
            "currency": project.get("currency", "USD"),
            "project_id": project_id,
        },
    )

    decision = evaluate(proposal)
    if decision.verdict != Verdict.ALLOW:
        raise PolicyViolationError(
            f"Funding blocked by policy: {', '.join(decision.blocked_by)}",
            checks=decision.checks,
        )

    # PayPal create order
    request_id = str(uuid.uuid4())
    order = await gateway.create_order(
        amount=total_amount,
        currency=project.get("currency", "USD"),
        request_id=request_id,
        description=f"ProofPay Escrow Project {project_id}",
    )

    order_id = order.get("id") or order.get("order_id")
    project_repo.update(project_id, paypal_order_id=order_id)

    log_event(
        "project_funding_initiated",
        {
            "project_id": project_id,
            "order_id": order_id,
            "amount": total_amount,
            "plan_hash": stored_hash,
        },
    )

    return {
        "project_id": project_id,
        "order_id": order_id,
        "amount": total_amount,
        "currency": project.get("currency", "USD"),
        "status": "order_created",
    }
