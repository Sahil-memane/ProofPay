# TEMP: replaced by policy/
"""
Stub policy engine — enforces:
  - 200 USD auto-action limit
  - Contact cap of 4
  - 48-hour gap minimum
  - Customer quiet hours (21:00 to 08:00 local time)
  - Opt-out enforcement
  - Channel allowlist (email, payment_link only)
  - Daily action cap
  - No open disputes
  - LLM call budget (max 2)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app.recovery.timing import is_in_quiet_hours
from backend.app.stubs import clock, llm
from backend.app.stubs.contracts_stub import ActionKind, PolicyDecision, Proposal, Verdict
from backend.app.stubs.repositories import case_repo, contact_repo

AUTO_LIMIT_USD = 200.0
MAX_CONTACT_CAP = 4
MIN_GAP_HOURS = 48.0
ALLOWED_CHANNELS = {"email", "payment_link", "none"}

_DAILY_CAP_REACHED: bool = False
_DAILY_COUNT: int = 0
_DAILY_LIMIT: int = 50


def evaluate(proposal: Proposal) -> PolicyDecision:
    """Evaluate proposal against all operational safety and compliance checks."""
    checks: dict[str, bool] = {}
    blocked: list[str] = []

    case_id = proposal.subject
    case = case_repo.get(case_id) or {}
    params = proposal.params

    # 1. 200 USD Auto-Action Limit
    amount = float(params.get("amount_usd") or case.get("amount_usd", 0.0))
    checks["under_auto_limit"] = amount <= AUTO_LIMIT_USD
    if not checks["under_auto_limit"]:
        blocked.append("over_auto_limit")

    # 2. Daily Action Cap
    checks["daily_cap_ok"] = not _DAILY_CAP_REACHED and _DAILY_COUNT < _DAILY_LIMIT
    if not checks["daily_cap_ok"]:
        blocked.append("daily_cap_reached")

    # 3. Channel Allowlist (only email and payment_link allowed for outbound contact)
    channel = str(params.get("channel") or ("payment_link" if proposal.action == ActionKind.SEND_PAYMENT_LINK else "email")).lower()
    checks["channel_allowed"] = channel in ALLOWED_CHANNELS
    if not checks["channel_allowed"]:
        blocked.append("channel_not_allowed")

    # 4. Opt-Out Enforcement
    opted_out = bool(params.get("opted_out") or case.get("opted_out", False))
    checks["not_opted_out"] = not opted_out
    if not checks["not_opted_out"]:
        blocked.append("customer_opted_out")

    # 5. No Open Dispute
    open_dispute = bool(case.get("has_open_dispute") or case.get("disputed") or case.get("state") == "HALTED")
    checks["no_open_dispute"] = not open_dispute
    if not checks["no_open_dispute"]:
        blocked.append("open_dispute_active")

    # 6. Contact Cap 4
    existing_contacts = contact_repo.list_for_case(case_id)
    contact_count = case.get("contact_count", len(existing_contacts))
    is_outbound_contact = proposal.action in (ActionKind.SEND_EMAIL, ActionKind.SEND_PAYMENT_LINK)
    if is_outbound_contact and contact_count >= MAX_CONTACT_CAP:
        checks["under_contact_cap"] = False
        blocked.append("contact_cap_exceeded")
    else:
        checks["under_contact_cap"] = True

    # 7. 48-Hour Gap Enforcement
    now = clock.utcnow()
    last_contact_str = case.get("last_contact_at")
    last_contact_dt = None
    if existing_contacts:
        last_c = existing_contacts[-1].get("sent_at")
        if last_c:
            last_contact_str = last_c

    if last_contact_str and is_outbound_contact:
        try:
            last_contact_dt = datetime.fromisoformat(last_contact_str)
            if last_contact_dt.tzinfo is None:
                last_contact_dt = last_contact_dt.replace(tzinfo=timezone.utc)
            hours_since = (now - last_contact_dt).total_seconds() / 3600.0
            checks["gap_48h_ok"] = hours_since >= MIN_GAP_HOURS
        except Exception:
            checks["gap_48h_ok"] = True
    else:
        checks["gap_48h_ok"] = True

    if not checks["gap_48h_ok"]:
        blocked.append("min_gap_violation")

    # 8. Quiet Hours Enforcement (Customer Local Time 21:00 to 08:00)
    customer_tz = case.get("timezone", "UTC")
    target_send_time = now
    if params.get("run_at"):
        try:
            target_send_time = datetime.fromisoformat(params["run_at"])
            if target_send_time.tzinfo is None:
                target_send_time = target_send_time.replace(tzinfo=timezone.utc)
        except Exception:
            target_send_time = now

    if is_outbound_contact and is_in_quiet_hours(target_send_time, customer_tz):
        checks["outside_quiet_hours"] = False
        blocked.append("quiet_hours_violation")
    else:
        checks["outside_quiet_hours"] = True

    # 9. LLM Call Budget (Max 2 Calls Per Case)
    llm_calls = llm.get_call_count(case_id)
    checks["llm_budget_ok"] = llm_calls <= 2
    if not checks["llm_budget_ok"]:
        blocked.append("llm_budget_exceeded")

    # Verdict Determination
    if not blocked:
        verdict = Verdict.ALLOW
    elif blocked == ["over_auto_limit"]:
        # Only over auto-limit requires approval
        verdict = Verdict.NEEDS_APPROVAL
    else:
        # Any safety/policy violation (opt-out, quiet hours, gap, cap) -> DENY
        verdict = Verdict.DENY

    return PolicyDecision(verdict=verdict, checks=checks, blocked_by=blocked)


# Alias check to evaluate
check = evaluate


def record_action_executed() -> None:
    """Increment daily action counter."""
    global _DAILY_COUNT, _DAILY_CAP_REACHED
    _DAILY_COUNT += 1
    if _DAILY_COUNT >= _DAILY_LIMIT:
        _DAILY_CAP_REACHED = True


def reset_daily_cap() -> None:
    global _DAILY_CAP_REACHED, _DAILY_COUNT
    _DAILY_CAP_REACHED = False
    _DAILY_COUNT = 0


def set_daily_cap_reached() -> None:
    global _DAILY_CAP_REACHED
    _DAILY_CAP_REACHED = True
