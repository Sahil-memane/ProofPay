"""Shared constants for datagen. No imports from app/."""
from __future__ import annotations

LANGUAGES = ["en", "hi"]

IANA_TIMEZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Los_Angeles",
    "America/Sao_Paulo",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Asia/Kolkata",
    "Asia/Tokyo",
    "Asia/Singapore",
    "Australia/Sydney",
]

FAILURE_CODES = [
    "insufficient_funds",
    "expired_card",
    "temporary_hold",
    "hard_decline",
]

# True customer behaviours (answer-key labels)
BEHAVIOUR_LABELS = [
    "pays_after_one_reminder",
    "needs_payment_link",
    "needs_card_update",
    "prefers_split",
    "ignores_everything",
    "disputes_if_chased_early",
    "already_paid_elsewhere",
]

TRAP_TYPES = [
    "already_paid_by_bank_transfer",
    "duplicate_payment",
    "partial_refund",
    "fee_deduction",
    "rounding_gap_003",
    "timing_offset_1_3_days",
    "disputes_if_chased_early",
    "hard_decline_looks_like_fraud",
    "promise_to_pay_kept",
    "promise_to_pay_broken",
    "borderline_evidence",
    "over_limit_release_attempt",
]

ESCROW_EVIDENCE_FIXTURES = [
    "contract_draft.pdf",
    "milestone_photo.jpg",
    "invoice_signed.pdf",
    "delivery_confirmation.png",
    "email_thread.eml",
    "bank_receipt.pdf",
    "chat_screenshot.png",
    "work_sample.zip",
    "dispute_letter.pdf",
    "inspection_report.pdf",
]

AUTO_LIMIT_USD = 200.0

