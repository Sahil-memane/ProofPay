"""Unit tests for reconciliation sub-package."""
import pytest
from datetime import datetime, timezone

from backend.app.reconciliation.normalizer import (
    normalize_transaction, normalize_currency, normalize_amount,
    normalize_reference, NormalizationError,
)
from backend.app.reconciliation.matcher import score_pair, match_many, MatchResult
from backend.app.reconciliation.tiers import assign_tier, ReconciliationTier
from backend.app.reconciliation.metrics import compute_metrics


def make_txn(txn_id="T1", customer_id="C1", amount=100.0, currency="USD",
             reference="INV-001", ts=None):
    return {
        "txn_id": txn_id,
        "customer_id": customer_id,
        "amount": amount,
        "currency": currency,
        "reference": reference,
        "timestamp": ts or datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        "source_channel": "paypal",
    }


# ── normalizer ────────────────────────────────────────────────────────────────

def test_normalize_happy_path():
    raw = make_txn()
    n = normalize_transaction(raw)
    assert n["_normalized"] is True
    assert n["currency"] == "USD"
    assert n["amount"] == 100.0


def test_normalize_bad_currency():
    with pytest.raises(NormalizationError):
        normalize_currency("XYZ")


def test_normalize_negative_amount():
    with pytest.raises(NormalizationError):
        normalize_amount(-10.0)


def test_normalize_reference_cleans():
    assert normalize_reference("  inv 001  ") == "INV 001"


def test_normalize_timestamp_string():
    raw = make_txn(ts="2025-03-15T10:00:00+00:00")
    n = normalize_transaction(raw)
    assert n["timestamp"].tzinfo is not None


# ── matcher ───────────────────────────────────────────────────────────────────

def test_score_perfect_match():
    inv = make_txn("I1")
    pay = make_txn("P1")
    r = score_pair(normalize_transaction(inv), normalize_transaction(pay))
    assert r.score >= 0.95
    assert r.matched


def test_score_currency_mismatch():
    inv = normalize_transaction(make_txn("I1", currency="USD"))
    pay = normalize_transaction(make_txn("P1", currency="EUR"))
    r = score_pair(inv, pay)
    assert "currency_mismatch" in r.anomalies
    assert not r.matched


def test_score_amount_mismatch():
    inv = normalize_transaction(make_txn("I1", amount=100.0))
    pay = normalize_transaction(make_txn("P1", amount=50.0))
    r = score_pair(inv, pay)
    assert "amount_mismatch" in r.anomalies


def test_match_many_assigns_best():
    invoices = [normalize_transaction(make_txn("I1"))]
    payments = [
        normalize_transaction(make_txn("P1")),
        normalize_transaction(make_txn("P2", amount=999.0, currency="EUR")),
    ]
    results = match_many(invoices, payments)
    matched = [r for r in results if r.matched]
    assert len(matched) == 1
    assert matched[0].payment_id == "P1"


def test_match_many_unmatched_invoice():
    invoices = [normalize_transaction(make_txn("I1"))]
    payments = [normalize_transaction(make_txn("P1", amount=999.0, currency="EUR"))]
    results = match_many(invoices, payments)
    unmatched = [r for r in results if not r.matched]
    assert any(r.invoice_id == "I1" for r in unmatched)


# ── tiers ──────────────────────────────────────────────────────────────────────

def test_tier_high_for_large_unmatched():
    r = MatchResult(invoice_id="I1", payment_id="", score=0.0, matched=False,
                    anomalies=["no_match"])
    inv = {"amount": 600.0}
    assert assign_tier(r, inv) == ReconciliationTier.HIGH


def test_tier_low_for_small_matched():
    r = MatchResult(invoice_id="I1", payment_id="P1", score=0.95, matched=True,
                    anomalies=[])
    inv = {"amount": 50.0}
    assert assign_tier(r, inv) == ReconciliationTier.LOW


# ── metrics ───────────────────────────────────────────────────────────────────

def test_compute_metrics_perfect():
    results = [MatchResult("I1", "P1", 0.99, matched=True)]
    key = [{"txn_id": "I1", "match_id": "P1", "anomaly": "clean"}]
    m = compute_metrics(results, key)
    assert m.precision == 1.0
    assert m.recall == 1.0
    assert m.f1 == 1.0


def test_compute_metrics_false_positive():
    results = [MatchResult("I1", "P2", 0.8, matched=True)]
    key = [{"txn_id": "I1", "match_id": "P1", "anomaly": "clean"}]
    m = compute_metrics(results, key)
    assert m.precision == 0.0


def test_compute_metrics_false_negative():
    results = [MatchResult("I1", "", 0.0, matched=False, anomalies=["no_match"])]
    key = [{"txn_id": "I1", "match_id": "P1", "anomaly": "clean"}]
    m = compute_metrics(results, key)
    assert m.recall == 0.0

