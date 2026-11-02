"""
Builds the full answer key.

answer_key/
  customers.yaml   — true behaviour profile per customer
  matches.yaml     — true record matches
  verifier.yaml    — expected verifier label per submission
  traps.json       — all trap records with unique IDs

IMPORTANT: this module may ONLY be imported by:
  - backend/app/simulator/
  - backend/app/reconciliation/metrics.py
  - backend/app/eval/
The AST test enforces this.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml


def _serialise(obj: Any) -> Any:
    """Recursively make obj JSON/YAML-safe."""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _serialise(v) for k, v in asdict(obj).items()}
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, list):
        return [_serialise(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _serialise(v) for k, v in obj.items()}
    return obj


def write_answer_key(
    answer_key_dir: Path,
    customers: list,
    invoices: list,
    paypal_txns: list[dict],
    traps: list,
) -> None:
    answer_key_dir.mkdir(parents=True, exist_ok=True)

    # 1. customers.yaml — true profile per customer
    cust_key = {
        c.customer_id: {
            "behaviour": c.behaviour,
            "timezone": c.timezone,
            "language": c.language,
            "opted_out": c.opted_out,
            "history": c.history,
        }
        for c in customers
    }
    (answer_key_dir / "customers.yaml").write_text(
        yaml.dump(cust_key, default_flow_style=False, allow_unicode=True),
        encoding="utf-8"
    )

    # 2. matches.yaml — expected invoice -> payment reference matches
    cust_to_txn: dict[str, str] = {}
    for t in paypal_txns:
        cust_to_txn.setdefault(t["customer_id"], t["txn_id"])

    matches = {
        inv.invoice_id: cust_to_txn.get(inv.customer_id, None)
        for inv in invoices
    }
    (answer_key_dir / "matches.yaml").write_text(
        yaml.dump(matches, default_flow_style=False),
        encoding="utf-8"
    )

    # 3. verifier.yaml — expected verifier outcome per customer
    verifier_labels = {
        "pays_after_one_reminder": "RECOVERED",
        "needs_payment_link": "ACTION_SENT",
        "needs_card_update": "ACTION_SENT",
        "prefers_split": "ACTION_PENDING_APPROVAL",
        "ignores_everything": "UNRECOVERED",
        "disputes_if_chased_early": "HALTED",
        "already_paid_elsewhere": "PAID_ELSEWHERE",
    }
    verifier = {
        c.customer_id: verifier_labels.get(c.behaviour, "OPEN")
        for c in customers
    }
    (answer_key_dir / "verifier.yaml").write_text(
        yaml.dump(verifier, default_flow_style=False),
        encoding="utf-8"
    )

    # 4. traps.json
    traps_data = [_serialise(t) for t in traps]
    (answer_key_dir / "traps.json").write_text(
        json.dumps({"traps": traps_data}, indent=2),
        encoding="utf-8"
    )

