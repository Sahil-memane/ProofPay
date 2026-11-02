"""
ProofPay Normalized Event Contract.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class NormalizedEvent(BaseModel):
    event_id: str
    event_type: str
    source: str = "paypal"  # "paypal" | "sim" | "internal"
    payload: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
