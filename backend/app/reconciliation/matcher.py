"""
Transaction matcher.

Performs three-pass reconciliation across normalized ReconRecords:
  Pass 1: Exact ID match (external_id or invoice reference)
  Pass 2: Customer match + amount within tolerance (rounding up to 0.05, fees, refunds) + date within 3 days
  Pass 3: Rapidfuzz fuzzy matching on reference and descriptor

Exposes check_already_paid(case) returning auto_match, human_review, or no_match.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from rapidfuzz import fuzz

from backend.app.reconciliation.normalizer import ReconRecord, load_all_recon_records, normalize_timestamp
from backend.app.reconciliation.tiers import DEFAULT_THRESHOLDS, ReconVerdict, classify_confidence
from backend.app.stubs.clock import clock


# ── Match Result Dataclass ────────────────────────────────────────────────────

@dataclass
class MatchResult:
    invoice_id: str
    payment_id: str
    score: float                   # 0.0 – 1.0
    signals: dict[str, float] = field(default_factory=dict)
    matched: bool = False
    anomalies: list[str] = field(default_factory=list)
    verdict: str = ReconVerdict.NO_MATCH.value
    matched_record: ReconRecord | None = None
    pass_name: str = "none"


# ── Tolerances & Math Helpers ─────────────────────────────────────────────────

ROUNDING_TOLERANCE = 0.05
MAX_TIMING_DAYS = 3.0


def _is_fee_deduction(invoice_amount: float, payment_amount: float) -> bool:
    """Check if payment amount matches standard gateway fee deduction (e.g. 2.9% + $0.30 or similar)."""
    if invoice_amount <= payment_amount:
        return False
    # Standard PayPal formula: net = round(gross - (gross * 0.029 + 0.30), 2)
    expected_paypal_net = round(invoice_amount - (invoice_amount * 0.029 + 0.30), 2)
    if abs(payment_amount - expected_paypal_net) <= ROUNDING_TOLERANCE:
        return True
    # General fee range: 1.5% to 5.0% + fixed fee
    diff = invoice_amount - payment_amount
    min_fee = invoice_amount * 0.015
    max_fee = invoice_amount * 0.05 + 0.50
    return min_fee <= diff <= max_fee


def _is_amount_within_tolerance(inv_amt: float, pay_amt: float) -> tuple[bool, str]:
    """Check amount equality within 0.05 rounding, fee deductions, or partial refund."""
    diff = abs(inv_amt - pay_amt)
    if diff <= ROUNDING_TOLERANCE:
        return True, "exact_or_rounding"
    if _is_fee_deduction(inv_amt, pay_amt):
        return True, "fee_deduction"
    # Partial refund (payment is 30% to 90% of invoice amount)
    if 0.30 * inv_amt <= pay_amt < inv_amt:
        return True, "partial_refund"
    return False, "mismatch"


def _days_between(d1: datetime, d2: datetime) -> float:
    """Return absolute days between two datetimes."""
    t1 = d1 if d1.tzinfo else d1.replace(tzinfo=timezone.utc)
    t2 = d2 if d2.tzinfo else d2.replace(tzinfo=timezone.utc)
    return abs((t1 - t2).total_seconds()) / 86400.0


# ── Three-Pass Matcher ────────────────────────────────────────────────────────

def match_case_against_record(case: dict[str, Any], record: ReconRecord) -> MatchResult:
    """Evaluate a single case against a single ReconRecord through the 3 passes."""
    payload = case.get("payload") if isinstance(case.get("payload"), dict) else {}
    inv_id = str(case.get("invoice_id") or payload.get("invoice_id") or case.get("case_id") or case.get("id", ""))
    cust_id = str(case.get("customer_id") or payload.get("customer_id") or case.get("customer_ref", ""))
    inv_amt = float(case.get("amount_usd") or payload.get("amount_usd") or case.get("amount", 0.0))
    inv_cur = str(case.get("currency") or payload.get("currency", "USD")).upper()
    inv_ref = str(case.get("reference") or payload.get("reference", "")).upper()
    raw_date = (
        case.get("due_at")
        or payload.get("due_at")
        or case.get("date")
        or payload.get("date")
        or case.get("due_date")
        or payload.get("due_date")
        or case.get("created_at")
        or clock.utcnow()
    )
    case_date = normalize_timestamp(raw_date)

    rec_amt = record.amount
    rec_cur = record.currency.upper()
    rec_id = record.external_id
    rec_ref = record.reference.upper()
    rec_cust = record.customer_ref

    anomalies: list[str] = []
    if inv_cur != rec_cur:
        anomalies.append("currency_mismatch")

    # Pass 1: Exact ID match (external_id == invoice_id or reference contains invoice_id)
    if inv_id and (rec_id == inv_id or inv_id in rec_ref or (inv_ref and inv_ref == rec_ref)):
        score = 0.98 if not anomalies else 0.50
        return MatchResult(
            invoice_id=inv_id,
            payment_id=rec_id,
            score=score,
            signals={"id_match": 1.0, "currency": float(not anomalies)},
            matched=not anomalies,
            anomalies=anomalies,
            verdict=classify_confidence(score),
            matched_record=record,
            pass_name="pass1_exact_id",
        )

    # Pass 2: Same customer + amount within tolerance + date within 3 days (or 30 days for bank transfers)
    if cust_id and cust_id == rec_cust:
        days_diff = _days_between(case_date, record.date)
        amt_ok, amt_kind = _is_amount_within_tolerance(inv_amt, rec_amt)
        max_days = 30.0 if record.source == "bank" else MAX_TIMING_DAYS

        if days_diff <= max_days and amt_ok and not anomalies:
            if amt_kind == "exact_or_rounding":
                score = 0.95
            elif amt_kind == "fee_deduction":
                score = 0.92
                anomalies.append("fee_deduction")
            elif amt_kind == "partial_refund":
                score = 0.75
                anomalies.append("partial_refund")
            else:
                score = 0.85

            if days_diff > 1.0:
                anomalies.append("timing_offset")

            return MatchResult(
                invoice_id=inv_id,
                payment_id=rec_id,
                score=score,
                signals={"customer": 1.0, "amount": 1.0, "date_diff_days": days_diff},
                matched=True,
                anomalies=anomalies,
                verdict=classify_confidence(score),
                matched_record=record,
                pass_name="pass2_customer_tolerance",
            )

    # Pass 3: Rapidfuzz fuzzy match on name and reference
    ref_target = inv_ref or inv_id
    ratio_ref = fuzz.token_sort_ratio(ref_target, rec_ref) / 100.0 if rec_ref else 0.0
    ratio_full = fuzz.token_sort_ratio(ref_target, f"{rec_ref} {rec_id} {rec_cust}".strip()) / 100.0
    fuzzy_ratio = max(ratio_ref, ratio_full)

    amt_diff_pct = abs(inv_amt - rec_amt) / inv_amt if inv_amt > 0 else 1.0
    if fuzzy_ratio >= 0.70 and amt_diff_pct <= 0.15 and not anomalies:
        score = round(0.60 + (fuzzy_ratio * 0.25), 2)
        anomalies.append("fuzzy_match")
        return MatchResult(
            invoice_id=inv_id,
            payment_id=rec_id,
            score=score,
            signals={"fuzzy_ref": fuzzy_ratio, "amt_diff_pct": amt_diff_pct},
            matched=True,
            anomalies=anomalies,
            verdict=classify_confidence(score),
            matched_record=record,
            pass_name="pass3_fuzzy",
        )

    return MatchResult(
        invoice_id=inv_id,
        payment_id=rec_id,
        score=0.0,
        signals={"fuzzy_ref": fuzzy_ratio},
        matched=False,
        anomalies=["no_match"],
        verdict=ReconVerdict.NO_MATCH.value,
        matched_record=None,
        pass_name="none",
    )


def check_already_paid(
    case: dict[str, Any] | Any,
    records: list[ReconRecord] | None = None,
) -> str:
    """
    Core operational query: "has this person already paid, in any source?"
    Returns:
      - "auto_match"
      - "human_review"
      - "no_match"
    """
    case_dict = case if isinstance(case, dict) else (
        case.__dict__ if hasattr(case, "__dict__") else dict(case)
    )

    candidate_records = records if records is not None else load_all_recon_records()

    best_result: MatchResult | None = None
    for rec in candidate_records:
        res = match_case_against_record(case_dict, rec)
        if best_result is None or res.score > best_result.score:
            best_result = res
            if res.verdict == ReconVerdict.AUTO_MATCH.value:
                # Fast return if auto_match achieved
                return ReconVerdict.AUTO_MATCH.value

    if best_result and best_result.score >= DEFAULT_THRESHOLDS["auto_match"]:
        return ReconVerdict.AUTO_MATCH.value
    elif best_result and best_result.score >= DEFAULT_THRESHOLDS["human_review"]:
        return ReconVerdict.HUMAN_REVIEW.value
    else:
        return ReconVerdict.NO_MATCH.value


# ── Legacy Helpers (Preserved for backward compatibility) ─────────────────────

AMOUNT_TOLERANCE_PCT = 0.02
MIN_MATCH_SCORE = 0.60


def _ref_score(inv_ref: str, pay_ref: str) -> float:
    if not inv_ref and not pay_ref:
        return 1.0
    if not pay_ref:
        return 0.0
    return fuzz.token_sort_ratio(inv_ref, pay_ref) / 100.0


def _amount_score(inv_amt: float, pay_amt: float) -> float:
    if inv_amt == 0:
        return 0.0
    diff_pct = abs(inv_amt - pay_amt) / inv_amt
    if diff_pct <= AMOUNT_TOLERANCE_PCT:
        return 1.0
    elif diff_pct <= 0.10:
        return 1.0 - (diff_pct - AMOUNT_TOLERANCE_PCT) / 0.08
    return 0.0


def _currency_score(inv_cur: str, pay_cur: str) -> float:
    return 1.0 if inv_cur == pay_cur else 0.0


def score_pair(invoice: dict[str, Any], payment: dict[str, Any]) -> MatchResult:
    cust_match = invoice.get("customer_id") == payment.get("customer_id")
    ref_s = _ref_score(invoice.get("reference", ""), payment.get("reference", ""))
    amt_s = _amount_score(invoice["amount"], payment["amount"])
    cur_s = _currency_score(invoice["currency"], payment["currency"])

    score = ref_s * 0.35 + amt_s * 0.35 + cur_s * 0.20 + (0.10 if cust_match else 0.0)

    anomalies: list[str] = []
    if ref_s < 0.5:
        anomalies.append("reference_mismatch")
    if amt_s < 0.8:
        anomalies.append("amount_mismatch")
    if cur_s == 0.0:
        anomalies.append("currency_mismatch")

    return MatchResult(
        invoice_id=invoice["txn_id"],
        payment_id=payment["txn_id"],
        score=round(score, 4),
        signals={"ref": ref_s, "amount": amt_s, "currency": cur_s, "customer": float(cust_match)},
        matched=score >= MIN_MATCH_SCORE and not anomalies,
        anomalies=anomalies,
        verdict=classify_confidence(score),
    )


def match_many(invoices: list[dict[str, Any]], payments: list[dict[str, Any]]) -> list[MatchResult]:
    results: list[MatchResult] = []
    used_payments: set[str] = set()
    all_scores: list[MatchResult] = []

    for inv in invoices:
        for pay in payments:
            all_scores.append(score_pair(inv, pay))

    all_scores.sort(key=lambda r: r.score, reverse=True)
    used_invoices: set[str] = set()

    for r in all_scores:
        if r.invoice_id in used_invoices or r.payment_id in used_payments:
            continue
        if r.score >= MIN_MATCH_SCORE:
            results.append(r)
            used_invoices.add(r.invoice_id)
            used_payments.add(r.payment_id)

    matched_inv_ids = {r.invoice_id for r in results}
    for inv in invoices:
        if inv["txn_id"] not in matched_inv_ids:
            results.append(MatchResult(
                invoice_id=inv["txn_id"],
                payment_id="",
                score=0.0,
                matched=False,
                anomalies=["no_match"],
                verdict=ReconVerdict.NO_MATCH.value,
            ))

    return results
