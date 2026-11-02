"""
PayPal Gateway Protocol (interface).

All PayPal interactions go through this interface.
- RestPayPalGateway: real httpx calls to sandbox/production.
- FakePayPal: deterministic test double that emits webhooks into ingestion.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PayPalGateway(Protocol):
    """Structural protocol for all PayPal gateway implementations."""

    async def create_order(
        self,
        amount: float,
        currency: str,
        request_id: str,
        description: str = "",
    ) -> dict[str, Any]: ...

    async def capture_order(
        self,
        order_id: str,
        request_id: str,
    ) -> dict[str, Any]: ...

    async def create_payout(
        self,
        recipient_email: str,
        amount: float,
        currency: str,
        sender_batch_id: str,
        note: str = "",
    ) -> dict[str, Any]: ...

    async def get_payout_item(
        self,
        payout_item_id: str,
    ) -> dict[str, Any]: ...

    async def refund_capture(
        self,
        capture_id: str,
        amount: float,
        currency: str,
        request_id: str,
        note: str = "",
    ) -> dict[str, Any]: ...

    async def get_capture(
        self,
        capture_id: str,
    ) -> dict[str, Any]: ...

    async def create_invoice(
        self,
        recipient_email: str,
        amount: float,
        currency: str,
        due_date: str,
        note: str = "",
    ) -> dict[str, Any]: ...

    async def send_invoice(
        self,
        invoice_id: str,
    ) -> dict[str, Any]: ...

    async def send_invoice_reminder(
        self,
        invoice_id: str,
    ) -> dict[str, Any]: ...
