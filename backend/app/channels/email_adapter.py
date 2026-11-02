"""
Email adapter for ProofPay outbound communication.

Adapts outbox messages into email protocol payloads (RFC 2822 format structure)
and simulates email dispatch. Recovery code never imports this file directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.app.channels.outbox import record_message
from backend.app.stubs import clock


@dataclass
class EmailEnvelope:
    to_email: str
    from_email: str
    subject: str
    body_text: str
    body_html: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    sent_at: str = field(default_factory=lambda: clock.utcnow().isoformat())


class EmailAdapter:
    """Outbound email transport adapter."""

    def __init__(self, sender_address: str = "recovery@proofpay.invalid") -> None:
        self.sender_address = sender_address
        self._sent_envelopes: list[EmailEnvelope] = []

    def dispatch(
        self,
        case_id: str,
        recipient: str,
        subject: str,
        body: str,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EmailEnvelope:
        envelope = EmailEnvelope(
            to_email=recipient,
            from_email=self.sender_address,
            subject=subject,
            body_text=body,
            headers={"X-Case-ID": case_id, "X-ProofPay-Outbox": "true"},
            sent_at=clock.utcnow().isoformat(),
        )
        self._sent_envelopes.append(envelope)
        record_message(
            case_id=case_id,
            channel="email",
            recipient=recipient,
            subject=subject,
            body=body,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )
        return envelope

    def get_sent(self) -> list[EmailEnvelope]:
        return list(self._sent_envelopes)

    def clear(self) -> None:
        self._sent_envelopes.clear()


# Default singleton instance
email_adapter = EmailAdapter()

