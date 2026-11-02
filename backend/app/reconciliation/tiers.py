"""
Risk tier and confidence classification for reconciliation cases.

Maps match confidence scores into operational decision tiers:
  - auto_match: 0.90 and up
  - human_review: 0.60 to 0.89
  - exception / no_match: below 0.60
"""
from __future__ import annotations

from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.reconciliation.matcher import MatchResult


# ── Operational Confidence Thresholds ────────────────────────────────────────

DEFAULT_THRESHOLDS: dict[str, float] = {
    "auto_match": 0.90,
    "human_review": 0.60,
}


class ReconVerdict(str, Enum):
    AUTO_MATCH = "auto_match"
    HUMAN_REVIEW = "human_review"
    EXCEPTION = "exception"
    NO_MATCH = "no_match"


def classify_confidence(
    confidence: float,
    thresholds: dict[str, float] | None = None,
) -> str:
    """
    Map confidence score (0.0 to 1.0) to decision tier:
      - auto_match (>= 0.90)
      - human_review (0.60 to 0.89)
      - exception (< 0.60)
    """
    th = thresholds or DEFAULT_THRESHOLDS
    if confidence >= th.get("auto_match", 0.90):
        return ReconVerdict.AUTO_MATCH.value
    elif confidence >= th.get("human_review", 0.60):
        return ReconVerdict.HUMAN_REVIEW.value
    else:
        return ReconVerdict.EXCEPTION.value


# ── Legacy Risk Tiering (Preserved for backward compatibility) ───────────────

class ReconciliationTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


AMOUNT_HIGH_THRESHOLD = 500.0
AMOUNT_MEDIUM_THRESHOLD = 100.0


def assign_tier(
    result: MatchResult,
    invoice: dict[str, Any],
) -> ReconciliationTier:
    """Assign a priority tier to an unmatched or anomalous reconciliation result."""
    amount = float(invoice.get("amount", 0.0))
    n_anomalies = len(result.anomalies)

    if not result.matched:
        if amount >= AMOUNT_HIGH_THRESHOLD or n_anomalies >= 2:
            return ReconciliationTier.HIGH
        elif amount >= AMOUNT_MEDIUM_THRESHOLD or n_anomalies == 1:
            return ReconciliationTier.MEDIUM
        else:
            return ReconciliationTier.LOW

    if n_anomalies >= 2:
        return ReconciliationTier.HIGH
    if n_anomalies == 1:
        return ReconciliationTier.MEDIUM
    return ReconciliationTier.LOW


def tier_all(
    results: list[MatchResult],
    invoice_map: dict[str, dict[str, Any]],
) -> dict[str, ReconciliationTier]:
    return {
        r.invoice_id: assign_tier(r, invoice_map.get(r.invoice_id, {}))
        for r in results
    }
