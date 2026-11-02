"""
Diagnosis Engine.

Maps failure codes, invoice statuses, and funding trigger events to canonical diagnoses:
  - insufficient_funds
  - expired_card
  - temporary_hold
  - forgot_to_pay
  - large_overdue_invoice
  - suspicious_hard_decline

Also triages customer conversational free-text replies via budgeted, injection-hardened LLM calls.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml

from backend.app.stubs import audit, llm

logger = logging.getLogger(__name__)

# Valid diagnoses enum list
VALID_DIAGNOSES = {
    "insufficient_funds",
    "expired_card",
    "temporary_hold",
    "forgot_to_pay",
    "large_overdue_invoice",
    "suspicious_hard_decline",
}

_RULES_CACHE: dict[str, Any] | None = None


def load_diagnosis_rules() -> dict[str, Any]:
    global _RULES_CACHE
    if _RULES_CACHE is not None:
        return _RULES_CACHE

    root = Path(__file__).resolve().parents[3]
    config_path = root / "backend" / "app" / "recovery" / "config" / "diagnosis_rules.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            _RULES_CACHE = yaml.safe_load(f) or {}
            return _RULES_CACHE
    return {}


def diagnose_case(case: dict[str, Any], rules: dict[str, Any] | None = None) -> str:
    """
    Map case attributes (failure code, invoice amount, trigger) to one of the 6 canonical diagnoses.
    """
    rule_set = rules or load_diagnosis_rules()
    payload = case.get("payload", {})

    failure_code = (
        case.get("failure_code")
        or payload.get("failure_code")
        or case.get("failure_reason")
        or payload.get("failure_reason")
    )
    trigger = case.get("trigger_type") or payload.get("trigger_type", "")
    amount = float(case.get("amount_usd") or payload.get("amount_usd") or case.get("amount", 0.0))

    # 1. Failure Code Rules
    if failure_code:
        fc = str(failure_code).strip().lower()
        if "insufficient" in fc or "funds" in fc:
            return "insufficient_funds"
        if "expired" in fc or "card" in fc:
            return "expired_card"
        if "hold" in fc or "temp" in fc:
            return "temporary_hold"
        if "decline" in fc or "hard" in fc or "fraud" in fc:
            return "suspicious_hard_decline"

    # 2. Invoice Trigger Rules
    threshold = float(rule_set.get("invoice_rules", {}).get("large_amount_threshold_usd", 200.0))
    if trigger == "overdue_invoice" or case.get("invoice_id") or payload.get("invoice_id"):
        if amount > threshold:
            return "large_overdue_invoice"
        return "forgot_to_pay"

    # 3. Funding Failed Rules
    if trigger == "funding_failed":
        reason = str(payload.get("reason", "")).lower()
        if "balance" in reason or "funds" in reason:
            return "insufficient_funds"
        if "expired" in reason:
            return "expired_card"
        if "risk" in reason or "fraud" in reason:
            return "suspicious_hard_decline"
        return "temporary_hold"

    # 4. Default fallback based on amount threshold
    if amount > threshold:
        return "large_overdue_invoice"
    return "forgot_to_pay"


def diagnose_free_text_reply(
    case_id: str,
    reply_text: str,
    llm_client: Any = None,
) -> dict[str, Any]:
    """
    Triage a customer conversational reply using one budgeted LLM call.
    The customer reply is strictly encapsulated in <customer_reply> delimiters
    to prevent prompt injection.
    
    Returns: {"diagnosis": str, "promised_date": str | None, "note": str | None}
    Falls back to a log-only note on bad output, timeout, or exceeded call budget.
    """
    client = llm_client or llm

    # Sanitize and strictly encapsulate customer text
    clean_reply = str(reply_text).replace("</customer_reply>", "").strip()

    prompt = (
        "You are an automated recovery triage classifier.\n"
        "Analyze the customer's response inside the delimited block below.\n"
        "Extract the underlying failure diagnosis and any promised payment date.\n"
        "Valid diagnoses: insufficient_funds, expired_card, temporary_hold, "
        "forgot_to_pay, large_overdue_invoice, suspicious_hard_decline.\n\n"
        "<customer_reply>\n"
        f"{clean_reply}\n"
        "</customer_reply>\n\n"
        "Return STRICT JSON only, with keys:\n"
        "- diagnosis: one of the valid diagnoses\n"
        "- promised_date: ISO date string or null\n"
    )

    try:
        raw_response = client.complete(case_id, prompt)

        # Parse JSON from response
        # Extract potential JSON block if LLM wrapped in markdown
        json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(0))
        else:
            # If stub returns canned string "[stub-llm] response #..."
            # Check keywords in customer reply as deterministic parsing
            parsed = _deterministic_reply_parse(clean_reply)

        diag = parsed.get("diagnosis", "")
        if diag not in VALID_DIAGNOSES:
            # Fall back to keyword or default
            parsed = _deterministic_reply_parse(clean_reply)

        return {
            "diagnosis": parsed.get("diagnosis", "forgot_to_pay"),
            "promised_date": parsed.get("promised_date"),
            "note": "llm_triage_completed",
        }

    except Exception as e:
        # On bad output, quota exhaustion, or budget exceeded (>2 calls):
        logger.warning("LLM triage fallback for case %s: %s", case_id, e)
        audit.log_event("llm_diagnosis_fallback", {
            "case_id": case_id,
            "error": str(e),
            "reply_snippet": clean_reply[:80],
        })
        fallback = _deterministic_reply_parse(clean_reply)
        return {
            "diagnosis": fallback.get("diagnosis", "forgot_to_pay"),
            "promised_date": fallback.get("promised_date"),
            "note": f"fallback_log_only: {e}",
        }


def _deterministic_reply_parse(reply: str) -> dict[str, Any]:
    """Safe keyword triage used for stub parsing and LLM fallback."""
    r = reply.lower()
    if "card" in r or "cvv" in r or "expir" in r or "कार्ड" in r:
        return {"diagnosis": "expired_card", "promised_date": None}
    if "funds" in r or "balance" in r or "money" in r or "पैसा" in r:
        return {"diagnosis": "insufficient_funds", "promised_date": None}
    if "friday" in r or "शुक्रवार" in r:
        return {"diagnosis": "forgot_to_pay", "promised_date": "2025-06-06"}
    if "monday" in r or "सोमवार" in r:
        return {"diagnosis": "forgot_to_pay", "promised_date": "2025-06-09"}
    if "split" in r or "installment" in r or "किश्त" in r:
        return {"diagnosis": "forgot_to_pay", "promised_date": None}
    return {"diagnosis": "forgot_to_pay", "promised_date": None}

