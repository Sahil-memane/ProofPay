"""
Escrow plan hash computation.

The plan_hash is a SHA-256 of the canonical JSON of milestone definitions.
It is stored on the project when both parties approve, and re-checked before
any PayPal order is created — tamper-proof plan locking.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_plan_hash(milestones: list[dict[str, Any]]) -> str:
    """
    Returns a stable SHA-256 hash of the milestone plan.
    Uses canonical JSON (sorted keys, no whitespace) for determinism.
    """
    # Normalise: sort criteria within each milestone, sort milestones by sequence
    normalised = []
    for m in sorted(milestones, key=lambda x: x.get("sequence", 0)):
        normalised.append({
            "title": m.get("title", ""),
            "amount": round(float(m.get("amount", 0)), 2),
            "currency": m.get("currency", "USD"),
            "criteria": sorted(
                m.get("criteria", []),
                key=lambda c: c.get("id", ""),
            ),
            "sequence": m.get("sequence", 0),
        })

    canonical = json.dumps(normalised, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
