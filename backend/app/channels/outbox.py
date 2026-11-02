"""
Channel Outbox.

In-memory queue storing dispatched emails and payment link messages.
Provides inspection functions for testing and auditing.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

_OUTBOX_MESSAGES: list[dict[str, Any]] = []


def record_message(
    case_id: str,
    channel: str,
    recipient: str,
    subject: str,
    body: str,
    idempotency_key: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Store an outgoing message in the outbox."""
    msg = {
        "message_id": f"msg-{uuid.uuid4().hex[:8]}",
        "case_id": case_id,
        "channel": channel,
        "recipient": recipient,
        "subject": subject,
        "body": body,
        "idempotency_key": idempotency_key,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }
    _OUTBOX_MESSAGES.append(msg)
    return msg


def list_messages(case_id: str | None = None) -> list[dict[str, Any]]:
    """List outbox messages, optionally filtered by case_id."""
    if case_id is None:
        return list(_OUTBOX_MESSAGES)
    return [m for m in _OUTBOX_MESSAGES if m.get("case_id") == case_id]


def clear_outbox() -> None:
    """Clear all outbox messages (for testing)."""
    _OUTBOX_MESSAGES.clear()

