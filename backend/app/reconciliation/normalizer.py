"""
Transaction normalizer.

Standardises raw transaction records from PayPal, shop (merchant CSV),
and bank statement CSV into canonical ReconRecord objects.
"""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


SUPPORTED_CURRENCIES = {"USD", "EUR", "GBP", "CAD", "AUD", "JPY", "SGD", "CHF"}


class NormalizationError(ValueError):
    pass


@dataclass
class ReconRecord:
    """Canonical representation of an external payment record across all sources."""
    source: str               # "paypal", "shop", "bank"
    external_id: str          # transaction ID, sale ID, entry ID
    amount: float
    currency: str
    date: datetime
    customer_ref: str         # customer_id or sender_id
    reference: str = ""
    status: str = "completed"
    raw_payload: dict[str, Any] = field(default_factory=dict)


def normalize_currency(raw: str) -> str:
    """Uppercase and validate a currency code."""
    code = raw.strip().upper()
    if code not in SUPPORTED_CURRENCIES:
        raise NormalizationError(f"Unsupported currency: {raw!r}")
    return code


def normalize_reference(ref: str) -> str:
    """Strip whitespace, uppercase, collapse internal spaces."""
    return re.sub(r"\s+", " ", ref.strip().upper())


def normalize_amount(amount: Any) -> float:
    """Round to 2 decimal places; reject non-positive values."""
    try:
        val = round(float(amount), 2)
    except (TypeError, ValueError) as e:
        raise NormalizationError(f"Invalid amount: {amount!r}") from e
    if val <= 0:
        raise NormalizationError(f"Amount must be positive, got {val}")
    return val


def normalize_timestamp(ts: Any) -> datetime:
    """Parse ISO string, date object, or pass-through datetime; ensure UTC."""
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    if isinstance(ts, date):
        return datetime(ts.year, ts.month, ts.day, 12, 0, 0, tzinfo=timezone.utc)
    if isinstance(ts, str):
        try:
            # Handles YYYY-MM-DD or full ISO
            if len(ts) == 10 and "-" in ts:
                d = date.fromisoformat(ts)
                return datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=timezone.utc)
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError as e:
            raise NormalizationError(f"Cannot parse timestamp: {ts!r}") from e
    raise NormalizationError(f"Unsupported timestamp type: {type(ts)}")


def normalize_transaction(raw: dict[str, Any]) -> dict[str, Any]:
    """Legacy helper for single-transaction dictionary normalization."""
    try:
        return {
            "txn_id": str(raw["txn_id"]).strip(),
            "customer_id": str(raw.get("customer_id", "")).strip(),
            "amount": normalize_amount(raw["amount"]),
            "currency": normalize_currency(raw["currency"]),
            "reference": normalize_reference(str(raw.get("reference", ""))),
            "timestamp": normalize_timestamp(raw["timestamp"]),
            "source_channel": str(raw.get("source_channel", "")).strip().lower(),
            "_normalized": True,
        }
    except KeyError as e:
        raise NormalizationError(f"Missing required field: {e}") from e


# ── Multi-Source Normalization Functions ─────────────────────────────────────

def normalize_paypal(data: list[dict[str, Any]] | str | Path) -> list[ReconRecord]:
    """Normalize PayPal JSON list into ReconRecords."""
    if isinstance(data, (str, Path)) and Path(str(data)).exists():
        with open(str(data), "r", encoding="utf-8") as f:
            items = json.load(f)
    elif isinstance(data, str):
        items = json.loads(data)
    else:
        items = data

    records: list[ReconRecord] = []
    for item in items:
        records.append(ReconRecord(
            source="paypal",
            external_id=str(item["txn_id"]).strip(),
            amount=normalize_amount(item["amount"]),
            currency=normalize_currency(item.get("currency", "USD")),
            date=normalize_timestamp(item["timestamp"]),
            customer_ref=str(item.get("customer_id", "")).strip(),
            reference=normalize_reference(str(item.get("reference", ""))),
            status=str(item.get("status", "completed")).lower(),
            raw_payload=item,
        ))
    return records


def normalize_shop_csv(csv_content: str | Path) -> list[ReconRecord]:
    """Normalize merchant_sales.csv into ReconRecords."""
    if isinstance(csv_content, (str, Path)) and Path(str(csv_content)).exists():
        with open(str(csv_content), "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    else:
        reader = csv.DictReader(io.StringIO(str(csv_content)))
        rows = list(reader)

    records: list[ReconRecord] = []
    for row in rows:
        records.append(ReconRecord(
            source="shop",
            external_id=str(row["sale_id"]).strip(),
            amount=normalize_amount(row["amount_usd"]),
            currency="USD",
            date=normalize_timestamp(row["date"]),
            customer_ref=str(row["customer_id"]).strip(),
            reference=f"SALE-{row['sale_id']}",
            status=str(row.get("status", "paid")).lower(),
            raw_payload=row,
        ))
    return records


def normalize_bank_csv(csv_content: str | Path) -> list[ReconRecord]:
    """Normalize bank_statement.csv into ReconRecords."""
    if isinstance(csv_content, (str, Path)) and Path(str(csv_content)).exists():
        with open(str(csv_content), "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    else:
        reader = csv.DictReader(io.StringIO(str(csv_content)))
        rows = list(reader)

    records: list[ReconRecord] = []
    for row in rows:
        records.append(ReconRecord(
            source="bank",
            external_id=str(row["entry_id"]).strip(),
            amount=normalize_amount(row["amount"]),
            currency=normalize_currency(row.get("currency", "USD")),
            date=normalize_timestamp(row["value_date"]),
            customer_ref=str(row["sender_id"]).strip(),
            reference=normalize_reference(str(row.get("description", ""))),
            status="completed",
            raw_payload=row,
        ))
    return records


def load_all_recon_records(data_dir: Path | None = None) -> list[ReconRecord]:
    """Load and normalize all transaction sources from data/generated/."""
    if data_dir is None:
        root = Path(__file__).resolve().parents[3]
        data_dir = root / "data" / "generated"

    records: list[ReconRecord] = []

    pp_path = data_dir / "paypal_txns.json"
    if pp_path.exists():
        records.extend(normalize_paypal(pp_path))

    shop_path = data_dir / "merchant_sales.csv"
    if shop_path.exists():
        records.extend(normalize_shop_csv(shop_path))

    bank_path = data_dir / "bank_statement.csv"
    if bank_path.exists():
        records.extend(normalize_bank_csv(bank_path))

    return records
