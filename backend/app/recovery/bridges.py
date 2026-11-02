"""
Bridge layer for ProofPay Recovery (Step 12).

Provides:
  - Repository, Policy, Audit, and Clock bridges
  - Handlers for funding.failed and instalment.failed (opens case of type escrow_funding)
  - State change listener:
      on RECOVERED -> publishes funding.resumed
      on UNRECOVERED -> publishes project.flagged_for_freelancer
  - Open case for overdue invoice outside escrow with an escrow suggestion line and intake link:
      /intake?prefill=<case_id>
"""
from __future__ import annotations

import uuid
from typing import Any

from backend.app.recovery.constants import (
    CASE_TYPE_ESCROW_FUNDING,
    CASE_TYPE_OVERDUE_INVOICE,
    EVENT_FUNDING_FAILED,
    EVENT_FUNDING_RESUMED,
    EVENT_INSTALMENT_FAILED,
    EVENT_PROJECT_FLAGGED,
)
from backend.app.recovery.state_machine import create_case_from_trigger, transition
from backend.app.stubs import audit, clock, policy, repositories
from backend.app.stubs.contracts_stub import CaseState, PolicyDecision, Proposal

_PUBLISHED_EVENTS: list[dict[str, Any]] = []


def publish_event(event_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Publish an external domain event (records to audit log and memory)."""
    event_record = {
        "event": event_name,
        "payload": payload,
        "published_at": clock.utcnow().isoformat(),
    }
    _PUBLISHED_EVENTS.append(event_record)
    audit.log_event(event_name, payload)
    return event_record


def get_published_events() -> list[dict[str, Any]]:
    return list(_PUBLISHED_EVENTS)


def clear_published_events() -> None:
    _PUBLISHED_EVENTS.clear()


# ── Escrow Bridge Handlers ───────────────────────────────────────────────────

def handle_funding_failed(
    project_id: str,
    client_id: str,
    amount_usd: float,
    failure_code: str = "funding_failed",
    event_id: str | None = None,
) -> dict[str, Any]:
    """
    Handle funding.failed: opens an escrow_funding case.
    """
    evt_id = event_id or f"evt-ff-{project_id}-{uuid.uuid4().hex[:6]}"
    case = create_case_from_trigger(
        trigger_type="funding_failed",
        event_id=evt_id,
        payload={
            "customer_id": client_id,
            "project_id": project_id,
            "amount_usd": amount_usd,
            "failure_code": failure_code,
            "case_type": CASE_TYPE_ESCROW_FUNDING,
        },
    )
    case["case_type"] = CASE_TYPE_ESCROW_FUNDING
    case["project_id"] = project_id
    repositories.case_repo.update(case["id"], case_type=CASE_TYPE_ESCROW_FUNDING, project_id=project_id)
    return case


def handle_instalment_failed(
    project_id: str,
    milestone_id: str,
    client_id: str,
    amount_usd: float,
    failure_code: str = "instalment_failed",
    event_id: str | None = None,
) -> dict[str, Any]:
    """
    Handle instalment.failed: opens an escrow_funding case for the specific milestone.
    """
    evt_id = event_id or f"evt-inst-{milestone_id}-{uuid.uuid4().hex[:6]}"
    case = create_case_from_trigger(
        trigger_type="funding_failed",
        event_id=evt_id,
        payload={
            "customer_id": client_id,
            "project_id": project_id,
            "milestone_id": milestone_id,
            "amount_usd": amount_usd,
            "failure_code": failure_code,
            "case_type": CASE_TYPE_ESCROW_FUNDING,
        },
    )
    case["case_type"] = CASE_TYPE_ESCROW_FUNDING
    case["project_id"] = project_id
    case["milestone_id"] = milestone_id
    repositories.case_repo.update(
        case["id"],
        case_type=CASE_TYPE_ESCROW_FUNDING,
        project_id=project_id,
        milestone_id=milestone_id,
    )
    return case


def on_escrow_case_state_change(case: dict[str, Any]) -> str | None:
    """
    Lifecycle listener for escrow cases:
      - on RECOVERED: publish funding.resumed
      - on UNRECOVERED: publish project.flagged_for_freelancer
    """
    if case.get("case_type") != CASE_TYPE_ESCROW_FUNDING:
        return None

    state = case.get("state")
    project_id = case.get("project_id") or case.get("payload", {}).get("project_id", "")
    case_id = case.get("id") or case.get("case_id", "")

    if state in (CaseState.RECOVERED, "RECOVERED"):
        publish_event(EVENT_FUNDING_RESUMED, {
            "project_id": project_id,
            "case_id": case_id,
            "client_id": case.get("customer_id"),
        })
        return EVENT_FUNDING_RESUMED

    elif state in (CaseState.UNRECOVERED, "UNRECOVERED"):
        publish_event(EVENT_PROJECT_FLAGGED, {
            "project_id": project_id,
            "case_id": case_id,
            "client_id": case.get("customer_id"),
            "reason": case.get("unrecovered_reason", "funding_unrecovered"),
        })
        return EVENT_PROJECT_FLAGGED

    return None


# ── Overdue Invoice With Escrow Suggestion ─────────────────────────────────────

def open_case_for_overdue_invoice_with_escrow_suggestion(
    invoice_id: str,
    customer_id: str,
    amount_usd: float,
    currency: str = "USD",
    event_id: str | None = None,
) -> dict[str, Any]:
    """
    Open a case for an overdue invoice created outside escrow,
    embedding an escrow suggestion line and an intake link in the notification params.
    """
    evt_id = event_id or f"evt-inv-{invoice_id}"
    case_id = f"CASE-{invoice_id}"

    case = create_case_from_trigger(
        trigger_type="overdue_invoice",
        event_id=evt_id,
        payload={
            "invoice_id": invoice_id,
            "customer_id": customer_id,
            "amount_usd": amount_usd,
            "currency": currency,
            "case_type": CASE_TYPE_OVERDUE_INVOICE,
        },
    )

    actual_case_id = case["id"]
    intake_link = f"/intake?prefill={actual_case_id}"
    suggestion_line = "To protect future project payments with automated milestone escrow, try ProofPay Escrow."

    case["case_type"] = CASE_TYPE_OVERDUE_INVOICE
    case["escrow_suggestion"] = suggestion_line
    case["intake_link"] = intake_link
    case["payload"]["case_type"] = CASE_TYPE_OVERDUE_INVOICE
    case["payload"]["escrow_suggestion"] = suggestion_line
    case["payload"]["intake_link"] = intake_link

    repositories.case_repo.update(
        actual_case_id,
        case_type=CASE_TYPE_OVERDUE_INVOICE,
        escrow_suggestion=suggestion_line,
        intake_link=intake_link,
    )

    audit.log_event("overdue_invoice_case_opened_with_escrow_suggestion", {
        "case_id": actual_case_id,
        "invoice_id": invoice_id,
        "customer_id": customer_id,
        "intake_link": intake_link,
    })

    return case


# ── Bridges ───────────────────────────────────────────────────────────────────

class RepositoryBridge:
    @staticmethod
    def get_case(case_id: str) -> dict[str, Any] | None:
        return repositories.case_repo.get(case_id)

    @staticmethod
    def update_case(case_id: str, **fields: Any) -> dict[str, Any]:
        return repositories.case_repo.update(case_id, **fields)

    @staticmethod
    def list_contacts(case_id: str) -> list[dict[str, Any]]:
        return repositories.contact_repo.list_for_case(case_id)


class PolicyBridge:
    @staticmethod
    def check_proposal(proposal: Proposal) -> PolicyDecision:
        return policy.check(proposal)


class AuditBridge:
    @staticmethod
    def record_event(name: str, payload: dict[str, Any]) -> None:
        audit.log_event(name, payload)


class ClockBridge:
    @staticmethod
    def current_utc() -> str:
        return clock.utcnow().isoformat()
