"""PayPal Orders v2 API operations."""
from __future__ import annotations

from typing import Any

from backend.app.paypal import client


async def create_order(
    amount: float,
    currency: str,
    request_id: str,
    description: str = "ProofPay Escrow",
) -> dict[str, Any]:
    """Create a CAPTURE intent order."""
    body = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": currency,
                    "value": f"{amount:.2f}",
                },
                "description": description,
            }
        ],
    }
    return await client.post("/v2/checkout/orders", body, request_id=request_id)


async def capture_order(order_id: str, request_id: str) -> dict[str, Any]:
    """Capture a previously created order."""
    return await client.post(
        f"/v2/checkout/orders/{order_id}/capture", {}, request_id=request_id
    )


async def get_order(order_id: str) -> dict[str, Any]:
    return await client.get(f"/v2/checkout/orders/{order_id}")


async def get_capture(capture_id: str) -> dict[str, Any]:
    return await client.get(f"/v2/payments/captures/{capture_id}")


async def refund_capture(
    capture_id: str,
    amount: float,
    currency: str,
    request_id: str,
    note: str = "",
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "amount": {"currency_code": currency, "value": f"{amount:.2f}"},
    }
    if note:
        body["note_to_payer"] = note
    return await client.post(
        f"/v2/payments/captures/{capture_id}/refund", body, request_id=request_id
    )
