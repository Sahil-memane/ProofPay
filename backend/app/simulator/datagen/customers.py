"""
Generate 120 synthetic customers with language, IANA timezone,
opt_out flag, and a short payment history list.
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from .constants import LANGUAGES, IANA_TIMEZONES, BEHAVIOUR_LABELS
from ._rng_helpers import rng_choice, rng_bool


@dataclass
class Customer:
    customer_id: str
    email: str
    language: str
    timezone: str
    opted_out: bool
    behaviour: str          # true label (answer-key only)
    history: list[str]      # past outcome codes: "paid", "defaulted", "disputed", ...
    has_email: bool = True


def _make_history(rng: random.Random, behaviour: str) -> list[str]:
    n = rng.randint(0, 5)
    pool = {
        "pays_after_one_reminder": ["paid", "paid", "paid", "late_paid"],
        "needs_payment_link": ["paid_via_link", "paid_via_link", "paid"],
        "needs_card_update": ["card_failed", "card_updated_paid", "paid"],
        "prefers_split": ["split_paid", "split_paid", "paid"],
        "ignores_everything": ["no_response", "no_response", "defaulted"],
        "disputes_if_chased_early": ["disputed", "disputed", "paid_after_mediation"],
        "already_paid_elsewhere": ["paid_elsewhere", "paid", "paid"],
    }.get(behaviour, ["paid"])
    return [rng_choice(rng, pool) for _ in range(n)]


def generate_customers(rng: random.Random, n: int = 120) -> list[Customer]:
    customers: list[Customer] = []
    # Ensure all behavior labels appear at least once across the population if n >= len(BEHAVIOUR_LABELS)
    labels_pool = list(BEHAVIOUR_LABELS)
    for i in range(n):
        cid = f"CUST-{i:05d}"
        lang = rng_choice(rng, LANGUAGES)
        tz = rng_choice(rng, IANA_TIMEZONES)
        opted_out = rng_bool(rng, 0.05)
        if i < len(labels_pool):
            behaviour = labels_pool[i]
        else:
            behaviour = rng_choice(rng, BEHAVIOUR_LABELS)
        history = _make_history(rng, behaviour)
        customers.append(Customer(
            customer_id=cid,
            email=f"user{i}@proofpay-test.invalid",
            language=lang,
            timezone=tz,
            opted_out=opted_out,
            behaviour=behaviour,
            history=history,
        ))
    return customers

