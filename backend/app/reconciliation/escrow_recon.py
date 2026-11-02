"""
Escrow Milestone Reconciliation Checks (Step 12).

Provides:
  - pre_release_check(milestone): verifies that a funding capture exists for the full amount.
  - post_release_check(milestone): verifies that the milestone payout appears in records.
Mismatches are recorded in an audited exception list.
"""
from __future__ import annotations

from typing import Any

from backend.app.reconciliation.normalizer import ReconRecord, load_all_recon_records
from backend.app.stubs import audit

_EXCEPTION_LIST: list[dict[str, Any]] = []


def clear_exception_list() -> None:
    """Clear recorded reconciliation exceptions."""
    _EXCEPTION_LIST.clear()


def get_exception_list() -> list[dict[str, Any]]:
    """Return all recorded reconciliation exceptions."""
    return list(_EXCEPTION_LIST)


def pre_release_check(
    milestone: dict[str, Any],
    records: list[ReconRecord] | None = None,
) -> bool:
    """
    Verify funding capture exists for the full milestone amount before release.
    A missing or incomplete capture blocks the pre-release check and logs to exception list.
    """
    m_id = str(milestone.get("milestone_id") or milestone.get("id", "UNKNOWN-MILESTONE"))
    proj_id = str(milestone.get("project_id", ""))
    target_amount = float(milestone.get("amount_usd") or milestone.get("amount", 0.0))
    target_currency = str(milestone.get("currency", "USD")).upper()
    capture_id = str(milestone.get("funding_capture_id") or milestone.get("capture_id", ""))

    all_records = records if records is not None else load_all_recon_records()

    # Search for matching capture record:
    # Must match project/milestone/capture_id, currency, and full amount (within 0.01 tolerance)
    found_capture = False
    matching_amount = 0.0

    for r in all_records:
        if r.currency.upper() != target_currency:
            continue

        id_match = (
            (capture_id and r.external_id == capture_id)
            or (m_id and (m_id in r.reference or m_id in r.external_id))
            or (proj_id and (proj_id in r.reference or proj_id in r.external_id))
        )

        amount_match = abs(r.amount - target_amount) <= 0.01

        if id_match and amount_match:
            found_capture = True
            matching_amount = r.amount
            break

    if found_capture:
        audit.log_event("escrow_pre_release_check_passed", {
            "milestone_id": m_id,
            "project_id": proj_id,
            "amount_usd": target_amount,
        })
        return True
    else:
        exception_entry = {
            "milestone_id": m_id,
            "project_id": proj_id,
            "check": "pre_release_check",
            "reason": "missing_or_partial_funding_capture",
            "expected_amount": target_amount,
            "captured_amount": matching_amount,
            "currency": target_currency,
        }
        _EXCEPTION_LIST.append(exception_entry)
        audit.log_event("escrow_pre_release_check_blocked", exception_entry)
        return False


def post_release_check(
    milestone: dict[str, Any],
    records: list[ReconRecord] | None = None,
) -> bool:
    """
    Verify milestone payout appears in records after release.
    A missing payout entry sends a mismatch entry to the exception list.
    """
    m_id = str(milestone.get("milestone_id") or milestone.get("id", "UNKNOWN-MILESTONE"))
    proj_id = str(milestone.get("project_id", ""))
    target_amount = float(milestone.get("amount_usd") or milestone.get("amount", 0.0))
    target_currency = str(milestone.get("currency", "USD")).upper()
    payout_id = str(milestone.get("payout_id", ""))

    all_records = records if records is not None else load_all_recon_records()

    found_payout = False
    for r in all_records:
        if r.currency.upper() != target_currency:
            continue

        id_match = (
            (payout_id and r.external_id == payout_id)
            or (m_id and (m_id in r.reference or m_id in r.external_id))
            or (proj_id and (proj_id in r.reference or proj_id in r.external_id))
        )
        amount_match = abs(r.amount - target_amount) <= 0.05

        if id_match and amount_match:
            found_payout = True
            break

    if found_payout:
        audit.log_event("escrow_post_release_check_passed", {
            "milestone_id": m_id,
            "project_id": proj_id,
            "amount_usd": target_amount,
        })
        return True
    else:
        exception_entry = {
            "milestone_id": m_id,
            "project_id": proj_id,
            "check": "post_release_check",
            "reason": "payout_not_found_in_records",
            "expected_amount": target_amount,
            "currency": target_currency,
        }
        _EXCEPTION_LIST.append(exception_entry)
        audit.log_event("escrow_post_release_check_mismatch", exception_entry)
        return False

