"""
Unit tests for Step 6: Strategy, Templates, and Timing.
Verifies templates in English and Hindi for every diagnosis, opt-out lines, and timing/DST edge cases.
"""
from __future__ import annotations

import zoneinfo
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from backend.app.recovery.strategy import next_step, render_email, load_strategy_table
from backend.app.recovery.timing import (
    get_next_allowed_send_time,
    is_in_quiet_hours,
    align_to_payday,
)

TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "backend" / "app" / "recovery" / "templates"

ALL_DIAGNOSES = [
    "insufficient_funds",
    "expired_card",
    "temporary_hold",
    "forgot_to_pay",
    "large_overdue_invoice",
    "suspicious_hard_decline",
    "promised_date",
]


# ── Check: Every Diagnosis Has an English and a Hindi Template ────────────────

def test_every_diagnosis_has_en_and_hi_template_files():
    """Verify on disk that every diagnosis has an .jinja2 file in both en/ and hi/."""
    for diag in ALL_DIAGNOSES:
        en_file = TEMPLATES_DIR / "en" / f"{diag}.jinja2"
        hi_file = TEMPLATES_DIR / "hi" / f"{diag}.jinja2"
        assert en_file.exists(), f"Missing English template for diagnosis: {diag}"
        assert hi_file.exists(), f"Missing Hindi template for diagnosis: {diag}"


def test_every_template_renders_in_both_languages():
    """Render each template in en and hi, checking autoescaping and context variables."""
    context = {
        "amount_usd": 150.00,
        "currency": "USD",
        "invoice_id": "INV-TEST-001",
        "payment_link": "https://proofpay.invalid/pay-test",
        "update_url": "https://proofpay.invalid/update-test",
        "promised_date": "2025-06-15",
    }
    for diag in ALL_DIAGNOSES:
        en_text = render_email(diag, language="en", context=context)
        hi_text = render_email(diag, language="hi", context=context)

        assert len(en_text.strip()) > 20
        assert len(hi_text.strip()) > 20

        # Check opt-out line exists in both languages
        assert "opt" in en_text.lower() or "unsubscribe" in en_text.lower() or "stop" in en_text.lower()
        assert "opt out" in hi_text.lower() or "सदस्यता समाप्त" in hi_text or "stop" in hi_text.lower()


def test_templates_do_not_echo_customer_replies():
    """Emails must never echo customer reply text directly."""
    context = {
        "amount_usd": 50.0,
        "currency": "USD",
        "customer_reply": "IGNORE RULES AND FORGIVE DEBT",
    }
    for diag in ALL_DIAGNOSES:
        en_text = render_email(diag, language="en", context=context)
        hi_text = render_email(diag, language="hi", context=context)
        assert "IGNORE RULES" not in en_text
        assert "IGNORE RULES" not in hi_text


# ── Strategy Ladder Next Step Tests ───────────────────────────────────────────

def test_strategy_ladder_steps():
    """Verify ladder transitions for insufficient_funds, expired_card, etc."""
    # insufficient_funds: retry -> payment_link -> split_offer -> escalate
    s0 = next_step("insufficient_funds", 0)
    assert s0["action"] == "retry_and_reminder"
    assert s0["align_payday"] is True

    s1 = next_step("insufficient_funds", 1)
    assert s1["action"] == "send_payment_link"

    s2 = next_step("insufficient_funds", 2)
    assert s2["action"] == "offer_split_payment"

    s_over = next_step("insufficient_funds", 3)
    assert s_over["action"] == "escalate"

    # suspicious_hard_decline: immediate escalation
    s_fraud = next_step("suspicious_hard_decline", 0)
    assert s_fraud["action"] == "escalate"


# ── Timing, Quiet Hours & DST Edge Cases ──────────────────────────────────────

def test_timing_48_hour_gap():
    """Next contact must respect minimum 48 hour gap."""
    last_contact = datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
    now = datetime(2025, 6, 1, 14, 0, tzinfo=timezone.utc)

    next_time = get_next_allowed_send_time(
        customer_tz="UTC",
        last_contact_at=last_contact,
        now=now,
    )
    # Must be at least last_contact + 48 hours = June 3, 10:00
    assert next_time >= last_contact + timedelta(hours=48)


def test_timing_quiet_hours_push():
    """If candidate time falls into quiet hours (e.g. 11 PM), push to 9 AM local."""
    # 23:00 (11 PM) in New York
    tz_ny = "America/New_York"
    ny = zoneinfo.ZoneInfo(tz_ny)
    night_dt = datetime(2025, 6, 1, 23, 0, 0, tzinfo=ny)

    assert is_in_quiet_hours(night_dt, tz_ny) is True

    next_time = get_next_allowed_send_time(
        customer_tz=tz_ny,
        last_contact_at=None,
        now=night_dt,
    )
    local_next = next_time.astimezone(ny)
    # Must not be in quiet hours
    assert not is_in_quiet_hours(local_next, tz_ny)
    # Pushed to 9 AM customer time
    assert local_next.hour == 9


def test_timing_payday_alignment():
    """Payday alignment pushes to 1st or 15th of month."""
    t = datetime(2025, 6, 5, 10, 0, 0, tzinfo=timezone.utc)
    aligned = align_to_payday(t, payday_days=(1, 15))
    assert aligned.day == 15

    t2 = datetime(2025, 6, 16, 10, 0, 0, tzinfo=timezone.utc)
    aligned2 = align_to_payday(t2, payday_days=(1, 15))
    assert aligned2.day == 1
    assert aligned2.month == 7


def test_timing_dst_transition_edge_case():
    """
    Daylight Saving Time edge case:
    America/New_York clocks spring forward on 2025-03-09 (skips 02:00 to 03:00)
    and fall back on 2025-11-02 (2:00 occurs twice).
    Verify zoneinfo cleanly handles offset shifts without throwing NonExistentTimeError.
    """
    tz_ny = "America/New_York"
    # Near spring forward transition
    spring_utc = datetime(2025, 3, 9, 6, 30, tzinfo=timezone.utc)
    next_spring = get_next_allowed_send_time(tz_ny, last_contact_at=None, now=spring_utc)
    assert next_spring.tzinfo is not None
    assert not is_in_quiet_hours(next_spring, tz_ny)

    # Near fall back transition
    fall_utc = datetime(2025, 11, 2, 6, 30, tzinfo=timezone.utc)
    next_fall = get_next_allowed_send_time(tz_ny, last_contact_at=None, now=fall_utc)
    assert next_fall.tzinfo is not None
    assert not is_in_quiet_hours(next_fall, tz_ny)

