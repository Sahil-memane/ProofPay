"""Unit tests for simulator sub-package."""
import pytest
from datetime import datetime, timezone
from backend.app.simulator.datagen.generator import (
    generate_dataset, AnomalyKind, TransactionRecord,
)
from backend.app.simulator.profiles import (
    generate_profiles, CustomerProfile, is_quiet_hours as _iqh,
)
from backend.app.simulator.sim_events import (
    simulate_response, is_quiet_hours, EventKind,
)


# ── datagen ───────────────────────────────────────────────────────────────────

def test_generate_dataset_count():
    invs, pays = generate_dataset(n_cases=50, seed=0)
    assert len(invs) == 50
    # payments >= 50 (duplicates add extra)
    assert len(pays) >= 50


def test_generate_dataset_anomalies():
    invs, pays = generate_dataset(n_cases=100, anomaly_rate=1.0, seed=7)
    anomalies = [p for p in pays if p.anomaly != AnomalyKind.CLEAN]
    assert len(anomalies) > 0


def test_generate_dataset_no_anomalies():
    invs, pays = generate_dataset(n_cases=50, anomaly_rate=0.0, seed=1)
    for p in pays:
        assert p.anomaly == AnomalyKind.CLEAN


def test_public_dict_hides_customer_id():
    invs, _ = generate_dataset(n_cases=5, seed=2)
    for inv in invs:
        pub = inv.to_public_dict()
        assert inv.customer_id not in pub.values()
        assert "anomaly" not in pub


def test_answer_key_has_anomaly():
    invs, pays = generate_dataset(n_cases=20, anomaly_rate=1.0, seed=3)
    keys = [p.to_answer_key_dict() for p in pays]
    anomaly_kinds = {k["anomaly"] for k in keys}
    assert len(anomaly_kinds) > 1  # multiple anomaly types


def test_reproducible_seed():
    a, _ = generate_dataset(n_cases=10, seed=99)
    b, _ = generate_dataset(n_cases=10, seed=99)
    assert [r.txn_id for r in a] == [r.txn_id for r in b]


# ── profiles ──────────────────────────────────────────────────────────────────

def test_generate_profiles_count():
    profiles = generate_profiles(100, seed=0)
    assert len(profiles) == 100


def test_profiles_fields():
    profiles = generate_profiles(10, seed=1)
    for p in profiles:
        assert 0.0 <= p.payment_reliability <= 1.0
        assert p.risk_tier in ("low", "medium", "high")


def test_some_opted_out():
    profiles = generate_profiles(1000, seed=42)
    opted = [p for p in profiles if p.opted_out]
    assert 0 < len(opted) < 100  # ~5%


# ── sim_events ────────────────────────────────────────────────────────────────

def test_quiet_hours_night():
    # 22:00 UTC in New_York (UTC-5) → 17:00 local → NOT quiet
    # 22:00 UTC in Tokyo (UTC+9) → 07:00 local → quiet (07 < 08)
    t = datetime(2025, 6, 1, 22, 0, 0, tzinfo=timezone.utc)
    assert is_quiet_hours(t, "Asia/Tokyo") is True
    assert is_quiet_hours(t, "America/New_York") is False


def test_quiet_hours_early_morning():
    # 07:00 UTC in London (UTC+0) → 07:00 local → quiet (07 < 08)
    t = datetime(2025, 6, 1, 7, 0, 0, tzinfo=timezone.utc)
    assert is_quiet_hours(t, "Europe/London") is True


def test_opted_out_customer():
    profile = CustomerProfile(
        customer_id="C1", email="x@x.com", timezone="Europe/London",
        opted_out=True, payment_reliability=0.9,
    )
    import random
    t = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    evt = simulate_response(profile, "case-1", 100.0, t, rng=random.Random(0))
    assert evt.kind == EventKind.OPT_OUT


def test_reliable_customer_pays():
    import random
    profile = CustomerProfile(
        customer_id="C2", email="x@x.com", timezone="Europe/London",
        opted_out=False, payment_reliability=1.0,
    )
    t = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    evt = simulate_response(profile, "case-2", 50.0, t, rng=random.Random(0))
    assert evt.kind in (EventKind.PAYMENT_RECEIVED, EventKind.PARTIAL_PAYMENT)
