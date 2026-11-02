#!/usr/bin/env python3
"""
CLI Script: Demo Reset (Step 13).

Wipes and reseeds deterministically in under 30 seconds:
  1. One escrow project at each stage:
     DRAFT, PLAN_APPROVED, FUNDED, IN_REVIEW, RELEASED, DISPUTED
  2. The 150+ recovery cases seeded into case_repo ready to run.
  3. Pre-computed evaluation run saved to data/eval_report.{json,md}.
  4. Prints frozen summary numbers.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.channels.outbox import clear_outbox
from backend.app.eval.report import generate_json_report, generate_markdown_report
from backend.app.eval.runner import run_evaluation
from backend.app.recovery.state_machine import clear_trigger_dedup_cache
from backend.app.scheduler.jobs.handlers import clear_scanned_invoices
from backend.app.simulator.datagen.generator import generate
from backend.app.simulator.profiles import CustomerProfile
from backend.app.stubs import audit, clock, llm, policy, repositories, scheduler
from backend.app.stubs.contracts_stub import CaseState

OUT_GEN = ROOT / "data" / "generated"
OUT_KEY = ROOT / "data" / "answer_key"
REPORT_MD = ROOT / "data" / "eval_report.md"
REPORT_JSON = ROOT / "data" / "eval_report.json"

ESCROW_STAGES = [
    "DRAFT",
    "PLAN_APPROVED",
    "FUNDED",
    "IN_REVIEW",
    "RELEASED",
    "DISPUTED",
]


def seed_escrow_stage_projects() -> list[dict[str, Any]]:
    """Seed one escrow project at each distinct lifecycle stage."""
    escrow_projects = []
    for idx, stage in enumerate(ESCROW_STAGES):
        proj = {
            "project_id": f"ESCROW-DEMO-{stage}",
            "title": f"Demo Milestone Project ({stage})",
            "client_id": f"CUST-{idx:05d}",
            "freelancer_id": f"CUST-{(idx+50):05d}",
            "amount_usd": 1000.0 + idx * 250.0,
            "currency": "USD",
            "stage": stage,
            "milestones": [
                {
                    "milestone_id": f"M-{stage}-1",
                    "title": f"Milestone 1 for {stage}",
                    "amount_usd": 500.0,
                    "status": "completed" if stage in ("RELEASED", "IN_REVIEW") else "pending",
                }
            ],
        }
        escrow_projects.append(proj)

    # Write to data/generated/escrow_staged.json
    staged_file = OUT_GEN / "escrow_staged.json"
    with open(staged_file, "w", encoding="utf-8") as f:
        json.dump(escrow_projects, f, indent=2)

    return escrow_projects


def reset_environment(seed: int = 42) -> dict[str, Any]:
    """Perform a deterministic wipe and reseed in under 30 seconds."""
    start_t = time.time()
    print("=================================================================")
    print("ProofPay Demo Reset: Deterministic Reseed & Pre-Evaluation")
    print("=================================================================")

    # 1. Clear in-memory repositories
    repositories.case_repo.reset()
    repositories.contact_repo._store.clear()

    # 2. Reset clock & scheduler
    clock.reset()
    scheduler.reset()

    # 3. Reset audit, outbox, llm, policy counters
    audit.clear()
    clear_outbox()
    llm.reset()
    policy.reset_daily_cap()
    clear_trigger_dedup_cache()
    clear_scanned_invoices()

    # 4. Regenerate synthetic fixtures
    print(f"1. Generating synthetic fixtures with seed={seed}...")
    generate(seed=seed, out_dir=OUT_GEN, answer_key_dir=OUT_KEY)

    # 5. Seed one escrow project at each stage
    print("2. Seeding escrow projects at all 6 stages...")
    staged_escrow = seed_escrow_stage_projects()

    # 6. Load generated cases and pre-seed the 150+ cases ready to run
    print("3. Pre-seeding 150+ recovery cases into CaseRepo...")
    cases_seeded = 0
    with open(OUT_GEN / "invoices.json", "r", encoding="utf-8") as f:
        invoices = json.load(f)
    with open(OUT_GEN / "subscriptions.json", "r", encoding="utf-8") as f:
        subscriptions = json.load(f)
    with open(OUT_KEY / "customers.yaml", "r", encoding="utf-8") as f:
        import yaml
        profiles = yaml.safe_load(f) or {}

    all_raw_cases = invoices + subscriptions
    for c in all_raw_cases:
        cid = str(c.get("customer_id") or c.get("id"))
        p_info = profiles.get(cid, {})
        prof = CustomerProfile(
            customer_id=cid,
            email=p_info.get("email", f"{cid}@example.com"),
            timezone=p_info.get("timezone", "UTC"),
            language=p_info.get("language", "en"),
            behaviour=p_info.get("behaviour", "pays_after_one_reminder"),
            opted_out=p_info.get("opted_out", False),
        )
        case_id = str(c.get("id") or c.get("invoice_id") or f"CASE-{cid}")
        amount = float(c.get("amount_usd") or c.get("amount", 100.0))
        repositories.case_repo._store[case_id] = {
            "id": case_id,
            "case_id": case_id,
            "customer_id": cid,
            "amount_usd": amount,
            "currency": str(c.get("currency", "USD")),
            "state": CaseState.OPEN,
            "contact_count": 0,
            "last_contact_at": None,
            "due_at": c.get("due_at") or c.get("created_at"),
            "payload": dict(c),
            "history": [],
            "profile": prof,
        }
        cases_seeded += 1

    # 7. Run pre-computed evaluation run
    print("4. Computing benchmark evaluation run...")
    comp = run_evaluation(cases_limit=None, seed=seed)

    # 8. Write frozen reports
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write(generate_markdown_report(comp))
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        f.write(generate_json_report(comp))

    elapsed = time.time() - start_t
    print(f"\nReset completed in {elapsed:.2f} seconds (< 30s target)!\n")

    # Print frozen numbers
    base = comp["baseline"]
    agent = comp["recovery_agent"]
    print("-----------------------------------------------------------------")
    print("FROZEN BENCHMARK NUMBERS:")
    print("-----------------------------------------------------------------")
    print(f"Total Seeded Cases Ready to Run : {cases_seeded} cases")
    print(f"Escrow Projects Staged         : {len(staged_escrow)} projects ({', '.join(ESCROW_STAGES)})")
    print(f"ProofPay Recovery Rate         : {agent.get('recovery_rate', 0.0) * 100:.1f}%")
    print(f"Naive Baseline Recovery Rate   : {base.get('recovery_rate', 0.0) * 100:.1f}%")
    print(f"Wrongfully Contacted (ProofPay): {agent.get('wrongful_contact_count', 0)} contacts")
    print(f"Wrongfully Contacted (Baseline): {base.get('wrongful_contact_count', 0)} contacts")
    print(f"Disputes Avoided               : {comp['comparison'].get('disputes_avoided', 0)} disputes")
    print(f"Unsafe Actions Blocked         : {agent.get('unsafe_actions_blocked', 0)} actions")
    print(f"Share with No LLM Call         : {agent.get('share_of_cases_with_no_llm_call', 0.0) * 100:.1f}%")
    print(f"Net Recovered Dollars (ProofPay): ${agent.get('net_dollars_recovered', 0.0):,.2f}")
    print(f"Net Recovered Dollars (Baseline): ${base.get('net_dollars_recovered', 0.0):,.2f}")
    print("-----------------------------------------------------------------\n")

    return comp


def main() -> None:
    reset_environment(seed=42)


if __name__ == "__main__":
    main()
