"""
Unit tests for the Customer Simulator (profiles.py and sim_events.py).
Tests all 7 customer profiles, determinism, language variants, and event callbacks.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
import pytest

from backend.app.simulator.profiles import (
    respond,
    assumptions_text,
    CustomerProfile,
    CANONICAL_PROFILES,
)
from backend.app.simulator.sim_events import (
    SimulatorEvent,
    SimulatorEventType,
    post_event,
    register_event_callback,
    clear_event_callbacks,
)

BASE_TIME = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_case(profile_type: str, language: str = "en", days_due: int = 5, amount: float = 120.0):
    """Helper to construct test case dictionary with explicit hidden profile."""
    due = BASE_TIME - timedelta(days=days_due)
    return {
        "case_id": f"CASE-{profile_type[:4].upper()}-001",
        "customer_id": f"CUST-{profile_type[:4].upper()}-001",
        "amount_usd": amount,
        "due_date": due,
        "profile": CustomerProfile(
            customer_id=f"CUST-{profile_type[:4].upper()}-001",
            email="test@example.com",
            timezone="America/New_York",
            behaviour=profile_type,
            language=language,
        ),
    }


# ── Tests for Each Profile (One per profile with fixed seed) ─────────────────

def test_profile_pays_after_one_reminder():
    """Profile 1: pays_after_one_reminder pays on initial contact."""
    case = make_case("pays_after_one_reminder")
    rng = random.Random(101)
    ev = respond(case, action="send_reminder", now=BASE_TIME, rng=rng)
    assert ev.event_type == SimulatorEventType.PAYMENT_SUCCESS
    assert ev.amount == 120.0
    assert ev.meta.get("action_matched") is True


def test_profile_needs_payment_link_matched():
    """Profile 2a: needs_payment_link with payment link action succeeds."""
    case = make_case("needs_payment_link")
    rng = random.Random(202)
    ev = respond(case, action="send_payment_link", now=BASE_TIME, rng=rng)
    assert ev.event_type == SimulatorEventType.PAYMENT_SUCCESS
    assert ev.amount == 120.0


def test_profile_needs_payment_link_unmatched():
    """Profile 2b: needs_payment_link without payment link requests one."""
    case = make_case("needs_payment_link")
    rng = random.Random(203)
    ev = respond(case, action="send_reminder", now=BASE_TIME, rng=rng)
    assert ev.event_type == SimulatorEventType.FREE_TEXT_REPLY
    assert "payment link" in ev.message.lower()


def test_profile_needs_card_update_matched():
    """Profile 3a: needs_card_update with card update request succeeds."""
    case = make_case("needs_card_update")
    rng = random.Random(303)
    ev = respond(case, action="request_card_update", now=BASE_TIME, rng=rng)
    assert ev.event_type == SimulatorEventType.PAYMENT_SUCCESS
    assert ev.amount == 120.0


def test_profile_needs_card_update_unmatched():
    """Profile 3b: needs_card_update without card action requests card update."""
    case = make_case("needs_card_update")
    rng = random.Random(304)
    ev = respond(case, action="send_reminder", now=BASE_TIME, rng=rng)
    assert ev.event_type == SimulatorEventType.FREE_TEXT_REPLY
    assert "card" in ev.message.lower()


def test_profile_prefers_split_matched():
    """Profile 4a: prefers_split with split offer succeeds."""
    case = make_case("prefers_split")
    rng = random.Random(404)
    ev = respond(case, action="offer_split_plan", now=BASE_TIME, rng=rng)
    assert ev.event_type == SimulatorEventType.PAYMENT_SUCCESS
    assert ev.amount == 120.0


def test_profile_prefers_split_unmatched():
    """Profile 4b: prefers_split without split offer asks for installments."""
    case = make_case("prefers_split")
    rng = random.Random(405)
    ev = respond(case, action="send_reminder", now=BASE_TIME, rng=rng)
    assert ev.event_type == SimulatorEventType.FREE_TEXT_REPLY
    assert "installment" in ev.message.lower() or "split" in ev.message.lower()


def test_profile_ignores_everything():
    """Profile 5: ignores_everything never pays across multiple attempts."""
    case = make_case("ignores_everything")
    for s in range(25):
        rng = random.Random(500 + s)
        ev = respond(case, action="send_payment_link", now=BASE_TIME, rng=rng)
        assert ev.event_type != SimulatorEventType.PAYMENT_SUCCESS
        assert ev.event_type in (SimulatorEventType.NOTHING, SimulatorEventType.OPT_OUT)


def test_profile_disputes_if_chased_early_chased_early():
    """Profile 6a: disputes_if_chased_early disputes when chased early (<3 days)."""
    # Due 1 day ago -> chased within 3-day quiet period
    case = make_case("disputes_if_chased_early", days_due=1)
    rng = random.Random(601)
    ev = respond(case, action="send_reminder", now=BASE_TIME, rng=rng, early_chase_days=3)
    assert ev.event_type == SimulatorEventType.DISPUTE
    assert ev.meta.get("chased_early") is True


def test_profile_disputes_if_chased_early_chased_late():
    """Profile 6b: disputes_if_chased_early converts normally after quiet window (>3 days)."""
    # Due 10 days ago -> beyond early chase window
    case = make_case("disputes_if_chased_early", days_due=10)
    rng = random.Random(602)
    ev = respond(case, action="send_reminder", now=BASE_TIME, rng=rng, early_chase_days=3)
    assert ev.event_type in (SimulatorEventType.PAYMENT_SUCCESS, SimulatorEventType.FREE_TEXT_REPLY)
    assert not ev.meta.get("chased_early")


def test_profile_already_paid_elsewhere():
    """Profile 7: already_paid_elsewhere flags any contact as wrongful contact."""
    case = make_case("already_paid_elsewhere")
    rng = random.Random(701)
    ev = respond(case, action="send_reminder", now=BASE_TIME, rng=rng)
    assert ev.event_type in (SimulatorEventType.FREE_TEXT_REPLY, SimulatorEventType.DISPUTE)
    assert ev.meta.get("is_wrongful_contact") is True
    assert ev.meta.get("wrongful_contact") is True
    assert "bank transfer" in ev.message.lower() or "dispute" in ev.message.lower()


# ── Determinism: Same Seed Gives Same Replies ─────────────────────────────────

def test_same_seed_gives_identical_replies():
    """Identical seed must yield identical event properties."""
    case = make_case("needs_payment_link", language="en")
    ev1 = respond(case, action="send_payment_link", now=BASE_TIME, rng=random.Random(42))
    ev2 = respond(case, action="send_payment_link", now=BASE_TIME, rng=random.Random(42))

    assert ev1.event_type == ev2.event_type
    assert ev1.amount == ev2.amount
    assert ev1.message == ev2.message
    assert ev1.timestamp == ev2.timestamp
    assert ev1.meta == ev2.meta


# ── Language Support: Hindi Reply ─────────────────────────────────────────────

def test_hindi_free_text_reply():
    """Customers with language=hi receive Hindi dialog replies."""
    case = make_case("needs_payment_link", language="hi")
    rng = random.Random(203)  # same seed that triggered unmatched free-text reply
    ev = respond(case, action="send_reminder", now=BASE_TIME, rng=rng)
    assert ev.event_type == SimulatorEventType.FREE_TEXT_REPLY
    # Verify presence of Devanagari script in Hindi response
    assert any("\u0900" <= ch <= "\u097f" for ch in ev.message)


# ── Assumptions Text for UI Honesty Panel ─────────────────────────────────────

def test_assumptions_text_content():
    """Verify assumptions_text returns comprehensive details for UI honesty panel."""
    text = assumptions_text()
    assert isinstance(text, str)
    assert "pays_after_one_reminder" in text
    assert "needs_payment_link" in text
    assert "needs_card_update" in text
    assert "prefers_split" in text
    assert "ignores_everything" in text
    assert "disputes_if_chased_early" in text
    assert "already_paid_elsewhere" in text
    assert "Quiet hours" in text or "quiet" in text.lower()


# ── Event Callback Dispatching ────────────────────────────────────────────────

def test_event_callback_delivery():
    """Events can be delivered to registered callback handlers."""
    clear_event_callbacks()
    received_events = []

    def on_event(ev: SimulatorEvent):
        received_events.append(ev)

    register_event_callback(on_event)

    test_ev = SimulatorEvent(
        event_type=SimulatorEventType.PAYMENT_SUCCESS,
        customer_id="CUST-0001",
        case_id="CASE-0001",
        timestamp=BASE_TIME,
        amount=50.0,
    )
    delivered = post_event(test_ev)
    assert delivered is True
    assert len(received_events) == 1
    assert received_events[0].amount == 50.0

    clear_event_callbacks()

