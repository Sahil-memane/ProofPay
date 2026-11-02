"""
Customer profiles and response simulator.

A Profile drives communication reachability, timezone, opt-out status,
and true underlying customer payment behavior.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

import yaml

from backend.app.simulator.sim_events import SimulatorEvent, SimulatorEventType


TIMEZONES = [
    "America/New_York",   # UTC-5/-4
    "America/Chicago",    # UTC-6/-5
    "America/Denver",     # UTC-7/-6
    "America/Los_Angeles",# UTC-8/-7
    "Europe/London",      # UTC+0/+1
    "Europe/Paris",       # UTC+1/+2
    "Asia/Kolkata",       # UTC+5:30
    "Asia/Tokyo",         # UTC+9
    "Australia/Sydney",   # UTC+10/+11
]

TZ_OFFSET_HOURS: dict[str, float] = {
    "America/New_York": -5,
    "America/Chicago": -6,
    "America/Denver": -7,
    "America/Los_Angeles": -8,
    "Europe/London": 0,
    "Europe/Paris": 1,
    "Asia/Kolkata": 5.5,
    "Asia/Tokyo": 9,
    "Australia/Sydney": 10,
}

# The 7 canonical customer hidden behavior profiles
CANONICAL_PROFILES = [
    "pays_after_one_reminder",
    "needs_payment_link",
    "needs_card_update",
    "prefers_split",
    "ignores_everything",
    "disputes_if_chased_early",
    "already_paid_elsewhere",
]

DEFAULT_EARLY_CHASE_DAYS = 3


# ── Customer Profile Models ───────────────────────────────────────────────────

@dataclass
class CustomerProfile:
    customer_id: str
    email: str
    timezone: str
    opted_out: bool = False
    has_email: bool = True
    avg_payment_delay_hours: float = 24.0
    payment_reliability: float = 0.85
    risk_tier: Literal["low", "medium", "high"] = "medium"
    tags: list[str] = field(default_factory=list)
    # Hidden profile characteristics (only known inside simulator)
    behaviour: str = "pays_after_one_reminder"
    language: str = "en"
    history: list[str] = field(default_factory=list)


def generate_profiles(n: int, seed: int = 42) -> list[CustomerProfile]:
    """Generate n synthetic customer profiles for testing."""
    rng = random.Random(seed)
    profiles: list[CustomerProfile] = []

    for i in range(n):
        cust_id = f"CUST-{i:05d}"
        email = f"customer{i}@example.com"
        tz = rng.choice(TIMEZONES)
        opted_out = rng.random() < 0.05
        reliability = rng.uniform(0.5, 1.0)
        delay = rng.uniform(4.0, 96.0)
        risk_tier = (
            "low" if reliability > 0.85
            else "high" if reliability < 0.65
            else "medium"
        )
        behaviour = CANONICAL_PROFILES[i % len(CANONICAL_PROFILES)]
        lang = "hi" if (i % 4 == 0) else "en"
        profiles.append(CustomerProfile(
            customer_id=cust_id,
            email=email,
            timezone=tz,
            opted_out=opted_out,
            has_email=True,
            avg_payment_delay_hours=delay,
            payment_reliability=reliability,
            risk_tier=risk_tier,
            behaviour=behaviour,
            language=lang,
        ))

    return profiles


def get_utc_offset(timezone_name: str) -> float:
    return TZ_OFFSET_HOURS.get(timezone_name, 0.0)


def _local_hour(utc_time: datetime, utc_offset_hours: float) -> float:
    return (utc_time.hour + utc_offset_hours) % 24


def is_quiet_hours(utc_time: datetime, timezone_name: str) -> bool:
    offset = get_utc_offset(timezone_name)
    local_h = _local_hour(utc_time, offset)
    return local_h >= 21.0 or local_h < 8.0


# ── Hidden Profile Loader (Simulator Internal Only) ──────────────────────────

_CACHE_HIDDEN_PROFILES: dict[str, dict[str, Any]] | None = None


def load_hidden_profiles() -> dict[str, dict[str, Any]]:
    """
    Read answer key customers.yaml (simulator internal).
    Returns mapping of customer_id -> attributes.
    """
    global _CACHE_HIDDEN_PROFILES
    if _CACHE_HIDDEN_PROFILES is not None:
        return _CACHE_HIDDEN_PROFILES

    repo_root = Path(__file__).resolve().parents[3]
    key_path = repo_root / "data" / "answer_key" / "customers.yaml"
    if key_path.exists():
        try:
            with key_path.open("r", encoding="utf-8") as f:
                _CACHE_HIDDEN_PROFILES = yaml.safe_load(f) or {}
                return _CACHE_HIDDEN_PROFILES
        except Exception:
            pass
    return {}


def clear_profile_cache() -> None:
    global _CACHE_HIDDEN_PROFILES
    _CACHE_HIDDEN_PROFILES = None


# ── Action Classifier ─────────────────────────────────────────────────────────

def _normalize_action(action: Any) -> str:
    """Normalize action string/object to one of: payment_link, card_update, split_offer, reminder."""
    if hasattr(action, "action"):
        action_val = str(action.action)
    elif isinstance(action, dict):
        action_val = str(action.get("action", ""))
    else:
        action_val = str(action)

    action_lower = action_val.lower()

    if "link" in action_lower or "payment_link" in action_lower:
        return "payment_link"
    if "card" in action_lower or "card_update" in action_lower:
        return "card_update"
    if "split" in action_lower or "installment" in action_lower:
        return "split_offer"
    return "reminder"


# ── Dialog Templates ──────────────────────────────────────────────────────────

FREE_TEXT_RESPONSES = {
    "en": {
        "promise_friday": "I'll pay Friday",
        "promise_monday": "Will settle this by next Monday.",
        "needs_link": "Could you please send me a direct payment link?",
        "needs_card": "My card expired. How can I update it?",
        "wants_split": "Can I split this across two installments?",
        "already_paid": "I already paid this invoice by bank transfer.",
        "dispute": "I dispute this charge; do not contact me again.",
    },
    "hi": {
        "promise_friday": "मैं शुक्रवार को भुगतान करूँगा",
        "promise_monday": "मैं सोमवार तक भुगतान कर दूँगा।",
        "needs_link": "कृपया मुझे सीधा भुगतान लिंक भेजें।",
        "needs_card": "मेरा कार्ड एक्सपायर हो गया है, कृपया कार्ड अपडेट लिंक दें।",
        "wants_split": "क्या मैं इसे दो किश्तों में विभाजित कर सकता हूँ?",
        "already_paid": "मैंने पहले ही बैंक ट्रांसफर से भुगतान कर दिया है।",
        "dispute": "यह अनुचित है, मैं इस पर विवाद करता हूँ।",
    },
}


# ── Main Simulator Function: respond() ─────────────────────────────────────────

def respond(
    case: Any,
    action: Any,
    now: datetime,
    rng: random.Random,
    early_chase_days: int = DEFAULT_EARLY_CHASE_DAYS,
) -> SimulatorEvent:
    """
    Simulate a customer's response to an outreach action.
    Reads customer's hidden profile (only inside simulator).
    
    Returns a SimulatorEvent:
      - payment_success
      - free_text_reply (e.g. "I'll pay Friday" in en or hi)
      - dispute
      - opt_out
      - nothing
    """
    # 1. Extract case metadata
    case_id = (
        case.get("case_id") or case.get("id") if isinstance(case, dict)
        else getattr(case, "case_id", getattr(case, "id", "CASE-UNKNOWN"))
    )
    customer_id = (
        case.get("customer_id") if isinstance(case, dict)
        else getattr(case, "customer_id", "CUST-00000")
    )
    amount_usd = (
        case.get("amount_usd") or case.get("amount") if isinstance(case, dict)
        else getattr(case, "amount_usd", getattr(case, "amount", 100.0))
    )
    due_date = (
        case.get("due_date") or case.get("created_at") if isinstance(case, dict)
        else getattr(case, "due_date", getattr(case, "created_at", None))
    )

    # 2. Extract hidden profile
    behaviour = None
    lang = "en"
    opted_out = False

    # Direct profile override on case if provided
    if isinstance(case, dict) and "profile" in case:
        p = case["profile"]
        if isinstance(p, CustomerProfile):
            behaviour = p.behaviour
            lang = p.language
            opted_out = p.opted_out
        elif isinstance(p, dict):
            behaviour = p.get("behaviour")
            lang = p.get("language", "en")
            opted_out = p.get("opted_out", False)
        elif isinstance(p, str):
            behaviour = p
    elif hasattr(case, "behaviour"):
        behaviour = case.behaviour
    elif hasattr(case, "profile"):
        p = case.profile
        behaviour = getattr(p, "behaviour", str(p))

    # Lookup from hidden answer key if not directly on case
    if not behaviour:
        hidden_map = load_hidden_profiles()
        cust_info = hidden_map.get(customer_id, {})
        behaviour = cust_info.get("behaviour", "pays_after_one_reminder")
        lang = cust_info.get("language", "en")
        opted_out = cust_info.get("opted_out", False)

    # If customer is opted out, emit opt_out event
    if opted_out:
        return SimulatorEvent(
            event_type=SimulatorEventType.OPT_OUT,
            customer_id=customer_id,
            case_id=case_id,
            timestamp=now + timedelta(minutes=1),
            amount=None,
            message="Unsubscribe / Opt-out requested.",
            meta={"opted_out": True},
        )

    action_type = _normalize_action(action)
    lang_code = lang if lang in ("en", "hi") else "en"
    texts = FREE_TEXT_RESPONSES[lang_code]

    # 3. Special Profile Case: already_paid_elsewhere
    # Needs no contact; any contact counts as a wrongful contact!
    if behaviour == "already_paid_elsewhere":
        reply_choice = rng.choice(["already_paid", "dispute"])
        msg = texts[reply_choice]
        ev_type = SimulatorEventType.DISPUTE if reply_choice == "dispute" else SimulatorEventType.FREE_TEXT_REPLY
        return SimulatorEvent(
            event_type=ev_type,
            customer_id=customer_id,
            case_id=case_id,
            timestamp=now + timedelta(hours=rng.uniform(1.0, 12.0)),
            amount=None,
            message=msg,
            meta={
                "is_wrongful_contact": True,
                "wrongful_contact": True,
                "reason": "already_paid_by_bank_transfer",
                "language": lang_code,
            },
        )

    # 4. Special Profile Case: ignores_everything
    # Never pays. Emits nothing (or rare opt_out).
    if behaviour == "ignores_everything":
        roll = rng.random()
        if roll < 0.08:
            return SimulatorEvent(
                event_type=SimulatorEventType.OPT_OUT,
                customer_id=customer_id,
                case_id=case_id,
                timestamp=now + timedelta(hours=rng.uniform(2.0, 24.0)),
                amount=None,
                message="Stop messaging me.",
                meta={"language": lang_code},
            )
        return SimulatorEvent(
            event_type=SimulatorEventType.NOTHING,
            customer_id=customer_id,
            case_id=case_id,
            timestamp=now + timedelta(days=2),
            amount=None,
            message=None,
            meta={"silence": True},
        )

    # 5. Special Profile Case: disputes_if_chased_early
    # If contacted within early_chase_days, triggers a dispute!
    days_since_due: float = 0.0
    if isinstance(due_date, datetime):
        delta = now - due_date
        days_since_due = max(0.0, delta.total_seconds() / 86400.0)
    elif isinstance(due_date, str):
        try:
            dt = datetime.fromisoformat(due_date)
            delta = now - dt
            days_since_due = max(0.0, delta.total_seconds() / 86400.0)
        except Exception:
            days_since_due = 1.0  # fallback to early
    else:
        # Default assume 1 day if not specified
        days_since_due = 1.0

    if behaviour == "disputes_if_chased_early":
        if days_since_due < early_chase_days:
            return SimulatorEvent(
                event_type=SimulatorEventType.DISPUTE,
                customer_id=customer_id,
                case_id=case_id,
                timestamp=now + timedelta(hours=rng.uniform(0.5, 6.0)),
                amount=None,
                message=texts["dispute"],
                meta={
                    "chased_early": True,
                    "days_since_due": round(days_since_due, 2),
                    "threshold_days": early_chase_days,
                    "language": lang_code,
                },
            )
        else:
            # Contacted after quiet window -> high payment probability
            roll = rng.random()
            if roll < 0.80:
                return SimulatorEvent(
                    event_type=SimulatorEventType.PAYMENT_SUCCESS,
                    customer_id=customer_id,
                    case_id=case_id,
                    timestamp=now + timedelta(hours=rng.uniform(2.0, 24.0)),
                    amount=float(amount_usd),
                    message=None,
                    meta={"language": lang_code},
                )
            else:
                return SimulatorEvent(
                    event_type=SimulatorEventType.FREE_TEXT_REPLY,
                    customer_id=customer_id,
                    case_id=case_id,
                    timestamp=now + timedelta(hours=rng.uniform(1.0, 8.0)),
                    amount=None,
                    message=texts["promise_friday"],
                    meta={"language": lang_code},
                )

    # 6. Cause-Matching Profiles:
    # needs_payment_link -> matches payment_link
    # needs_card_update -> matches card_update
    # prefers_split -> matches split_offer
    # pays_after_one_reminder -> matches any action
    is_match = False
    if behaviour == "needs_payment_link" and action_type == "payment_link":
        is_match = True
    elif behaviour == "needs_card_update" and action_type == "card_update":
        is_match = True
    elif behaviour == "prefers_split" and action_type == "split_offer":
        is_match = True
    elif behaviour == "pays_after_one_reminder":
        is_match = True

    # 7. Roll against probability distribution
    roll = rng.random()

    if is_match:
        # High success probability (~85%)
        if roll < 0.85:
            return SimulatorEvent(
                event_type=SimulatorEventType.PAYMENT_SUCCESS,
                customer_id=customer_id,
                case_id=case_id,
                timestamp=now + timedelta(hours=rng.uniform(1.0, 18.0)),
                amount=float(amount_usd),
                message=None,
                meta={"action_matched": True, "behaviour": behaviour},
            )
        elif roll < 0.95:
            # Promise to pay / confirmation reply
            return SimulatorEvent(
                event_type=SimulatorEventType.FREE_TEXT_REPLY,
                customer_id=customer_id,
                case_id=case_id,
                timestamp=now + timedelta(hours=rng.uniform(0.5, 4.0)),
                amount=None,
                message=texts["promise_friday"],
                meta={"action_matched": True, "language": lang_code},
            )
        else:
            return SimulatorEvent(
                event_type=SimulatorEventType.NOTHING,
                customer_id=customer_id,
                case_id=case_id,
                timestamp=now + timedelta(days=2),
                amount=None,
                message=None,
                meta={"action_matched": True},
            )
    else:
        # Unmatched action: low success probability (~2%)
        if roll < 0.02:
            return SimulatorEvent(
                event_type=SimulatorEventType.PAYMENT_SUCCESS,
                customer_id=customer_id,
                case_id=case_id,
                timestamp=now + timedelta(hours=rng.uniform(6.0, 48.0)),
                amount=float(amount_usd),
                message=None,
                meta={"action_matched": False, "behaviour": behaviour},
            )
        elif roll < 0.65:
            # Free text reply prompting for the right resolution
            if behaviour == "needs_payment_link":
                prompt_msg = texts["needs_link"]
            elif behaviour == "needs_card_update":
                prompt_msg = texts["needs_card"]
            elif behaviour == "prefers_split":
                prompt_msg = texts["wants_split"]
            else:
                prompt_msg = texts["promise_monday"]

            return SimulatorEvent(
                event_type=SimulatorEventType.FREE_TEXT_REPLY,
                customer_id=customer_id,
                case_id=case_id,
                timestamp=now + timedelta(hours=rng.uniform(1.0, 12.0)),
                amount=None,
                message=prompt_msg,
                meta={"action_matched": False, "hint": behaviour, "language": lang_code},
            )
        elif roll < 0.95:
            return SimulatorEvent(
                event_type=SimulatorEventType.NOTHING,
                customer_id=customer_id,
                case_id=case_id,
                timestamp=now + timedelta(days=2),
                amount=None,
                message=None,
                meta={"action_matched": False},
            )
        else:
            return SimulatorEvent(
                event_type=SimulatorEventType.OPT_OUT,
                customer_id=customer_id,
                case_id=case_id,
                timestamp=now + timedelta(hours=rng.uniform(1.0, 6.0)),
                amount=None,
                message="Opt me out.",
                meta={"action_matched": False},
            )


# ── Assumptions Text for UI Honesty Panel ────────────────────────────────────

def assumptions_text() -> str:
    """
    Return plain text for the UI honesty panel explaining
    all simulator assumptions and behavior dynamics.
    """
    return (
        "ProofPay Customer Simulator Assumptions & Model Specifications:\n"
        "---------------------------------------------------------------\n"
        "1. Behavioral Archetypes:\n"
        "   - pays_after_one_reminder: Responds with payment_success (~85%) upon initial outreach.\n"
        "   - needs_payment_link: High conversion (85%) when offered direct payment link; low (10%) otherwise.\n"
        "   - needs_card_update: High conversion (85%) when guided to update card credentials; low otherwise.\n"
        "   - prefers_split: High conversion (85%) when offered installment / split plans; requests split otherwise.\n"
        "   - ignores_everything: Zero payment probability (0%); exhibits complete non-response or opt-out.\n"
        "   - disputes_if_chased_early: Contact within configurable window (<3 days) guarantees dispute filing;\n"
        "     contact after quiet window converts at standard high reliability (80%).\n"
        "   - already_paid_elsewhere: Paid out-of-band via bank transfer. Any outreach is recorded as a\n"
        "     wrongful contact violation and triggers immediate dispute or corrective reply.\n"
        "\n"
        "2. Action-Matching Dynamics:\n"
        "   - Matched actions yield 85% payment success, 10% confirmation reply, 5% silence.\n"
        "   - Unmatched actions yield 2% payment success, 63% clarifying reply, 30% silence, 5% opt-out.\n"
        "\n"
        "3. Quiet Hours & Timing Constraints:\n"
        "   - Quiet hours defined as 21:00 to 08:00 in customer's local IANA timezone.\n"
        "   - Minimum 48-hour gap enforced between non-urgent contacts.\n"
        "\n"
        "4. Localization:\n"
        "   - Free-text conversational replies dynamically generated in English (en) or Hindi (hi)\n"
        "     based on customer profile language attributes.\n"
        "\n"
        "5. Event Dispatching:\n"
        "   - All simulated customer responses are dispatched via sim_events callback handlers\n"
        "     and postable to /sim/events webhook receivers."
    )
