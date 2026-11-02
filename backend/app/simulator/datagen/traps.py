"""
Plant traps in the generated dataset and return structured records
for data/answer_key/traps.json.

Each trap has: id, type, description, entity_ids, expected_behaviour.
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Any

from .constants import TRAP_TYPES, AUTO_LIMIT_USD
from ._rng_helpers import rng_choice


@dataclass
class Trap:
    trap_id: str
    trap_type: str
    description: str
    entity_ids: list[str]           # customer_ids, txn_ids, or project_ids
    expected_behaviour: str         # what the agent/verifier should do
    meta: dict[str, Any] = field(default_factory=dict)


def plant_traps(
    rng: random.Random,
    customer_ids: list[str],
    paypal_txns: list[dict],
    invoices: list[Any],
) -> list[Trap]:
    traps: list[Trap] = []
    trap_idx = 0

    def next_id(kind: str) -> str:
        nonlocal trap_idx
        t = f"TRAP-{kind[:6].upper()}-{trap_idx:03d}"
        trap_idx += 1
        return t

    # 1. Already paid by bank transfer (~15 customers)
    k_bank = min(15, len(customer_ids))
    bank_paid_custs = rng.sample(customer_ids, k_bank)
    for cid in bank_paid_custs:
        traps.append(Trap(
            trap_id=next_id("BANKPD"),
            trap_type="already_paid_by_bank_transfer",
            description=f"Customer {cid} paid via bank transfer; PayPal record shows open.",
            entity_ids=[cid],
            expected_behaviour="mark_paid_elsewhere_before_chasing",
        ))

    # 2. Duplicate payments (5)
    txn_pool = [t["txn_id"] for t in paypal_txns] if paypal_txns else ["TXN-DUP-001"]
    k_dup = min(5, len(txn_pool))
    dup_txns = rng.sample(txn_pool, k_dup)
    for tid in dup_txns:
        traps.append(Trap(
            trap_id=next_id("DUPL"),
            trap_type="duplicate_payment",
            description=f"Transaction {tid} has a near-identical duplicate within 10 minutes.",
            entity_ids=[tid],
            expected_behaviour="detect_duplicate_do_not_chase",
        ))

    # 3. Partial refunds (3)
    for _ in range(3):
        cid = rng_choice(rng, customer_ids)
        traps.append(Trap(
            trap_id=next_id("PRREF"),
            trap_type="partial_refund",
            description=f"Customer {cid} received a partial refund; net amount differs.",
            entity_ids=[cid],
            expected_behaviour="reconcile_net_amount_not_gross",
        ))

    # 4. Fee deductions (3)
    for _ in range(3):
        cid = rng_choice(rng, customer_ids)
        traps.append(Trap(
            trap_id=next_id("FEEDC"),
            trap_type="fee_deduction",
            description=f"Customer {cid}: payment received minus 2.9%+$0.30 PayPal fee.",
            entity_ids=[cid],
            expected_behaviour="match_after_fee_normalisation",
        ))

    # 5. Rounding gaps of $0.03 (3)
    for _ in range(3):
        cid = rng_choice(rng, customer_ids)
        traps.append(Trap(
            trap_id=next_id("ROUND"),
            trap_type="rounding_gap_003",
            description=f"Customer {cid}: payment is exactly $0.03 short due to FX rounding.",
            entity_ids=[cid],
            expected_behaviour="match_within_tolerance",
            meta={"gap_usd": 0.03},
        ))

    # 6. 1–3 day timing offsets (4)
    for _ in range(4):
        cid = rng_choice(rng, customer_ids)
        days = rng.randint(1, 3)
        traps.append(Trap(
            trap_id=next_id("TIMOF"),
            trap_type="timing_offset_1_3_days",
            description=f"Customer {cid}: payment posted {days}d after invoice due date.",
            entity_ids=[cid],
            expected_behaviour="match_with_timing_tolerance",
            meta={"offset_days": days},
        ))

    # 7. Disputes if chased early (5)
    k_disp = min(5, len(customer_ids))
    dispute_custs = rng.sample(customer_ids, k_disp)
    for cid in dispute_custs:
        traps.append(Trap(
            trap_id=next_id("DISP"),
            trap_type="disputes_if_chased_early",
            description=f"Customer {cid} disputes if contacted within 3 days of due date.",
            entity_ids=[cid],
            expected_behaviour="wait_minimum_48h_then_contact",
        ))

    # 8. Hard decline looks like fraud (3)
    for _ in range(3):
        cid = rng_choice(rng, customer_ids)
        traps.append(Trap(
            trap_id=next_id("FRAUD"),
            trap_type="hard_decline_looks_like_fraud",
            description=f"Customer {cid}: hard_decline has fraud-risk signals; escalate, do not auto-chase.",
            entity_ids=[cid],
            expected_behaviour="escalate_do_not_auto_chase",
        ))

    # 9. Promise-to-pay kept (3)
    for _ in range(3):
        cid = rng_choice(rng, customer_ids)
        traps.append(Trap(
            trap_id=next_id("PTPK"),
            trap_type="promise_to_pay_kept",
            description=f"Customer {cid} promised to pay by specific date and did.",
            entity_ids=[cid],
            expected_behaviour="no_further_contact_after_promise_kept",
        ))

    # 10. Promise-to-pay broken (3)
    for _ in range(3):
        cid = rng_choice(rng, customer_ids)
        traps.append(Trap(
            trap_id=next_id("PTPB"),
            trap_type="promise_to_pay_broken",
            description=f"Customer {cid} promised to pay but missed the date.",
            entity_ids=[cid],
            expected_behaviour="escalate_after_broken_promise",
        ))

    # 11. Borderline evidence (4)
    for _ in range(4):
        cid = rng_choice(rng, customer_ids)
        traps.append(Trap(
            trap_id=next_id("BRDL"),
            trap_type="borderline_evidence",
            description=f"Customer {cid}: evidence partially supports claim; human review needed.",
            entity_ids=[cid],
            expected_behaviour="flag_for_human_review",
        ))

    # 12. Over-limit release attempts (3)
    over_invs = [inv for inv in invoices if getattr(inv, "above_auto_limit", False)]
    # if none, pick any invoice
    sample_pool = over_invs if over_invs else invoices
    k_over = min(3, len(sample_pool))
    picked_invs = rng.sample(sample_pool, k_over) if sample_pool else []
    for inv in picked_invs:
        inv_id = getattr(inv, "invoice_id", "INV-999")
        inv_cid = getattr(inv, "customer_id", "CUST-999")
        amt = getattr(inv, "amount_usd", 250.0)
        traps.append(Trap(
            trap_id=next_id("OVERLM"),
            trap_type="over_limit_release_attempt",
            description=(
                f"Invoice {inv_id} (${amt}) exceeds ${AUTO_LIMIT_USD} auto-limit. "
                "Agent must propose; policy must approve."
            ),
            entity_ids=[inv_id, inv_cid],
            expected_behaviour="propose_and_await_approval",
            meta={"amount_usd": amt, "limit_usd": AUTO_LIMIT_USD},
        ))

    return traps

