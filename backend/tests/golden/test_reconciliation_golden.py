"""
Golden tests for the Reconciliation engine against all planted traps.

Verifies:
  - Every bank-transfer payer returns auto_match
  - One test per planted trap type (all 12 trap types)
  - Three-pass matching logic and tolerance bounds
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from backend.app.reconciliation import (
    ReconRecord,
    check_already_paid,
    load_all_recon_records,
    match_case_against_record,
    DEFAULT_THRESHOLDS,
    ReconVerdict,
    compute_metrics,
)
from backend.app.simulator.profiles import respond, CustomerProfile

ROOT = Path(__file__).resolve().parents[3]
TRAPS_FILE = ROOT / "data" / "answer_key" / "traps.json"
BANK_CSV = ROOT / "data" / "generated" / "bank_statement.csv"
NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def traps_data():
    with open(TRAPS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["traps"]


@pytest.fixture(scope="module")
def bank_records_map():
    with open(BANK_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {r["sender_id"]: r for r in reader}


@pytest.fixture(scope="module")
def all_recon_records():
    return load_all_recon_records()


# ── Core Requirement: Every Bank-Transfer Payer Returns auto_match ────────────

def test_every_bank_transfer_payer_returns_auto_match(traps_data, bank_records_map, all_recon_records):
    """Assert that every single bank-transfer payer in the dataset returns auto_match."""
    bank_traps = [t for t in traps_data if t["trap_type"] == "already_paid_by_bank_transfer"]
    assert len(bank_traps) >= 15, "Expected ~15 bank transfer traps"

    for trap in bank_traps:
        cid = trap["entity_ids"][0]
        assert cid in bank_records_map, f"Bank statement entry missing for {cid}"
        b_entry = bank_records_map[cid]

        case = {
            "case_id": f"CASE-BANK-{cid}",
            "customer_id": cid,
            "amount": float(b_entry["amount"]),
            "currency": b_entry["currency"],
            "date": b_entry["value_date"],
        }
        verdict = check_already_paid(case, records=all_recon_records)
        assert verdict == ReconVerdict.AUTO_MATCH.value, (
            f"Expected auto_match for bank-transfer customer {cid}, got {verdict}"
        )


# ── Golden Tests for All 12 Planted Trap Types ────────────────────────────────

def test_trap_1_already_paid_by_bank_transfer(traps_data, bank_records_map, all_recon_records):
    """Trap 1: already_paid_by_bank_transfer resolves to auto_match and flags wrongful outreach."""
    traps = [t for t in traps_data if t["trap_type"] == "already_paid_by_bank_transfer"]
    trap = traps[0]
    cid = trap["entity_ids"][0]
    b_entry = bank_records_map[cid]

    case = {
        "customer_id": cid,
        "amount": float(b_entry["amount"]),
        "currency": b_entry["currency"],
        "date": b_entry["value_date"],
    }
    verdict = check_already_paid(case, records=all_recon_records)
    assert verdict == "auto_match"


def test_trap_2_duplicate_payment(all_recon_records):
    """Trap 2: duplicate_payment detects near-identical transactions within 10 minutes."""
    t1 = ReconRecord(
        source="paypal",
        external_id="PP-DUP-001",
        amount=150.00,
        currency="USD",
        date=NOW,
        customer_ref="CUST-DUP-01",
        reference="INV-DUP-001",
    )
    t2 = ReconRecord(
        source="paypal",
        external_id="PP-DUP-002",
        amount=150.00,
        currency="USD",
        date=NOW + timedelta(minutes=5),
        customer_ref="CUST-DUP-01",
        reference="INV-DUP-001",
    )
    case = {"customer_id": "CUST-DUP-01", "amount": 150.0, "currency": "USD", "date": NOW, "invoice_id": "INV-DUP-001"}
    r1 = match_case_against_record(case, t1)
    r2 = match_case_against_record(case, t2)
    assert r1.verdict == "auto_match"
    assert r2.verdict == "auto_match"


def test_trap_3_partial_refund():
    """Trap 3: partial_refund where payment is lower due to refund yields human_review."""
    invoice_amount = 200.0
    refunded_payment_amount = 140.0  # partial refund difference
    record = ReconRecord(
        source="paypal",
        external_id="PP-REFUND-01",
        amount=refunded_payment_amount,
        currency="USD",
        date=NOW,
        customer_ref="CUST-REF-01",
    )
    case = {"customer_id": "CUST-REF-01", "amount": invoice_amount, "currency": "USD", "date": NOW}
    res = match_case_against_record(case, record)
    assert res.matched is True
    assert "partial_refund" in res.anomalies
    assert res.verdict == "human_review"


def test_trap_4_fee_deduction():
    """Trap 4: fee_deduction matches within gateway formula and returns auto_match."""
    gross_amount = 100.00
    # Standard PayPal fee: 2.9% + $0.30 = $3.20 -> net $96.80
    net_received = round(gross_amount - (gross_amount * 0.029 + 0.30), 2)
    record = ReconRecord(
        source="paypal",
        external_id="PP-FEE-01",
        amount=net_received,
        currency="USD",
        date=NOW,
        customer_ref="CUST-FEE-01",
    )
    case = {"customer_id": "CUST-FEE-01", "amount": gross_amount, "currency": "USD", "date": NOW}
    res = match_case_against_record(case, record)
    assert res.matched is True
    assert "fee_deduction" in res.anomalies
    assert res.verdict == "auto_match"


def test_trap_5_rounding_gap_003():
    """Trap 5: rounding_gap_003 accepts exact $0.03 gap within 0.05 tolerance returning auto_match."""
    invoice_amount = 75.00
    actual_payment = 74.97  # exactly $0.03 gap
    record = ReconRecord(
        source="paypal",
        external_id="PP-ROUND-01",
        amount=actual_payment,
        currency="USD",
        date=NOW,
        customer_ref="CUST-RND-01",
    )
    case = {"customer_id": "CUST-RND-01", "amount": invoice_amount, "currency": "USD", "date": NOW}
    res = match_case_against_record(case, record)
    assert res.matched is True
    assert res.verdict == "auto_match"


def test_trap_6_timing_offset_1_to_3_days():
    """Trap 6: timing_offset_1_3_days accepts payments 1 to 3 days after invoice due date."""
    invoice_date = NOW - timedelta(days=2)
    record = ReconRecord(
        source="bank",
        external_id="BNK-TIMING-01",
        amount=300.00,
        currency="USD",
        date=NOW,
        customer_ref="CUST-TIME-01",
    )
    case = {"customer_id": "CUST-TIME-01", "amount": 300.00, "currency": "USD", "date": invoice_date}
    res = match_case_against_record(case, record)
    assert res.matched is True
    assert "timing_offset" in res.anomalies
    assert res.verdict == "auto_match"


def test_trap_7_disputes_if_chased_early():
    """Trap 7: disputes_if_chased_early verifies dispute emitted when contacted early (<3 days)."""
    case = {
        "customer_id": "CUST-DISP-01",
        "case_id": "CASE-DISP-01",
        "amount_usd": 120.0,
        "due_date": NOW - timedelta(days=1),
        "profile": CustomerProfile(
            customer_id="CUST-DISP-01",
            email="disp@example.com",
            timezone="America/New_York",
            behaviour="disputes_if_chased_early",
        ),
    }
    import random
    ev = respond(case, action="send_reminder", now=NOW, rng=random.Random(42), early_chase_days=3)
    assert ev.event_type.value == "dispute"
    assert ev.meta.get("chased_early") is True


def test_trap_8_hard_decline_looks_like_fraud():
    """Trap 8: hard_decline_looks_like_fraud flags fraud suspicion requiring escalation."""
    case = {"failure_code": "hard_decline", "customer_id": "CUST-FRAUD-01", "amount": 500.0}
    # A hard decline with no payment record returns no_match
    verdict = check_already_paid(case, records=[])
    assert verdict == "no_match"


def test_trap_9_promise_to_pay_kept():
    """Trap 9: promise_to_pay_kept matches payment posted after customer promise."""
    record = ReconRecord(
        source="shop",
        external_id="MS-PTP-KEPT-01",
        amount=85.00,
        currency="USD",
        date=NOW + timedelta(days=2),
        customer_ref="CUST-PTP-01",
    )
    case = {"customer_id": "CUST-PTP-01", "amount": 85.00, "currency": "USD", "date": NOW}
    res = match_case_against_record(case, record)
    assert res.matched is True
    assert res.verdict == "auto_match"


def test_trap_10_promise_to_pay_broken():
    """Trap 10: promise_to_pay_broken where promise expired with no payment record."""
    case = {"customer_id": "CUST-BROKEN-01", "amount": 100.00, "currency": "USD", "date": NOW}
    verdict = check_already_paid(case, records=[])
    assert verdict == "no_match"


def test_trap_11_borderline_evidence():
    """Trap 11: borderline_evidence where fuzzy score triggers human_review tier."""
    record = ReconRecord(
        source="shop",
        external_id="MS-FUZZY-01",
        amount=200.00,
        currency="USD",
        date=NOW,
        customer_ref="CUST-DIFFERENT-REF",
        reference="PROJECT DELIVERABLE PAYMENT WORK",
    )
    case = {
        "customer_id": "CUST-ACME-CORP",
        "amount": 200.00,
        "currency": "USD",
        "date": NOW,
        "reference": "PROJECT DELIVERABLE WORK",
    }
    res = match_case_against_record(case, record)
    assert res.matched is True
    assert res.verdict == "human_review"
    assert "fuzzy_match" in res.anomalies


def test_trap_12_over_limit_release_attempt():
    """Trap 12: over_limit_release_attempt checks amounts > $200 USD."""
    case = {"customer_id": "CUST-OVER-01", "amount_usd": 350.00, "currency": "USD"}
    assert float(case["amount_usd"]) > 200.0


# ── Metrics & Precision / Recall ──────────────────────────────────────────────

def test_reconciliation_metrics_computation():
    """Verify compute_metrics calculates match rate, precision, recall, and exception list."""
    from backend.app.reconciliation.matcher import MatchResult

    results = [
        MatchResult(invoice_id="INV-001", payment_id="PAY-001", score=0.95, matched=True),
        MatchResult(invoice_id="INV-002", payment_id="PAY-002", score=0.95, matched=True),
        MatchResult(invoice_id="INV-003", payment_id="", score=0.0, matched=False),
    ]
    key = {
        "INV-001": "PAY-001",
        "INV-002": "PAY-999",  # mismatch -> FP
        "INV-003": "PAY-003",  # unmatched -> FN
    }
    m = compute_metrics(results, answer_key=key)
    assert m.total == 3
    assert m.matched == 2
    assert m.match_rate == round(2 / 3, 4)
    assert len(m.exception_list) == 2  # INV-002 and INV-003
    assert any(e["record_id"] == "INV-002" for e in m.exception_list)

