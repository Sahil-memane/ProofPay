"""Pure RNG helpers — no I/O, no imports from app/."""
from __future__ import annotations
import random
import uuid
from datetime import datetime, timedelta, timezone


def rng_uuid(rng: random.Random) -> str:
    return str(uuid.UUID(int=rng.getrandbits(128)))


def rng_amount(rng: random.Random, lo: float = 10.0, hi: float = 800.0) -> float:
    return round(rng.uniform(lo, hi), 2)


def rng_ts(rng: random.Random, base: datetime, spread_days: int = 90) -> datetime:
    delta = timedelta(seconds=rng.randint(0, spread_days * 86400))
    return base + delta


def rng_choice(rng: random.Random, seq: list) -> object:
    return seq[rng.randrange(len(seq))]


def rng_bool(rng: random.Random, p: float = 0.5) -> bool:
    return rng.random() < p

