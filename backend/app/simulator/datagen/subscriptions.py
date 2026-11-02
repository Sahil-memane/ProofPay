"""
Generate 90 failed-subscription cases across 4 failure codes.
"""
from __future__ import annotations
import random
from dataclasses import dataclass
from datetime import datetime
from .constants import FAILURE_CODES
from ._rng_helpers import rng_uuid, rng_amount, rng_ts, rng_choice


@dataclass
class FailedSubscription:
    sub_id: str
    customer_id: str
    failure_code: str
    amount_usd: float
    currency: str = "USD"
    failed_at: datetime | None = None
    retry_count: int = 0


def generate_subscriptions(
    rng: random.Random,
    customer_ids: list[str],
    base_time: datetime,
    n: int = 90,
) -> list[FailedSubscription]:
    subs: list[FailedSubscription] = []
    codes_pool = list(FAILURE_CODES)
    for i in range(n):
        cid = rng_choice(rng, customer_ids)
        if i < len(codes_pool):
            code = codes_pool[i]
        else:
            code = rng_choice(rng, FAILURE_CODES)
        amount = rng_amount(rng, 9.99, 299.99)
        ts = rng_ts(rng, base_time, spread_days=60)
        retry = rng.randint(0, 3)
        subs.append(FailedSubscription(
            sub_id=rng_uuid(rng),
            customer_id=cid,
            failure_code=code,
            amount_usd=round(amount, 2),
            currency="USD",
            failed_at=ts,
            retry_count=retry,
        ))
    return subs

