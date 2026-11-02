"""Hypothesis property tests for reconciliation."""
from hypothesis import given, settings, strategies as st
from backend.app.reconciliation.matcher import score_pair


def make_norm_txn(txn_id, amount, currency, reference, customer_id="C1"):
    from datetime import datetime, timezone
    return {
        "txn_id": txn_id,
        "customer_id": customer_id,
        "amount": round(abs(amount) + 0.01, 2),
        "currency": currency,
        "reference": reference,
        "timestamp": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "source_channel": "test",
        "_normalized": True,
    }


@given(
    amount=st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False),
    ref=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Nd"))),
)
@settings(max_examples=40)
def test_identical_pair_high_score(amount, ref):
    inv = make_norm_txn("I1", amount, "USD", ref)
    pay = make_norm_txn("P1", amount, "USD", ref)
    r = score_pair(inv, pay)
    assert r.score >= 0.9


@given(
    cur1=st.sampled_from(["USD", "EUR", "GBP"]),
    cur2=st.sampled_from(["USD", "EUR", "GBP"]),
)
@settings(max_examples=20)
def test_currency_mismatch_not_matched(cur1, cur2):
    if cur1 == cur2:
        return
    inv = make_norm_txn("I1", 100.0, cur1, "REF")
    pay = make_norm_txn("P1", 100.0, cur2, "REF")
    r = score_pair(inv, pay)
    assert "currency_mismatch" in r.anomalies

