"""
Generate 60 overdue invoices; some above AUTO_LIMIT_USD (200 USD).
"""
from __future__ import annotations
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from .constants import AUTO_LIMIT_USD
from ._rng_helpers import rng_amount, rng_ts, rng_choice

CURRENCIES = ["USD", "EUR", "GBP"]


@dataclass
class OverdueInvoice:
    invoice_id: str
    customer_id: str
    amount_usd: float
    currency: str
    issued_at: datetime
    due_at: datetime
    above_auto_limit: bool


def generate_invoices(
    rng: random.Random,
    customer_ids: list[str],
    base_time: datetime,
    n: int = 60,
) -> list[OverdueInvoice]:
    invoices: list[OverdueInvoice] = []
    for i in range(n):
        cid = rng_choice(rng, customer_ids)
        # Guarantee some invoices (at least 15) above $200
        if i < 18:
            amount = rng_amount(rng, 205.0, 950.0)
        else:
            amount = rng_amount(rng, 15.0, 650.0)
        above = amount > AUTO_LIMIT_USD
        currency = rng_choice(rng, CURRENCIES)
        issued = rng_ts(rng, base_time - timedelta(days=60), spread_days=30)
        due = issued + timedelta(days=rng.randint(14, 45))
        invoices.append(OverdueInvoice(
            invoice_id=f"INV-{i:05d}",
            customer_id=cid,
            amount_usd=round(amount, 2),
            currency=currency,
            issued_at=issued,
            due_at=due,
            above_auto_limit=above,
        ))
    return invoices

