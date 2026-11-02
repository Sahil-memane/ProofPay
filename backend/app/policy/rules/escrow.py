"""
Policy rules for Escrow domain.
Checks project creation, milestone release, funding, and dispute rules.
"""
from __future__ import annotations

from typing import Any

from backend.app.contracts.enums import ActionKind
from backend.app.contracts.proposals import Proposal
from backend.app.policy import config_loader


def evaluate_escrow_rules(proposal: Proposal) -> tuple[dict[str, bool], list[str]]:
    checks: dict[str, bool] = {}
    blocked: list[str] = []
    params = proposal.params

    max_project_total = config_loader.get_float("max_project_total_usd", 25000.0)
    max_release = config_loader.get_float("max_release_amount_usd", 5000.0)

    amount = float(params.get("amount") or params.get("amount_usd") or 0.0)

    # 1. Action specific checks
    if proposal.action in (ActionKind.CREATE_ORDER, ActionKind.PAYMENT_LINK):
        checks["under_project_cap"] = amount <= max_project_total
        if not checks["under_project_cap"]:
            blocked.append("project_total_exceeds_cap")

    elif proposal.action == ActionKind.PAYOUT:
        checks["under_max_release"] = amount <= max_release
        if not checks["under_max_release"]:
            blocked.append("release_amount_exceeds_cap")

        recipient = params.get("recipient_email") or params.get("recipient")
        checks["recipient_present"] = bool(recipient and "@" in str(recipient))
        if not checks["recipient_present"]:
            blocked.append("invalid_recipient")

    # 2. Check disputes
    has_dispute = bool(params.get("has_open_dispute") or params.get("disputed"))
    checks["no_dispute"] = not has_dispute
    if not checks["no_dispute"]:
        blocked.append("dispute_active_on_milestone")

    return checks, blocked
