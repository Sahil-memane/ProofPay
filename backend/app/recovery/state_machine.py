"""
Case State Machine and Lifecycle Management.

Enforces allowed transitions, writes audit rows, prevents invalid transitions
from final states, provides human reopen, and handles halting with schedule cancellation.
Also handles trigger-based deduplicated case creation.
"""
from __future__ import annotations

import uuid
from typing import Any

from backend.app.stubs import audit, scheduler
from backend.app.stubs.clock import utcnow
from backend.app.stubs.contracts_stub import CaseState, FINAL_STATES
from backend.app.stubs.repositories import case_repo


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal case state transition is attempted."""
    pass


# ── Allowed Transitions Table ─────────────────────────────────────────────────

ALLOWED_TRANSITIONS: dict[CaseState, set[CaseState]] = {
    CaseState.OPEN: {
        CaseState.RECONCILING,
        CaseState.DIAGNOSED,
        CaseState.ACTION_PENDING_APPROVAL,
        CaseState.HALTED,
        CaseState.PAID_ELSEWHERE,
        CaseState.UNRECOVERED,
    },
    CaseState.RECONCILING: {
        CaseState.DIAGNOSED,
        CaseState.HALTED,
        CaseState.PAID_ELSEWHERE,
        CaseState.UNRECOVERED,
        CaseState.RECOVERED,
    },
    CaseState.DIAGNOSED: {
        CaseState.ACTION_PENDING_APPROVAL,
        CaseState.ACTION_SENT,
        CaseState.HALTED,
        CaseState.PAID_ELSEWHERE,
        CaseState.UNRECOVERED,
    },
    CaseState.ACTION_PENDING_APPROVAL: {
        CaseState.ACTION_SENT,
        CaseState.HALTED,
        CaseState.PAID_ELSEWHERE,
        CaseState.UNRECOVERED,
    },
    CaseState.ACTION_SENT: {
        CaseState.AWAITING_RESULT,
        CaseState.RECOVERED,
        CaseState.HALTED,
        CaseState.PAID_ELSEWHERE,
        CaseState.UNRECOVERED,
    },
    CaseState.AWAITING_RESULT: {
        CaseState.RECOVERED,
        CaseState.ACTION_SENT,
        CaseState.ACTION_PENDING_APPROVAL,
        CaseState.DIAGNOSED,
        CaseState.HALTED,
        CaseState.UNRECOVERED,
        CaseState.PAID_ELSEWHERE,
    },
    # Final states: zero outgoing transitions allowed in normal flow
    CaseState.RECOVERED: set(),
    CaseState.HALTED: set(),
    CaseState.UNRECOVERED: set(),
    CaseState.PAID_ELSEWHERE: set(),
}


# ── Transition Function ───────────────────────────────────────────────────────

def transition(
    case: dict[str, Any],
    to_state: CaseState | str,
    actor: str,
    reason: str,
) -> dict[str, Any]:
    """
    Transition a case to a new state.
    Rejects any transition from a final state.
    Writes an audit row on every transition.
    """
    target = CaseState(to_state) if isinstance(to_state, str) else to_state
    current_raw = case.get("state")
    current = CaseState(current_raw) if isinstance(current_raw, str) else current_raw
    case_id = case.get("id") or case.get("case_id", "UNKNOWN")

    # 1. Reject any transition attempt from a final state
    if current in FINAL_STATES:
        raise InvalidStateTransitionError(
            f"Cannot transition case {case_id} from final state {current.value} to {target.value}"
        )

    # 2. Check if transition is allowed
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransitionError(
            f"Illegal transition for case {case_id}: {current.value} -> {target.value}"
        )

    # 3. Perform update
    case["state"] = target
    history_entry = {
        "from_state": current.value if current else None,
        "to_state": target.value,
        "actor": actor,
        "reason": reason,
        "timestamp": utcnow().isoformat(),
    }
    case.setdefault("history", []).append(history_entry)

    # If case exists in repo, update it
    if case_id in case_repo._store:
        case_repo.update(case_id, state=target, history=case["history"])

    # 4. Log audit event
    audit.log_event("case_state_transition", {
        "case_id": case_id,
        "from_state": current.value if current else None,
        "to_state": target.value,
        "actor": actor,
        "reason": reason,
    })

    return case


# ── Human Reopen Function ─────────────────────────────────────────────────────

def reopen(
    case: dict[str, Any],
    actor: str = "human",
    reason: str = "human_operator_reopened",
) -> dict[str, Any]:
    """
    Audited human override to reopen a halted or unrecovered case.
    Transitions state back to OPEN.
    """
    if "human" not in actor.lower():
        raise PermissionError(f"Only humans can reopen cases, actor was: {actor}")

    case_id = case.get("id") or case.get("case_id", "UNKNOWN")
    current_raw = case.get("state")
    current = CaseState(current_raw) if isinstance(current_raw, str) else current_raw

    # Reopen is supported for HALTED or UNRECOVERED cases
    if current not in (CaseState.HALTED, CaseState.UNRECOVERED):
        raise InvalidStateTransitionError(
            f"Cannot reopen case {case_id} in state {current.value} (only HALTED or UNRECOVERED can be reopened)"
        )

    case["state"] = CaseState.OPEN
    history_entry = {
        "from_state": current.value,
        "to_state": CaseState.OPEN.value,
        "actor": actor,
        "reason": reason,
        "timestamp": utcnow().isoformat(),
    }
    case.setdefault("history", []).append(history_entry)

    if case_id in case_repo._store:
        case_repo.update(case_id, state=CaseState.OPEN, history=case["history"])

    audit.log_event("case_reopened", {
        "case_id": case_id,
        "from_state": current.value,
        "to_state": CaseState.OPEN.value,
        "actor": actor,
        "reason": reason,
    })

    return case


# ── Halt Case Function ────────────────────────────────────────────────────────

def halt_case(
    case_id: str,
    reason: str = "case_halted",
    actor: str = "system",
) -> dict[str, Any]:
    """
    Halt a case and cancel every pending scheduled action for it.
    Safe to call multiple times (idempotent).
    """
    case = case_repo.get(case_id)
    if case is None:
        # Create a stub record in repo if not found
        case = {
            "id": case_id,
            "state": CaseState.HALTED,
            "customer_id": "UNKNOWN",
            "amount_usd": 0.0,
            "history": [],
        }
        case_repo._store[case_id] = case

    # Cancel every pending scheduled action for this case
    cancelled_count = scheduler.cancel_for_case(case_id)

    # If already halted, return safely (safe to call twice)
    if case.get("state") == CaseState.HALTED:
        audit.log_event("case_halt_noop", {
            "case_id": case_id,
            "reason": "already_halted",
            "cancelled_actions": cancelled_count,
        })
        return case

    # Otherwise transition to HALTED
    current_raw = case.get("state")
    current = CaseState(current_raw) if isinstance(current_raw, str) else current_raw

    case["state"] = CaseState.HALTED
    history_entry = {
        "from_state": current.value if current else None,
        "to_state": CaseState.HALTED.value,
        "actor": actor,
        "reason": reason,
        "timestamp": utcnow().isoformat(),
    }
    case.setdefault("history", []).append(history_entry)
    case_repo.update(case_id, state=CaseState.HALTED, history=case["history"])

    audit.log_event("case_halted", {
        "case_id": case_id,
        "from_state": current.value if current else None,
        "to_state": CaseState.HALTED.value,
        "actor": actor,
        "reason": reason,
        "cancelled_actions": cancelled_count,
    })

    return case


# ── Case Creation From Triggers ───────────────────────────────────────────────

VALID_TRIGGERS = {"failed_payment", "overdue_invoice", "funding_failed"}
_EVENT_DEDUP_MAP: dict[str, str] = {}  # event_id -> case_id


def clear_trigger_dedup_cache() -> None:
    _EVENT_DEDUP_MAP.clear()


def create_case_from_trigger(
    trigger_type: str,
    event_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Create a new case from one of the three triggers:
      - failed_payment
      - overdue_invoice
      - funding_failed
    Deduped by event_id: returns existing case if event_id has already been processed.
    """
    if trigger_type not in VALID_TRIGGERS:
        raise ValueError(
            f"Invalid trigger_type: {trigger_type!r}. Must be one of {sorted(VALID_TRIGGERS)}"
        )

    # Deduplication check by event ID
    if event_id in _EVENT_DEDUP_MAP:
        existing_case_id = _EVENT_DEDUP_MAP[event_id]
        existing_case = case_repo.get(existing_case_id)
        if existing_case:
            audit.log_event("case_trigger_deduped", {
                "event_id": event_id,
                "case_id": existing_case_id,
                "trigger_type": trigger_type,
            })
            return existing_case

    # Create new case
    case_id = str(uuid.uuid4())
    customer_id = str(payload.get("customer_id", "CUST-UNKNOWN"))
    amount_usd = float(payload.get("amount_usd") or payload.get("amount", 0.0))
    currency = str(payload.get("currency", "USD"))

    case = {
        "id": case_id,
        "case_id": case_id,
        "event_id": event_id,
        "trigger_type": trigger_type,
        "customer_id": customer_id,
        "amount_usd": amount_usd,
        "currency": currency,
        "state": CaseState.OPEN,
        "contact_count": 0,
        "last_contact_at": None,
        "created_at": utcnow().isoformat(),
        "payload": payload,
        "history": [{
            "from_state": None,
            "to_state": CaseState.OPEN.value,
            "actor": "system",
            "reason": f"Created via trigger: {trigger_type}",
            "timestamp": utcnow().isoformat(),
        }],
    }

    case_repo._store[case_id] = case
    _EVENT_DEDUP_MAP[event_id] = case_id

    audit.log_event("case_created_from_trigger", {
        "case_id": case_id,
        "event_id": event_id,
        "trigger_type": trigger_type,
        "customer_id": customer_id,
        "amount_usd": amount_usd,
    })

    return case

