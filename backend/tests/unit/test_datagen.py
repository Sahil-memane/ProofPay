"""Unit tests for the datagen sub-package."""
from __future__ import annotations
import json
import random
from pathlib import Path
import pytest

from backend.app.simulator.datagen import generate
from backend.app.simulator.datagen.customers import generate_customers
from backend.app.simulator.datagen.subscriptions import generate_subscriptions
from backend.app.simulator.datagen.invoices import generate_invoices
from backend.app.simulator.datagen.records import generate_records
from backend.app.simulator.datagen.escrow import generate_escrow
from backend.app.simulator.datagen.traps import plant_traps
from backend.app.simulator.datagen.constants import (
    FAILURE_CODES, BEHAVIOUR_LABELS, TRAP_TYPES, IANA_TIMEZONES, LANGUAGES,
    AUTO_LIMIT_USD,
)

BASE = __import__("datetime").datetime(2025, 1, 1, tzinfo=__import__("datetime").timezone.utc)


# ── customers ─────────────────────────────────────────────────────────────────

def test_customer_count():
    rng = random.Random(42)
    custs = generate_customers(rng, n=120)
    assert len(custs) == 120


def test_customer_language_valid():
    rng = random.Random(42)
    custs = generate_customers(rng, n=50)
    for c in custs:
        assert c.language in LANGUAGES


def test_customer_timezone_valid():
    rng = random.Random(42)
    custs = generate_customers(rng, n=50)
    for c in custs:
        assert c.timezone in IANA_TIMEZONES


def test_customer_behaviour_valid():
    rng = random.Random(42)
    custs = generate_customers(rng, n=120)
    for c in custs:
        assert c.behaviour in BEHAVIOUR_LABELS


def test_some_customers_opted_out():
    rng = random.Random(42)
    custs = generate_customers(rng, n=200)
    assert any(c.opted_out for c in custs)


def test_all_behaviour_labels_represented():
    rng = random.Random(42)
    custs = generate_customers(rng, n=120)
    seen = {c.behaviour for c in custs}
    assert seen == set(BEHAVIOUR_LABELS)


# ── subscriptions ─────────────────────────────────────────────────────────────

def test_subscription_count():
    rng = random.Random(42)
    cids = [f"C-{i}" for i in range(20)]
    subs = generate_subscriptions(rng, cids, BASE, n=90)
    assert len(subs) == 90


def test_subscription_failure_codes():
    rng = random.Random(42)
    cids = [f"C-{i}" for i in range(20)]
    subs = generate_subscriptions(rng, cids, BASE, n=90)
    codes = {s.failure_code for s in subs}
    assert codes == set(FAILURE_CODES)


# ── invoices ──────────────────────────────────────────────────────────────────

def test_invoice_count():
    rng = random.Random(42)
    cids = [f"C-{i}" for i in range(20)]
    invs = generate_invoices(rng, cids, BASE, n=60)
    assert len(invs) == 60


def test_invoices_some_above_limit():
    rng = random.Random(42)
    cids = [f"C-{i}" for i in range(20)]
    invs = generate_invoices(rng, cids, BASE, n=60)
    above = [i for i in invs if i.above_auto_limit]
    assert len(above) >= 15
    for i in above:
        assert i.amount_usd > AUTO_LIMIT_USD


# ── records ───────────────────────────────────────────────────────────────────

def test_records_total_above_200():
    rng = random.Random(42)
    cids = [f"C-{i}" for i in range(20)]
    recs = generate_records(rng, cids, BASE)
    assert recs.total_records >= 200


def test_records_three_sources():
    rng = random.Random(42)
    cids = [f"C-{i}" for i in range(20)]
    recs = generate_records(rng, cids, BASE)
    assert len(recs.paypal_txns) > 0
    assert "sale_id" in recs.merchant_csv
    assert "entry_id" in recs.bank_csv


# ── escrow ────────────────────────────────────────────────────────────────────

