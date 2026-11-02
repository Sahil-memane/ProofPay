"""
Main entry point for the ProofPay synthetic data generator.

Usage:
    from backend.app.simulator.datagen import generate
    result = generate(seed=42)   # identical every run
"""
from __future__ import annotations

import csv
import hashlib
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from .customers import generate_customers, Customer
from .subscriptions import generate_subscriptions, FailedSubscription
from .invoices import generate_invoices, OverdueInvoice
from .records import generate_records, RecordSet
from .escrow import generate_escrow, EscrowProject
from .traps import plant_traps, Trap
from .answer_key import write_answer_key
from .writer import write_generated


BASE_TIME = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

# Path to root of repository (d:/paypal)
ROOT = Path(__file__).resolve().parents[4]
GENERATED_DIR = ROOT / "data" / "generated"
ANSWER_KEY_DIR = ROOT / "data" / "answer_key"


def generate(
    seed: int = 42,
    n_customers: int = 120,
    n_subscriptions: int = 90,
    n_invoices: int = 60,
    out_dir: Path | None = None,
    answer_key_dir: Path | None = None,
    write: bool = True,
) -> dict[str, Any]:
    """
    Generate the full ProofPay synthetic dataset using only random.Random(seed).
    Identical seed produces identical output on every run.
    """
    rng = random.Random(seed)

    customers = generate_customers(rng, n=n_customers)
    cids = [c.customer_id for c in customers]

    subscriptions = generate_subscriptions(rng, cids, BASE_TIME, n=n_subscriptions)
    invoices = generate_invoices(rng, cids, BASE_TIME, n=n_invoices)
    records = generate_records(rng, cids, BASE_TIME)
    escrow = generate_escrow(rng, cids, BASE_TIME)
    traps = plant_traps(rng, cids, records.paypal_txns, invoices)

    # Ensure every bank-transfer payer has a corresponding bank statement entry
    bank_lines = records.bank_csv.strip().splitlines()
    existing_senders = {line.split(",")[1].strip() for line in bank_lines[1:] if "," in line}
    inv_map = {inv.customer_id: inv for inv in invoices}
    sub_map = {sub.customer_id: sub for sub in subscriptions}

    bank_paid_cids = {t.entity_ids[0] for t in traps if t.trap_type == "already_paid_by_bank_transfer"}

    # Align customer behaviour and plant bank statement records for all already_paid customers
    appended_bank_lines = []
    entry_counter = 0
    for c in customers:
        if c.customer_id in bank_paid_cids:
            c.behaviour = "already_paid_elsewhere"
        if c.behaviour == "already_paid_elsewhere":
            cust_invs = [inv for inv in invoices if inv.customer_id == c.customer_id]
            cust_subs = [sub for sub in subscriptions if sub.customer_id == c.customer_id]

            if not cust_invs and not cust_subs:
                entry_counter += 1
                entry_id = f"BNK-BT-{c.customer_id.replace('CUST-', '')}-{entry_counter}"
                appended_bank_lines.append(f"{entry_id},{c.customer_id},125.00,USD,2025-01-15,BANK TRANSFER PAYMENT")

            for inv in cust_invs:
                entry_counter += 1
                amt = getattr(inv, "amount_usd", 100.0)
                cur = getattr(inv, "currency", "USD")
                dt = getattr(inv, "due_at", BASE_TIME)
                d_str = dt.date().isoformat() if hasattr(dt, "date") else str(dt)[:10]
                entry_id = f"BNK-BT-{c.customer_id.replace('CUST-', '')}-{entry_counter}"
                appended_bank_lines.append(f"{entry_id},{c.customer_id},{amt:.2f},{cur},{d_str},BANK TRANSFER PAYMENT {inv.invoice_id}")

            for sub in cust_subs:
                entry_counter += 1
                amt = getattr(sub, "amount_usd", 50.0)
                cur = getattr(sub, "currency", "USD")
                dt = getattr(sub, "failed_at", BASE_TIME)
                d_str = dt.date().isoformat() if hasattr(dt, "date") else str(dt)[:10]
                entry_id = f"BNK-BT-{c.customer_id.replace('CUST-', '')}-{entry_counter}"
                appended_bank_lines.append(f"{entry_id},{c.customer_id},{amt:.2f},{cur},{d_str},BANK TRANSFER PAYMENT {sub.sub_id}")

    if appended_bank_lines:
        records.bank_csv = records.bank_csv.strip() + "\n" + "\n".join(appended_bank_lines) + "\n"

    payload: dict[str, Any] = {
        "customers": customers,
        "subscriptions": subscriptions,
        "invoices": invoices,
        "records": records,
        "escrow": escrow,
        "traps": traps,
    }

    written: dict[str, Path] = {}
    if write:
        _out = out_dir if out_dir is not None else GENERATED_DIR
        _key = answer_key_dir if answer_key_dir is not None else ANSWER_KEY_DIR
        written = write_generated(_out, payload)
        write_answer_key(_key, customers, invoices, records.paypal_txns, traps)

    payload["written_paths"] = written
    return payload


# ── Backward-compatible dataset generation for existing unit tests ──────────

class AnomalyKind(str):
    DUPLICATE = "duplicate"
    AMOUNT_MISMATCH = "amount_mismatch"
    CURRENCY_MISMATCH = "currency_mismatch"
    MISSING_REF = "missing_ref"
    CLEAN = "clean"


CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD"]
CHANNELS_SRC = ["paypal", "stripe", "bank_transfer", "card"]


