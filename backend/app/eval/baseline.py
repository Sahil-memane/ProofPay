"""
Naive Baseline Recovery Agent for ProofPay Benchmarking.

Represents a standard legacy dunning workflow:
  - No reconciliation: never checks if payment was already made elsewhere.
  - No diagnosis: treats all cases identically.
  - Fixed 3-step ladder (Generic Reminder -> Payment Link -> Final Reminder).
  - Contacts customers regardless of disputes or quiet hours.
Used as the benchmark against which the ProofPay Recovery Agent is evaluated.
"""
from __future__ import annotations

import random
from typing import Any

from backend.app.simulator.profiles import respond
from backend.app.stubs import clock
from backend.app.stubs.contracts_stub import CaseState


class BaselineAgent:
    """Conventional, naive recovery baseline without reconciliation or diagnosis."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)

    def process_case(
        self,
        case: dict[str, Any],
        profile: Any | None = None,
        now: Any | None = None,
    ) -> dict[str, Any]:
        """
        Run the naive baseline lifecycle on a single case:
        Attempts up to 3 contacts at fixed steps:
          Step 0: generic reminder
          Step 1: payment link
          Step 2: generic reminder
        Returns the final evaluated case state dict.
        """
        sim_now = now or clock.utcnow()
        case_id = case.get("id") or case.get("case_id", "CASE-BASE-001")
        amount_usd = float(case.get("amount_usd", 100.0))
        contacts: list[dict[str, Any]] = []
        is_recovered = False
        is_halted = False
        days_to_recover: float | None = None

        # Naive 3-step sequence: same email to everyone 3 times
        actions = ["send_reminder", "send_reminder", "send_reminder"]
        successful_intervention = None

        for step_idx, action in enumerate(actions):
            # Record outbound contact
            contacts.append({
                "step": step_idx,
                "action": action,
                "timestamp": sim_now.isoformat(),
            })

            # Check customer response using simulator (ignoring quiet hours)
            resp = respond(case=case, action=action, now=sim_now, rng=self.rng)
            event_type = resp.event_type.value

            if event_type in ("payment_success", "payment_received"):
                is_recovered = True
                successful_intervention = action
                days_to_recover = float(step_idx * 3)  # Naive 3-day intervals
                break
            elif event_type == "dispute":
                # Naive baseline doesn't check disputes early; customer may dispute
                is_halted = True
                break
            elif event_type == "opt_out":
                is_halted = True
                break

        final_state = (
            CaseState.RECOVERED.value
            if is_recovered
            else (CaseState.HALTED.value if is_halted else CaseState.UNRECOVERED.value)
        )

        unrecovered_reason = None
        if not is_recovered:
            unrecovered_reason = "customer_dispute" if is_halted else "max_attempts_reached"

        return {
            "case_id": case_id,
            "state": final_state,
            "recovered": is_recovered,
            "halted": is_halted,
            "contact_count": len(contacts),
            "contacts": contacts,
            "amount_usd": amount_usd,
            "amount_recovered": amount_usd if is_recovered else 0.0,
            "days_to_recover": days_to_recover,
            "intervention_type": successful_intervention,
            "dispute_occurred": is_halted and event_type == "dispute",
            "unrecovered_reason": unrecovered_reason,
            "llm_calls_used": 0,
            "agent_type": "baseline",
        }

