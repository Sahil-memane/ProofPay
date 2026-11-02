"""PayPal Invoicing v2 API operations."""
from __future__ import annotations

from typing import Any

from backend.app.paypal import client


async def create_invoice(
    recipient_email: str,
    amount: float,
    currency: str,
    due_date: str,  # ISO date string: "2026-11-10"
    note: str = "",
) -> dict[str, Any]:
    body = {
        "detail": {
            "currency_code": currency,
            "note": note or "Invoice from ProofPay",
            "payment_term": {"due_date": due_date},
        },
        "primary_recipients": [
            {"billing_info": {"email_address": recipient_email}}
        ],
        "items": [
            {
                "name": "ProofPay Invoice",
                "quantity": "1",
                "unit_amount": {"currency_code": currency, "value": f"{amount:.2f}"},
            }
        ],
    }
    return await client.post("/v2/invoicing/invoices", body)


async def send_invoice(invoice_id: str) -> dict[str, Any]:
    return await client.post(f"/v2/invoicing/invoices/{invoice_id}/send", {})


async def send_invoice_reminder(invoice_id: str) -> dict[str, Any]:
    body = {
        "subject": "Friendly payment reminder",
        "note": "This is a reminder that your invoice is due.",
    }
    return await client.post(f"/v2/invoicing/invoices/{invoice_id}/remind", body)


async def get_invoice(invoice_id: str) -> dict[str, Any]:
    return await client.get(f"/v2/invoicing/invoices/{invoice_id}")


async def record_payment(invoice_id: str, amount: float, currency: str) -> dict[str, Any]:
    body = {
        "method": "OTHER",
        "amount": {"currency_code": currency, "value": f"{amount:.2f}"},
    }
    return await client.post(f"/v2/invoicing/invoices/{invoice_id}/payments", body)