@dataclass
class TransactionRecord:
    txn_id: str
    customer_id: str
    amount: float
    currency: str
    source_channel: str
    timestamp: datetime
    reference: str
    anomaly: str = AnomalyKind.CLEAN
    _expected_state: str = field(default="RECONCILING", repr=False)
    _match_id: str | None = field(default=None, repr=False)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "txn_id": self.txn_id,
            "customer_id": hashlib.sha256(self.customer_id.encode()).hexdigest()[:12],
            "amount": self.amount,
            "currency": self.currency,
            "source_channel": self.source_channel,
            "timestamp": self.timestamp.isoformat(),
            "reference": self.reference,
        }

    def to_answer_key_dict(self) -> dict[str, Any]:
        return {
            "txn_id": self.txn_id,
            "customer_id": self.customer_id,
            "anomaly": self.anomaly,
            "expected_state": self._expected_state,
            "match_id": self._match_id,
        }


def generate_dataset(
    n_cases: int = 200,
    anomaly_rate: float = 0.25,
    seed: int = 42,
    base_time: datetime | None = None,
) -> tuple[list[TransactionRecord], list[TransactionRecord]]:
    rng = random.Random(seed)
    base = base_time or datetime(2025, 1, 1, tzinfo=timezone.utc)

    invoices: list[TransactionRecord] = []
    payments: list[TransactionRecord] = []

    for i in range(n_cases):
        cust_id = f"CUST-{i:05d}"
        inv_id = str(uuid.UUID(int=rng.getrandbits(128)))
        pay_id = str(uuid.UUID(int=rng.getrandbits(128)))
        ref = f"INV-{i:06d}"
        amount = round(rng.uniform(10.0, 2000.0), 2)
        currency = rng.choice(CURRENCIES)
        channel = rng.choice(CHANNELS_SRC)
        delta = timedelta(seconds=rng.randint(0, 720 * 3600))
        ts_inv = base + delta
        ts_pay = ts_inv + timedelta(hours=rng.randint(1, 72))

        inv = TransactionRecord(
            txn_id=inv_id,
            customer_id=cust_id,
            amount=amount,
            currency=currency,
            source_channel=channel,
            timestamp=ts_inv,
            reference=ref,
            anomaly=AnomalyKind.CLEAN,
            _expected_state="RECONCILING",
            _match_id=pay_id,
        )

        roll = rng.random()
        if roll < anomaly_rate:
            kind = rng.choice([
                AnomalyKind.DUPLICATE,
                AnomalyKind.AMOUNT_MISMATCH,
                AnomalyKind.CURRENCY_MISMATCH,
                AnomalyKind.MISSING_REF,
            ])
        else:
            kind = AnomalyKind.CLEAN

        pay_amount = amount
        pay_currency = currency
        pay_ref = ref

        if kind == AnomalyKind.AMOUNT_MISMATCH:
            pay_amount = round(amount * rng.uniform(0.5, 1.5), 2)
        elif kind == AnomalyKind.CURRENCY_MISMATCH:
            alts = [c for c in CURRENCIES if c != currency]
            pay_currency = rng.choice(alts)
        elif kind == AnomalyKind.MISSING_REF:
            pay_ref = ""
        elif kind == AnomalyKind.DUPLICATE:
            dup_id = str(uuid.UUID(int=rng.getrandbits(128)))
            dup = TransactionRecord(
                txn_id=dup_id,
                customer_id=cust_id,
                amount=amount,
                currency=currency,
                source_channel=channel,
                timestamp=ts_pay + timedelta(minutes=5),
                reference=ref,
                anomaly=AnomalyKind.DUPLICATE,
                _expected_state="DIAGNOSED",
                _match_id=inv_id,
            )
            payments.append(dup)

        expected_state = "RECOVERED" if kind == AnomalyKind.CLEAN else "DIAGNOSED"

        pay = TransactionRecord(
            txn_id=pay_id,
            customer_id=cust_id,
            amount=pay_amount,
            currency=pay_currency,
            source_channel=channel,
            timestamp=ts_pay,
            reference=pay_ref,
            anomaly=kind,
            _expected_state=expected_state,
            _match_id=inv_id,
        )

        invoices.append(inv)
        payments.append(pay)

    return invoices, payments


def write_dataset(
    out_dir: Path,
    answer_key_dir: Path,
    n_cases: int = 200,
    anomaly_rate: float = 0.25,
    seed: int = 42,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    answer_key_dir.mkdir(parents=True, exist_ok=True)

    invoices, payments = generate_dataset(n_cases=n_cases, anomaly_rate=anomaly_rate, seed=seed)

    inv_path = out_dir / "invoices.csv"
    pay_path = out_dir / "payments.csv"
    key_path = answer_key_dir / "answer_key.yaml"

    with inv_path.open("w", newline="", encoding="utf-8") as f:
        if invoices:
            w = csv.DictWriter(f, fieldnames=list(invoices[0].to_public_dict().keys()))
            w.writeheader()
            w.writerows(r.to_public_dict() for r in invoices)

    with pay_path.open("w", newline="", encoding="utf-8") as f:
        if payments:
            w = csv.DictWriter(f, fieldnames=list(payments[0].to_public_dict().keys()))
            w.writeheader()
            w.writerows(r.to_public_dict() for r in payments)

    answer_key = {
        "invoices": [r.to_answer_key_dict() for r in invoices],
        "payments": [r.to_answer_key_dict() for r in payments],
        "meta": {
            "n_cases": n_cases,
            "anomaly_rate": anomaly_rate,
            "seed": seed,
        },
    }
    with key_path.open("w", encoding="utf-8") as f:
        yaml.dump(answer_key, f, default_flow_style=False)

    return {"invoices": inv_path, "payments": pay_path, "answer_key": key_path}
