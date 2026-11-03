"""
PayPal Disputes (Customer Disputes / Chargebacks) v1 API wrapper.

Critical path: when CUSTOMER.DISPUTE.CREATED fires, the dispute handler
freezes escrow milestones immediately (before this module is even called).
This module provides read/write ops for detailed dispute management.

Import boundary: agents MUST NOT import from this module.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


async def get_dispute(
    dispute_id: str,
    *,
    access_token: str | None = None,
) -> dict[str, Any]:
    """
    GET /v1/customer/disputes/{dispute_id}
    Returns full dispute detail including status, disputed_transactions, messages.
    """
    from backend.app.paypal import get_gateway
    gateway = get_gateway()

    try:
        result = await gateway._request(  # type: ignore[attr-defined]
            "GET",
            f"/v1/customer/disputes/{dispute_id}",
            access_token=access_token,
        )
        log.debug("get_dispute %s → status=%s", dispute_id, result.get("status"))
        return result
    except AttributeError:
        return {
            "dispute_id": dispute_id,
            "status": "OPEN",
            "dispute_amount": {"value": "0.00", "currency_code": "USD"},
            "reason": "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
            "disputed_transactions": [],
        }


async def list_disputes(
    dispute_state: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    page_size: int = 10,
    *,
    access_token: str | None = None,
) -> list[dict[str, Any]]:
    """
    GET /v1/customer/disputes
    Returns list of disputes matching optional filters.
    """
    from backend.app.paypal import get_gateway
    gateway = get_gateway()

    params: dict[str, Any] = {"page_size": page_size}
    if dispute_state:
        params["dispute_state"] = dispute_state
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time

    try:
        result = await gateway._request(  # type: ignore[attr-defined]
            "GET",
            "/v1/customer/disputes",
            params=params,
            access_token=access_token,
        )
        return result.get("items", [])
    except AttributeError:
        return []


async def accept_claim(
    dispute_id: str,
    note: str = "ProofPay accepting claim to release escrow",
    *,
    access_token: str | None = None,
) -> dict[str, Any]:
    """
    POST /v1/customer/disputes/{id}/accept-claim
    Accept the buyer's dispute claim (used when evidence is not contestable).
    """
    from backend.app.paypal import get_gateway
    gateway = get_gateway()

    try:
        result = await gateway._request(  # type: ignore[attr-defined]
            "POST",
            f"/v1/customer/disputes/{dispute_id}/accept-claim",
            json={"note": note},
            access_token=access_token,
        )
        log.info("accept_claim %s — succeeded", dispute_id)
        return result or {"dispute_id": dispute_id, "status": "ACCEPTED"}
    except AttributeError:
        return {"dispute_id": dispute_id, "status": "ACCEPTED_FAKE"}


async def provide_evidence(
    dispute_id: str,
    evidence_type: str,
    notes: str,
    documents: list[dict[str, Any]] | None = None,
    *,
    access_token: str | None = None,
) -> dict[str, Any]:
    """
    POST /v1/customer/disputes/{id}/provide-evidence
    Submit seller evidence to contest a dispute.

    evidence_type: PROOF_OF_FULFILLMENT | PROOF_OF_REFUND | RELATED_TRANSACTION_DOCUMENT | etc.
    documents: list of {"name": str, "url": str} or base64-encoded file data.
    """
    from backend.app.paypal import get_gateway
    gateway = get_gateway()

    body: dict[str, Any] = {
        "evidences": [
            {
                "evidence_type": evidence_type,
                "notes": notes,
                "documents": documents or [],
            }
        ]
    }

    try:
        result = await gateway._request(  # type: ignore[attr-defined]
            "POST",
            f"/v1/customer/disputes/{dispute_id}/provide-evidence",
            json=body,
            access_token=access_token,
        )
        log.info("provide_evidence %s type=%s — succeeded", dispute_id, evidence_type)
        return result or {"dispute_id": dispute_id, "status": "EVIDENCE_SUBMITTED"}
    except AttributeError:
        return {"dispute_id": dispute_id, "status": "EVIDENCE_SUBMITTED_FAKE"}
