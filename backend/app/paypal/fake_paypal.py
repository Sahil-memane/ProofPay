"""
FakePayPal — a deterministic test double for PayPalGateway.

Key properties:
- Programmable failure injection per action type.
- Stores created orders/payouts in memory for retrieval.
- `emit_webhook()` inserts directly into the webhook_events table (or the
  in-memory worker queue if DB is unavailable), so the full ingestion path runs
  — identical to a real delivery.
- Implements PayPalGateway Protocol exactly.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from backend.app.core.errors import PayPalError
from backend.app.core.logging import get_logger

log = get_logger(__name__)


class FakePayPal:
    """
    Test double for PayPalGateway.
    All switch attributes are instance-level so tests can set them per instance.
    """

    def __init__(self) -> None:
        self.fail_capture: bool = False
        self.fail_payout: bool = False
        self.fail_refund: bool = False
        self.deny_payout: bool = False  # payout item DENIED (not an API error)
        self.fail_invoice: bool = False

        self._orders: dict[str, dict[str, Any]] = {}
        self._captures: dict[str, dict[str, Any]] = {}
        self._payouts: dict[str, dict[str, Any]] = {}
        self._invoices: dict[str, dict[str, Any]] = {}

    # ── Orders ────────────────────────────────────────────────────────────────

    async def create_order(
        self,
        amount: float,
        currency: str,
        request_id: str,
        description: str = "",
    ) -> dict[str, Any]:
        order_id = f"FAKE-ORDER-{uuid.uuid4().hex[:8].upper()}"
        order = {
            "id": order_id,
            "status": "CREATED",
            "purchase_units": [{"amount": {"currency_code": currency, "value": f"{amount:.2f}"}}],
            "links": [
                {
                    "href": f"https://sandbox.paypal.com/checkoutnow?token={order_id}",
                    "rel": "approve",
                    "method": "GET",
                }
            ],
        }
        self._orders[order_id] = order
        log.info("FakePayPal.create_order: %s amount=%s %s", order_id, amount, currency)
        return order

    async def capture_order(
        self,
        order_id: str,
        request_id: str,
    ) -> dict[str, Any]:
        if self.fail_capture:
            raise PayPalError("FakePayPal: capture_order injected failure", {})

        order = self._orders.get(order_id, {})
        amount = float(
            order.get("purchase_units", [{}])[0]
            .get("amount", {})
            .get("value", "0")
        )
        currency = (
            order.get("purchase_units", [{}])[0]
            .get("amount", {})
            .get("currency_code", "USD")
        )
        capture_id = f"FAKE-CAPTURE-{uuid.uuid4().hex[:8].upper()}"
        capture = {
            "id": capture_id,
            "status": "COMPLETED",
            "amount": {"currency_code": currency, "value": f"{amount:.2f}"},
            "order_id": order_id,
        }
        self._captures[capture_id] = capture
        self._orders[order_id] = {**order, "status": "COMPLETED"}

        # Emit webhook into ingestion path
        self.emit_webhook(
            "PAYMENT.CAPTURE.COMPLETED",
            {
                "id": f"WH-FAKE-{uuid.uuid4().hex[:8]}",
                "resource_type": "capture",
                "resource": capture,
                "create_time": datetime.now(timezone.utc).isoformat(),
            },
        )
        log.info("FakePayPal.capture_order: %s -> capture %s", order_id, capture_id)
        return capture

    async def get_capture(self, capture_id: str) -> dict[str, Any]:
        return self._captures.get(capture_id, {"id": capture_id, "status": "COMPLETED"})

    async def refund_capture(
        self,
        capture_id: str,
        amount: float,
        currency: str,
        request_id: str,
        note: str = "",
    ) -> dict[str, Any]:
        if self.fail_refund:
            raise PayPalError("FakePayPal: refund_capture injected failure", {})

        refund_id = f"FAKE-REFUND-{uuid.uuid4().hex[:8].upper()}"
        self.emit_webhook(
            "PAYMENT.CAPTURE.REFUNDED",
            {
                "id": f"WH-FAKE-{uuid.uuid4().hex[:8]}",
                "resource": {"id": refund_id, "amount": {"value": f"{amount:.2f}", "currency_code": currency}},
                "create_time": datetime.now(timezone.utc).isoformat(),
            },
        )
        return {"id": refund_id, "status": "COMPLETED"}

    # ── Payouts ───────────────────────────────────────────────────────────────

    async def create_payout(
        self,
        recipient_email: str,
        amount: float,
        currency: str,
        sender_batch_id: str,
        note: str = "",
    ) -> dict[str, Any]:
        if self.fail_payout:
            raise PayPalError("FakePayPal: create_payout injected failure", {})

        payout_batch_id = f"FAKE-BATCH-{uuid.uuid4().hex[:8].upper()}"
        payout_item_id = f"FAKE-ITEM-{uuid.uuid4().hex[:8].upper()}"

        payout = {
            "batch_header": {
                "payout_batch_id": payout_batch_id,
                "batch_status": "PENDING",
                "sender_batch_header": {"sender_batch_id": sender_batch_id},
            },
            "items": [{"payout_item_id": payout_item_id}],
        }
        self._payouts[payout_batch_id] = payout

        # Emit success webhook (or denied if switch is set)
        event_type = (
            "PAYMENT.PAYOUTS-ITEM.DENIED" if self.deny_payout else "PAYMENT.PAYOUTS-ITEM.SUCCEEDED"
        )
        self.emit_webhook(
            event_type,
            {
                "id": f"WH-FAKE-{uuid.uuid4().hex[:8]}",
                "resource": {
                    "payout_item_id": payout_item_id,
                    "payout_batch_id": payout_batch_id,
                    "sender_batch_id": sender_batch_id,
                    "transaction_status": "SUCCESS" if not self.deny_payout else "DENIED",
                    "payout_item": {
                        "receiver": recipient_email,
                        "amount": {"value": f"{amount:.2f}", "currency": currency},
                    },
                },
            },
        )
        return payout

    async def get_payout_item(self, payout_item_id: str) -> dict[str, Any]:
        return {"payout_item_id": payout_item_id, "transaction_status": "SUCCESS"}

    # ── Invoicing ─────────────────────────────────────────────────────────────

    async def create_invoice(
        self,
        recipient_email: str,
        amount: float,
        currency: str,
        due_date: str,
        note: str = "",
    ) -> dict[str, Any]:
        if self.fail_invoice:
            raise PayPalError("FakePayPal: create_invoice injected failure", {})
        invoice_id = f"FAKE-INV-{uuid.uuid4().hex[:8].upper()}"
        inv = {"id": invoice_id, "status": "DRAFT", "recipient": recipient_email}
        self._invoices[invoice_id] = inv
        return inv

    async def send_invoice(self, invoice_id: str) -> dict[str, Any]:
        if invoice_id in self._invoices:
            self._invoices[invoice_id]["status"] = "SENT"
        return {"id": invoice_id, "status": "SENT"}

    async def send_invoice_reminder(self, invoice_id: str) -> dict[str, Any]:
        return {"id": invoice_id, "reminder_sent": True}

    # ── Webhook emission ──────────────────────────────────────────────────────

    def emit_webhook(self, event_type: str, payload: dict[str, Any]) -> None:
        """
        Push a simulated webhook into the ingestion pipeline.
        Inserts directly into webhook_events table with source='fake'.
        Falls back to a module-level in-memory queue if DB is unavailable.
        """
        event_id = payload.get("id") or f"FAKE-EVT-{uuid.uuid4().hex[:12]}"
        try:
            from backend.app.db.session import get_sync_session
            from backend.app.db.models.webhooks import WebhookEvent
            import uuid as _uuid

            with get_sync_session() as session:
                row = WebhookEvent(
                    id=str(_uuid.uuid4()),
                    event_id=event_id,
                    event_type=event_type,
                    source="fake",
                    payload=payload,
                    status="pending",
                )
                session.add(row)
                session.commit()
            log.info("FakePayPal.emit_webhook: %s %s -> DB", event_type, event_id)
        except Exception as exc:
            log.warning("FakePayPal.emit_webhook DB unavailable (%s), using memory queue", exc)
            _PENDING_FAKE_WEBHOOKS.append({"event_id": event_id, "event_type": event_type, "payload": payload})

        # In-process dispatch for fake-mode testing
        try:
            from backend.app.ingestion.normalizer import normalize
            from backend.app.ingestion.handlers import dispatch
            if "event_type" not in payload:
                payload["event_type"] = event_type
            normalised = normalize(payload, source="fake")
            normalised["event_id"] = event_id
            dispatch(normalised)
        except Exception as exc2:
            log.warning("FakePayPal.emit_webhook in-process dispatch error: %s", exc2)


# In-memory queue for tests without DB
_PENDING_FAKE_WEBHOOKS: list[dict[str, Any]] = []


def get_pending_fake_webhooks() -> list[dict[str, Any]]:
    return list(_PENDING_FAKE_WEBHOOKS)


def clear_pending_fake_webhooks() -> None:
    _PENDING_FAKE_WEBHOOKS.clear()
