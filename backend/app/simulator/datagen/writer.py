"""Write generated datasets to disk. No answer-key logic here."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any


def _to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _to_dict(v) for k, v in asdict(obj).items()}
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, list):
        return [_to_dict(i) for i in obj]
    return obj


def write_generated(out_dir: Path, payload: dict[str, Any]) -> dict[str, Path]:
    """Write all generated data to out_dir. Returns {name: path}."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    # customers.json (public — no hidden behaviour label)
    custs = [
        {
            "customer_id": c.customer_id,
            "email": c.email,
            "language": c.language,
            "timezone": c.timezone,
            "opted_out": c.opted_out,
            "history": c.history,
        }
        for c in payload["customers"]
    ]
    p = out_dir / "customers.json"
    p.write_text(json.dumps(custs, indent=2), encoding="utf-8")
    written["customers"] = p

    # subscriptions.json
    subs = [_to_dict(s) for s in payload["subscriptions"]]
    p = out_dir / "subscriptions.json"
    p.write_text(json.dumps(subs, indent=2, default=str), encoding="utf-8")
    written["subscriptions"] = p

    # invoices.json (public)
    invs = [
        {k: _to_dict(v) for k, v in _to_dict(i).items() if k != "above_auto_limit"}
        for i in payload["invoices"]
    ]
    p = out_dir / "invoices.json"
    p.write_text(json.dumps(invs, indent=2, default=str), encoding="utf-8")
    written["invoices"] = p

    # paypal_txns.json
    p = out_dir / "paypal_txns.json"
    p.write_text(json.dumps(payload["records"].paypal_txns, indent=2), encoding="utf-8")
    written["paypal_txns"] = p

    # merchant_sales.csv
    p = out_dir / "merchant_sales.csv"
    p.write_text(payload["records"].merchant_csv, encoding="utf-8")
    written["merchant_sales"] = p

    # bank_statement.csv
    p = out_dir / "bank_statement.csv"
    p.write_text(payload["records"].bank_csv, encoding="utf-8")
    written["bank_statement"] = p

    # escrow.json
    escrows = [_to_dict(e) for e in payload["escrow"]]
    p = out_dir / "escrow.json"
    p.write_text(json.dumps(escrows, indent=2, default=str), encoding="utf-8")
    written["escrow"] = p

    return written

