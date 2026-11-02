"""Generate 10 escrow projects with evidence fixture names."""
from __future__ import annotations
import random
from dataclasses import dataclass
from datetime import datetime
from .constants import ESCROW_EVIDENCE_FIXTURES
from ._rng_helpers import rng_amount, rng_ts, rng_choice, rng_bool


@dataclass
class EscrowProject:
    project_id: str
    buyer_id: str
    seller_id: str
    amount_usd: float
    currency: str
    milestone: str
    evidence_fixtures: list[str]
    disputed: bool
    created_at: datetime


def generate_escrow(
    rng: random.Random,
    customer_ids: list[str],
    base_time: datetime,
    n: int = 10,
) -> list[EscrowProject]:
    projects: list[EscrowProject] = []
    milestones = ["design", "development", "testing", "delivery", "maintenance"]
    for i in range(n):
        buyer = rng_choice(rng, customer_ids)
        seller = rng_choice(rng, customer_ids)
        while seller == buyer and len(customer_ids) > 1:
            seller = rng_choice(rng, customer_ids)
        k = rng.randint(2, min(4, len(ESCROW_EVIDENCE_FIXTURES)))
        evidence = rng.sample(ESCROW_EVIDENCE_FIXTURES, k)
        projects.append(EscrowProject(
            project_id=f"ESCROW-{i:03d}",
            buyer_id=buyer,
            seller_id=seller,
            amount_usd=round(rng_amount(rng, 100.0, 5000.0), 2),
            currency="USD",
            milestone=rng_choice(rng, milestones),
            evidence_fixtures=evidence,
            disputed=rng_bool(rng, 0.3),
            created_at=rng_ts(rng, base_time, 60),
        ))
    return projects

