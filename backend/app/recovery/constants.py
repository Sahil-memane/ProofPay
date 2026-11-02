"""
Event and Case Type Constants for ProofPay Recovery Subsystem.
"""
from __future__ import annotations

# PayPal & Escrow Webhook / Pipeline Event Names
EVENT_FUNDING_FAILED = "funding.failed"
EVENT_INSTALMENT_FAILED = "instalment.failed"
EVENT_FUNDING_RESUMED = "funding.resumed"
EVENT_PROJECT_FLAGGED = "project.flagged_for_freelancer"
EVENT_INVOICE_PAID = "invoice.paid"
EVENT_INVOICE_CANCELLED = "invoice.cancelled"
EVENT_SUBSCRIPTION_FAILED = "subscription.payment_failed"

# Case Types
CASE_TYPE_ESCROW_FUNDING = "escrow_funding"
CASE_TYPE_OVERDUE_INVOICE = "overdue_invoice"
CASE_TYPE_SUBSCRIPTION = "subscription"

