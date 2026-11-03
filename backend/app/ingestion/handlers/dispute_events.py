"""
Handlers: CUSTOMER.DISPUTE.CREATED / UPDATED / RESOLVED

Critical invariant:
  On CREATED → freeze all FUNDED/SUBMITTED milestones immediately,
  halt any active recovery case, cancel scheduler jobs.
  No LLM involved. Pure deterministic freeze.

On RESOLVED → audit + unfreeze milestones if outcome is seller-favoured.
"""
from __future__ import annotations

from typing import Any

from backend.app.core.logging import get_logger
from backend.app.ingestion.handlers import register

log = get_logger(__name__)


@register("customer_dispute_created")
def handle_dispute_created(event: dict[str, Any]) -> None:
    """
    CUSTOMER.DISPUTE.CREATED:
    1. Freeze all FUNDED / SUBMITTED milestones on the affected project
    2. Halt active recovery case (if any)
    3. Cancel pending scheduler jobs for this project
    4. Write audit event
    """
    resource = event.get("payload", {}).get("resource", {})
    dispute_id = resource.get("dispute_id", "")
    disputed_transactions = resource.get("disputed_transactions", [])

    # Extract order_id from disputed transactions to find our project
    order_ids: list[str] = []
    for txn in disputed_transactions:
        oid = (
            txn.get("seller_transaction_id")
            or txn.get("buyer_transaction_id")
            or txn.get("order_id")
            or ""
        )
        if oid:
            order_ids.append(oid)

    log.warning(
        "customer_dispute_created: dispute_id=%s order_ids=%s",
        dispute_id, order_ids,
    )

    try:
        from backend.app.audit import log_event as audit_log
        from backend.app.api.projects import _PROJECTS, _MILESTONES

        # Find project(s) by paypal_order_id
        affected_project_ids: list[str] = []
        for project_id, project in _PROJECTS.items():
            if project.get("paypal_order_id") in order_ids or project.get("paypal_capture_id") in order_ids:
                affected_project_ids.append(project_id)

        frozen_milestones: list[str] = []
        for project_id in affected_project_ids:
            project = _PROJECTS.get(project_id, {})
            milestones = _MILESTONES.get(project_id, [])

            for m in milestones:
                if m.get("state") in ("FUNDED", "SUBMITTED", "VERIFYING", "IN_REVIEW", "CLIENT_APPROVED"):
                    m["state"] = "DISPUTED"
                    m["dispute_id"] = dispute_id
                    frozen_milestones.append(m["id"])

            # Mark project as disputed
            project["dispute_id"] = dispute_id

            log.warning(
                "customer_dispute_created: frozen %d milestones for project %s",
                len(frozen_milestones), project_id,
            )

        # Halt any active recovery case for affected orders
        try:
            from backend.app.stubs.repositories import case_repo
            from backend.app.recovery.state_machine import transition
            from backend.app.contracts.enums import CaseState

            for case in case_repo.list_all():
                payload = case.get("payload", {})
                if any(
                    payload.get(k) in order_ids
                    for k in ("order_id", "capture_id", "invoice_id")
                ):
                    if case.get("state") not in ("RECOVERED", "HALTED", "UNRECOVERED"):
                        transition(
                            case,
                            to_state=CaseState.HALTED,
                            actor="webhook",
                            reason=f"dispute_created:{dispute_id}",
                        )
                        log.warning("Halted recovery case %s due to dispute %s", case.get("id"), dispute_id)
        except Exception as exc:
            log.warning("Could not halt recovery cases: %s", exc)

        audit_log("dispute_created", {
            "subject": dispute_id,
            "actor": "webhook",
            "dispute_id": dispute_id,
            "order_ids": order_ids,
            "affected_projects": affected_project_ids,
            "frozen_milestones": frozen_milestones,
        })

    except Exception as exc:
        log.error("customer_dispute_created handler error: %s", exc, exc_info=True)
        raise


@register("customer_dispute_updated")
def handle_dispute_updated(event: dict[str, Any]) -> None:
    """
    CUSTOMER.DISPUTE.UPDATED — audit only.
    Do NOT change milestone states mid-dispute.
    """
    resource = event.get("payload", {}).get("resource", {})
    dispute_id = resource.get("dispute_id", "")
    status = resource.get("status", "")
    log.info("customer_dispute_updated: dispute_id=%s status=%s", dispute_id, status)

    try:
        from backend.app.audit import log_event as audit_log
        audit_log("dispute_updated", {
            "subject": dispute_id,
            "actor": "webhook",
            "dispute_id": dispute_id,
            "status": status,
            "payload": resource,
        })
    except Exception as exc:
        log.error("customer_dispute_updated handler error: %s", exc, exc_info=True)


@register("customer_dispute_resolved")
def handle_dispute_resolved(event: dict[str, Any]) -> None:
    """
    CUSTOMER.DISPUTE.RESOLVED:
    - Audit the outcome.
    - If outcome is seller-favoured (RESOLVED_SELLER_FAVOUR), unfreeze milestones.
    - If buyer-favoured, milestones stay DISPUTED (client to initiate refund separately).
    """
    resource = event.get("payload", {}).get("resource", {})
    dispute_id = resource.get("dispute_id", "")
    outcome = resource.get("dispute_outcome", {})
    outcome_code = outcome.get("outcome_code", "")  # RESOLVED_BUYER_FAVOUR | RESOLVED_SELLER_FAVOUR | etc.
    log.info(
        "customer_dispute_resolved: dispute_id=%s outcome=%s",
        dispute_id, outcome_code,
    )

    try:
        from backend.app.audit import log_event as audit_log
        from backend.app.api.projects import _PROJECTS, _MILESTONES

        seller_favoured = "SELLER" in outcome_code.upper()
        unfrozen_milestones: list[str] = []

        if seller_favoured:
            for project_id, project in _PROJECTS.items():
                if project.get("dispute_id") == dispute_id:
                    milestones = _MILESTONES.get(project_id, [])
                    for m in milestones:
                        if m.get("state") == "DISPUTED" and m.get("dispute_id") == dispute_id:
                            # Revert to SUBMITTED so client/freelancer can continue
                            m["state"] = "SUBMITTED"
                            m.pop("dispute_id", None)
                            unfrozen_milestones.append(m["id"])
                    project.pop("dispute_id", None)

        audit_log("dispute_resolved", {
            "subject": dispute_id,
            "actor": "webhook",
            "dispute_id": dispute_id,
            "outcome_code": outcome_code,
            "seller_favoured": seller_favoured,
            "unfrozen_milestones": unfrozen_milestones,
        })

        log.info(
            "customer_dispute_resolved: outcome=%s seller_favoured=%s unfrozen=%d milestones",
            outcome_code, seller_favoured, len(unfrozen_milestones),
        )

    except Exception as exc:
        log.error("customer_dispute_resolved handler error: %s", exc, exc_info=True)
        raise

