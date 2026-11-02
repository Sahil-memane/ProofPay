"""PayPal Payouts v1 API operations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.paypal import client


@dataclass
class PayoutItem:
    recipient_email: str
    amount: float
    currency: str
    sender_item_id: str  # idempotency key per item
    note: str = ""


async def create_payout_batch(items: list[PayoutItem]) -> dict[str, Any]:
    """
    Create a single-item payout batch.
    sender_batch_id is derived from the first item's sender_item_id to ensure
    PayPal-side idempotency on retries.
    """
    body = {
        "sender_batch_header": {
            "sender_batch_id": items[0].sender_item_id,
            "email_subject": "ProofPay milestone payment",
        },
        "items": [
            {
                "recipient_type": "EMAIL",
                "amount": {"value": f"{item.amount:.2f}", "currency": item.currency},
                "receiver": item.recipient_email,
                "note": item.note or "Milestone payment from ProofPay",
                "sender_item_id": item.sender_item_id,
            }
            for item in items
        ],
    }
    return await client.post("/v1/payments/payouts", body, request_id=items[0].sender_item_id)


async def get_payout_batch(payout_batch_id: str) -> dict[str, Any]:
    return await client.get(f"/v1/payments/payouts/{payout_batch_id}")


async def get_payout_item(payout_item_id: str) -> dict[str, Any]:
    return await client.get(f"/v1/payments/payouts-item/{payout_item_id}")
