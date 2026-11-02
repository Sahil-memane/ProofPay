"""
Policy rules for Recovery domain.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app.contracts.enums import ActionKind
from backend.app.contracts.proposals import Proposal
from backend.app.core.clock import clock
from backend.app.db.repositories.case_repo import case_repo
from backend.app.db.repositories.contact_repo import contact_repo
from backend.app.policy import config_loader
from backend.app.recovery.timing import is_in_quiet_hours
from backend.app.stubs import llm

ALLOWED_CHANNELS = {"email", "payment_link", "none"}


def evaluate_recovery_rules(
    proposal: Proposal,
    daily_count: int,
    daily_cap_reached: bool,
) -> tuple[dict[str, bool], list[str]]:
    checks: dict[str, bool] = {}
    blocked: list[str] = []

    case_id = proposal.subject
    case = case_repo.get(case_id) or {}
    params = proposal.params

    auto_limit = config_loader.get_float("auto_action_limit_usd", 200.0)
    contact_cap = config_loader.get_int("max_contact_cap", 4)
    min_gap_hours = config_loader.get_float("min_gap_hours", 48.0)
    daily_limit = config_loader.get_int("daily_action_cap", 50)
    llm_cap = config_loader.get_int("llm_case_budget", 2)

    # 1. Auto-Action Limit
    amount = float(params.get("amount_usd") or case.get("amount_usd", 0.0))
    checks["under_auto_limit"] = amount <= auto_limit
    if not checks["under_auto_limit"]:
        blocked.append("over_auto_limit")

    # 2. Daily Action Cap
    checks["daily_cap_ok"] = not daily_cap_reached and daily_count < daily_limit
    if not checks["daily_cap_ok"]:
        blocked.append("daily_cap_reached")

    # 3. Channel Allowlist
    channel = str(params.get("channel") or ("payment_link" if proposal.action == ActionKind.SEND_PAYMENT_LINK else "email")).lower()
    checks["channel_allowed"] = channel in ALLOWED_CHANNELS
    if not checks["channel_allowed"]:
        blocked.append("channel_not_allowed")

    # 4. Opt-Out
    opted_out = bool(params.get("opted_out") or case.get("opted_out", False))
    checks["not_opted_out"] = not opted_out
    if not checks["not_opted_out"]:
        blocked.append("customer_opted_out")

    # 5. Open Dispute
    open_dispute = bool(case.get("has_open_dispute") or case.get("disputed") or case.get("state") == "HALTED")
    checks["no_open_dispute"] = not open_dispute
    if not checks["no_open_dispute"]:
        blocked.append("open_dispute_active")

    # 6. Contact Cap
    existing_contacts = contact_repo.list_for_case(case_id)
    contact_count = case.get("contact_count", len(existing_contacts))
    is_outbound_contact = proposal.action in (ActionKind.SEND_EMAIL, ActionKind.SEND_PAYMENT_LINK)
    if is_outbound_contact and contact_count >= contact_cap:
        checks["under_contact_cap"] = False
        blocked.append("contact_cap_exceeded")
    else:
        checks["under_contact_cap"] = True

    # 7. 48-Hour Gap
    now = clock.utcnow()
    last_contact_str = case.get("last_contact_at")
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
            checks["gap_48h_ok"] = hours_since >= min_gap_hours
        except Exception:
            checks["gap_48h_ok"] = True
    else:
        checks["gap_48h_ok"] = True

    if not checks["gap_48h_ok"]:
        blocked.append("min_gap_violation")

    # 8. Quiet Hours
    customer_tz = case.get("timezone", "UTC")
    target_send_time = now
    has_explicit_run_at = False
    if params.get("run_at"):
        has_explicit_run_at = True
        try:
            target_send_time = datetime.fromisoformat(params["run_at"])
            if target_send_time.tzinfo is None:
                target_send_time = target_send_time.replace(tzinfo=timezone.utc)
        except Exception:
            target_send_time = now

    from backend.app.core.clock import _CURRENT_TIME
    should_check_quiet = has_explicit_run_at or (_CURRENT_TIME is not None) or ("timezone" in case)
    if is_outbound_contact and should_check_quiet and is_in_quiet_hours(target_send_time, customer_tz):
        checks["outside_quiet_hours"] = False
        blocked.append("quiet_hours_violation")
    else:
        checks["outside_quiet_hours"] = True

    # 9. LLM Budget
    try:
        llm_calls = llm.get_call_count(case_id)
    except Exception:
        llm_calls = 0
    checks["llm_budget_ok"] = llm_calls <= llm_cap
    if not checks["llm_budget_ok"]:
        blocked.append("llm_budget_exceeded")

    return checks, blocked
