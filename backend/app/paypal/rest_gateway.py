"""
RestPayPalGateway — real implementation of PayPalGateway using the httpx client.
Selected when PAYPAL_EXEC_MODE=rest (default for sandbox/production).
"""
from __future__ import annotations

from typing import Any

from backend.app.paypal import invoicing, orders, payouts


class RestPayPalGateway:
    """Thin facade that maps the PayPalGateway protocol to the REST client calls."""

    async def create_order(
        self, amount: float, currency: str, request_id: str, description: str = ""
    ) -> dict[str, Any]:
        return await orders.create_order(amount, currency, request_id, description)

    async def capture_order(self, order_id: str, request_id: str) -> dict[str, Any]:
        return await orders.capture_order(order_id, request_id)

    async def get_capture(self, capture_id: str) -> dict[str, Any]:
        return await orders.get_capture(capture_id)

    async def refund_capture(
        self,
        capture_id: str,
        amount: float,
        currency: str,
        request_id: str,
        note: str = "",
    ) -> dict[str, Any]:
        return await orders.refund_capture(capture_id, amount, currency, request_id, note)

    async def create_payout(
        self,
        recipient_email: str,
        amount: float,
        currency: str,
        sender_batch_id: str,
        note: str = "",
    ) -> dict[str, Any]:
        from backend.app.paypal.payouts import PayoutItem
        items = [PayoutItem(
            recipient_email=recipient_email,
            amount=amount,
            currency=currency,
            sender_item_id=sender_batch_id,
            note=note,
        )]
        return await payouts.create_payout_batch(items)

    async def get_payout_item(self, payout_item_id: str) -> dict[str, Any]:
        return await payouts.get_payout_item(payout_item_id)

    async def create_invoice(
        self,
        recipient_email: str,
        amount: float,
        currency: str,
        due_date: str,
        note: str = "",
    ) -> dict[str, Any]:
        return await invoicing.create_invoice(recipient_email, amount, currency, due_date, note)

    async def send_invoice(self, invoice_id: str) -> dict[str, Any]:
        return await invoicing.send_invoice(invoice_id)

    async def send_invoice_reminder(self, invoice_id: str) -> dict[str, Any]:
        return await invoicing.send_invoice_reminder(invoice_id)
