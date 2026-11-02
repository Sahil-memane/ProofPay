"""
Generate three record sources:
  - PayPal-format transactions (list of dicts)
  - merchant_sales.csv  (CSV string)
  - bank_statement.csv  (CSV string)
Total across all three sources >= 200 records.
"""
from __future__ import annotations
import csv
import io
import random
from dataclasses import dataclass
from datetime import datetime
from ._rng_helpers import rng_uuid, rng_amount, rng_ts, rng_choice

CURRENCIES = ["USD", "EUR", "GBP", "CAD"]
PP_STATUS = ["completed", "pending", "refunded", "reversed"]
MERCHANT_CATS = ["SaaS", "eCommerce", "Freelance", "Marketplace"]


@dataclass
class RecordSet:
    paypal_txns: list[dict]         # list of dicts (JSON-serialisable)
    merchant_csv: str               # raw CSV text
    bank_csv: str                   # raw CSV text

    @property
    def total_records(self) -> int:
        merchant_lines = self.merchant_csv.strip().splitlines()
        bank_lines = self.bank_csv.strip().splitlines()
        return (
            len(self.paypal_txns)
            + max(0, len(merchant_lines) - 1)   # minus header
            + max(0, len(bank_lines) - 1)
        )


def _make_paypal_txns(rng: random.Random, customer_ids: list[str], base: datetime, n: int) -> list[dict]:
    rows = []
    for _ in range(n):
        cid = rng_choice(rng, customer_ids)
        rows.append({
            "txn_id": rng_uuid(rng),
            "customer_id": cid,
            "amount": rng_amount(rng, 5.0, 1000.0),
            "currency": rng_choice(rng, CURRENCIES),
            "status": rng_choice(rng, PP_STATUS),
            "timestamp": rng_ts(rng, base, 90).isoformat(),
            "reference": f"PP-{rng.randint(100000, 999999)}",
        })
    return rows


def _make_merchant_csv(rng: random.Random, customer_ids: list[str], base: datetime, n: int) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["sale_id", "customer_id", "amount_usd", "category", "date", "status"])
    for _ in range(n):
        cid = rng_choice(rng, customer_ids)
        writer.writerow([
            f"MS-{rng.randint(10000, 99999)}",
            cid,
            round(rng_amount(rng, 5.0, 500.0), 2),
            rng_choice(rng, MERCHANT_CATS),
            rng_ts(rng, base, 90).date().isoformat(),
            rng_choice(rng, ["paid", "pending", "failed"]),
        ])
    return buf.getvalue()


def _make_bank_csv(rng: random.Random, customer_ids: list[str], base: datetime, n: int) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["entry_id", "sender_id", "amount", "currency", "value_date", "description"])
    for _ in range(n):
        cid = rng_choice(rng, customer_ids)
        writer.writerow([
            f"BNK-{rng.randint(100000, 999999)}",
            cid,
            round(rng_amount(rng, 1.0, 2000.0), 2),
            rng_choice(rng, ["USD", "EUR", "GBP"]),
            rng_ts(rng, base, 90).date().isoformat(),
            rng_choice(rng, ["PAYMENT REF", "BANK TRANSFER", "WIRE TRANSFER", "ACH DEBIT"]),
        ])
    return buf.getvalue()


def generate_records(
    rng: random.Random,
    customer_ids: list[str],
    base_time: datetime,
    pp_n: int = 80,
    merchant_n: int = 70,
    bank_n: int = 70,
) -> RecordSet:
    return RecordSet(
        paypal_txns=_make_paypal_txns(rng, customer_ids, base_time, pp_n),
        merchant_csv=_make_merchant_csv(rng, customer_ids, base_time, merchant_n),
        bank_csv=_make_bank_csv(rng, customer_ids, base_time, bank_n),
    )

