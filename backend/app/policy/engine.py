"""
Policy Engine — evaluates proposals against recovery and escrow rule sets.
"""
from __future__ import annotations

from typing import Any

from backend.app.audit.writer import log_event
from backend.app.contracts.enums import ActionKind, Verdict
from backend.app.contracts.proposals import PolicyDecision, Proposal
from backend.app.policy.rules.escrow import evaluate_escrow_rules
from backend.app.policy.rules.recovery import evaluate_recovery_rules

_DAILY_CAP_REACHED: bool = False
_DAILY_COUNT: int = 0


def evaluate(proposal: Proposal) -> PolicyDecision:
    """Evaluate a proposal and return a PolicyDecision."""
    global _DAILY_COUNT, _DAILY_CAP_REACHED

    # Escrow actions vs Recovery actions
    if proposal.action in (
        ActionKind.CREATE_ORDER,
        ActionKind.CAPTURE_ORDER,
        ActionKind.PAYOUT,
        ActionKind.REFUND,
    ):
        checks, blocked = evaluate_escrow_rules(proposal)
    else:
        checks, blocked = evaluate_recovery_rules(
            proposal,
            daily_count=_DAILY_COUNT,
            daily_cap_reached=_DAILY_CAP_REACHED,
        )

    # Verdict determination
    if not blocked:
        verdict = Verdict.ALLOW
    elif blocked == ["over_auto_limit"]:
        verdict = Verdict.NEEDS_APPROVAL
    else:
        verdict = Verdict.DENY

    decision = PolicyDecision(verdict=verdict, checks=checks, blocked_by=blocked)

    # Audit log policy decision
    try:
        log_event(
            "policy_evaluated",
            {
                "proposal_subject": proposal.subject,
                "action": str(proposal.action),
                "verdict": str(verdict),
                "blocked_by": blocked,
            },
        )
    except Exception:
        pass

    return decision


check = evaluate


def record_action_executed() -> None:
    global _DAILY_COUNT, _DAILY_CAP_REACHED
    _DAILY_COUNT += 1
    # Check limit dynamically from config_loader if needed
    if _DAILY_COUNT >= 50:
        _DAILY_CAP_REACHED = True


def reset_daily_cap() -> None:
    global _DAILY_CAP_REACHED, _DAILY_COUNT
    _DAILY_CAP_REACHED = False
    _DAILY_COUNT = 0


def set_daily_cap_reached() -> None:
    global _DAILY_CAP_REACHED
    _DAILY_CAP_REACHED = True
