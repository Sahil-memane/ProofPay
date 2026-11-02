"""
Hypothesis property test: Invariant that NO final case ever moves.

Configured with 1000+ examples to strictly verify the state machine invariant.
"""
from __future__ import annotations

from hypothesis import given, settings, strategies as st
import pytest

from backend.app.recovery.state_machine import (
    transition,
    InvalidStateTransitionError,
)
from backend.app.stubs.contracts_stub import CaseState, FINAL_STATES


# Strategies for random inputs
final_state_strategy = st.sampled_from(list(FINAL_STATES))
target_state_strategy = st.sampled_from(list(CaseState))
actor_strategy = st.text(min_size=1, max_size=30)
reason_strategy = st.text(min_size=1, max_size=50)


@given(
    initial_final_state=final_state_strategy,
    target_state=target_state_strategy,
    actor=actor_strategy,
    reason=reason_strategy,
    amount=st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=1200)
def test_no_final_case_ever_moves(
    initial_final_state: CaseState,
    target_state: CaseState,
    actor: str,
    reason: str,
    amount: float,
):
    """
    Property: For any case in a final state (RECOVERED, HALTED, UNRECOVERED, PAID_ELSEWHERE),
    transition() must always raise InvalidStateTransitionError, and the case state
    must remain unaltered.
    Verified across 1000+ generated test examples.
    """
    case = {
        "id": "CASE-FINAL-PROP",
        "case_id": "CASE-FINAL-PROP",
        "state": initial_final_state,
        "amount_usd": amount,
        "history": [],
    }

    # Must raise InvalidStateTransitionError on any transition attempt
    with pytest.raises(InvalidStateTransitionError):
        transition(case, to_state=target_state, actor=actor, reason=reason)

    # Invariant: Case state never changes
    assert case["state"] == initial_final_state
    # Invariant: No new history entry added on rejection
    assert len(case["history"]) == 0