def test_escrow_count():
    rng = random.Random(42)
    cids = [f"C-{i}" for i in range(20)]
    projects = generate_escrow(rng, cids, BASE, n=10)
    assert len(projects) == 10


def test_escrow_has_evidence():
    rng = random.Random(42)
    cids = [f"C-{i}" for i in range(20)]
    projects = generate_escrow(rng, cids, BASE, n=10)
    for p in projects:
        assert len(p.evidence_fixtures) >= 2


# ── traps ──────────────────────────────────────────────────────────────────────

def test_all_trap_types_planted():
    result = generate(seed=42, write=False)
    trap_types_found = {t.trap_type for t in result["traps"]}
    for tt in TRAP_TYPES:
        assert tt in trap_types_found, f"Missing trap type: {tt}"


def test_trap_count_reasonable():
    result = generate(seed=42, write=False)
    assert len(result["traps"]) >= len(TRAP_TYPES)


# ── counts correct on full generate ───────────────────────────────────────────

def test_generate_counts():
    result = generate(seed=42, write=False)
    assert len(result["customers"]) == 120
    assert len(result["subscriptions"]) == 90
    assert len(result["invoices"]) == 60
    assert result["records"].total_records >= 200
    assert len(result["escrow"]) == 10
    # Bank transfer traps around 15
    bank_traps = [t for t in result["traps"] if t.trap_type == "already_paid_by_bank_transfer"]
    assert len(bank_traps) == 15


# ── reproducibility (same seed gives identical files) ─────────────────────────

def test_same_seed_same_customers():
    r1 = generate(seed=42, write=False)
    r2 = generate(seed=42, write=False)
    ids1 = [c.customer_id for c in r1["customers"]]
    ids2 = [c.customer_id for c in r2["customers"]]
    assert ids1 == ids2
    assert [c.behaviour for c in r1["customers"]] == [c.behaviour for c in r2["customers"]]


def test_same_seed_same_traps():
    r1 = generate(seed=42, write=False)
    r2 = generate(seed=42, write=False)
    assert [t.trap_id for t in r1["traps"]] == [t.trap_id for t in r2["traps"]]


def test_different_seeds_differ():
    r1 = generate(seed=42, write=False)
    r2 = generate(seed=99, write=False)
    beh1 = [c.behaviour for c in r1["customers"]]
    beh2 = [c.behaviour for c in r2["customers"]]
    assert beh1 != beh2


def test_written_files_same_seed_identical(tmp_path):
    out1 = tmp_path / "run1" / "generated"
    key1 = tmp_path / "run1" / "key"
    out2 = tmp_path / "run2" / "generated"
    key2 = tmp_path / "run2" / "key"
    generate(seed=42, out_dir=out1, answer_key_dir=key1, write=True)
    generate(seed=42, out_dir=out2, answer_key_dir=key2, write=True)
    for fname in ["customers.json", "paypal_txns.json", "merchant_sales.csv", "bank_statement.csv", "escrow.json", "invoices.json", "subscriptions.json"]:
        assert (out1 / fname).read_text(encoding="utf-8") == (out2 / fname).read_text(encoding="utf-8"), f"Mismatch in generated: {fname}"
    for kfname in ["traps.json", "customers.yaml", "matches.yaml", "verifier.yaml"]:
        assert (key1 / kfname).read_text(encoding="utf-8") == (key2 / kfname).read_text(encoding="utf-8"), f"Mismatch in key: {kfname}"


def test_traps_json_has_all_types(tmp_path):
    out = tmp_path / "generated"
    key = tmp_path / "answer_key"
    generate(seed=42, out_dir=out, answer_key_dir=key, write=True)
    data = json.loads((key / "traps.json").read_text(encoding="utf-8"))
    found_types = {t["trap_type"] for t in data["traps"]}
    for tt in TRAP_TYPES:
        assert tt in found_types, f"Missing in traps.json: {tt}"
    # check that each trap has an id
    for t in data["traps"]:
        assert "trap_id" in t and t["trap_id"].startswith("TRAP-")

