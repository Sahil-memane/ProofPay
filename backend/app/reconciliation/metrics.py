"""
Reconciliation quality metrics.

Computes match rate, precision, recall against the answer key,
and aggregates an exception list with a diagnostic reason per record.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from backend.app.reconciliation.matcher import MatchResult


@dataclass
class ReconciliationMetrics:
    total: int
    matched: int
    unmatched: int
    anomaly_counts: dict[str, int]
    precision: float
    recall: float
    f1: float
    tier_distribution: dict[str, int]
    match_rate: float = 0.0
    exception_list: list[dict[str, Any]] = field(default_factory=list)


def compute_metrics(
    results: list[MatchResult],
    answer_key: list[dict[str, Any]] | dict[str, Any] | None = None,
) -> ReconciliationMetrics:
    """
    Compute reconciliation metrics against an answer key.
    Produces precision, recall, f1, match_rate, and an exception list with reasons.
    """
    # If answer_key is not passed, attempt to load from data/answer_key/matches.yaml
    key_map: dict[str, Any] = {}
    if answer_key is None:
        root = Path(__file__).resolve().parents[3]
        key_path = root / "data" / "answer_key" / "matches.yaml"
        if key_path.exists():
            with open(key_path, "r", encoding="utf-8") as f:
                key_map = yaml.safe_load(f) or {}
    elif isinstance(answer_key, list):
        key_map = {item.get("txn_id") or item.get("invoice_id"): item for item in answer_key}
    elif isinstance(answer_key, dict):
        key_map = answer_key

    tp = fp = fn = tn = 0
    anomaly_counts: dict[str, int] = {}
    exception_list: list[dict[str, Any]] = []

    for r in results:
        expected = key_map.get(r.invoice_id)
        expected_match_id = (
            expected.get("match_id") if isinstance(expected, dict)
            else expected
        )
        anomaly = (
            expected.get("anomaly", "clean") if isinstance(expected, dict)
            else ("has_anomaly" if r.anomalies else "clean")
        )
        anomaly_counts[anomaly] = anomaly_counts.get(anomaly, 0) + 1

        if r.matched:
            # Expected a match?
            if expected_match_id:
                if expected_match_id is True or r.payment_id == expected_match_id:
                    tp += 1
                else:
                    fp += 1
                    exception_list.append({
                        "record_id": r.invoice_id,
                        "payment_id": r.payment_id,
                        "reason": f"Mismatched expected payment ID (got {r.payment_id}, expected {expected_match_id})",
                    })
            else:
                fp += 1
                exception_list.append({
                    "record_id": r.invoice_id,
                    "payment_id": r.payment_id,
                    "reason": "Unexpected match (record had no expected payment)",
                })
        else:
            if expected_match_id:
                fn += 1
                exception_list.append({
                    "record_id": r.invoice_id,
                    "payment_id": r.payment_id,
                    "reason": f"Unmatched (expected payment {expected_match_id})",
                })
            else:
                tn += 1

    total = len(results)
    matched_count = sum(1 for r in results if r.matched)
    match_rate = round(matched_count / total, 4) if total > 0 else 0.0

    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if total > 0 and fp == 0 and fn == 0 else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if total > 0 and fp == 0 and fn == 0 else 0.0)
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) > 0 else 0.0)

    return ReconciliationMetrics(
        total=total,
        matched=matched_count,
        unmatched=total - matched_count,
        anomaly_counts=anomaly_counts,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        tier_distribution={},
        match_rate=match_rate,
        exception_list=exception_list,
    )
