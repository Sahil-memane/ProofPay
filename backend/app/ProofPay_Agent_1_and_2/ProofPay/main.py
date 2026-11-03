"""ProofPay – Scoping Agent Main Entry Point.

Provides:
1. Working CLI demo demonstrating milestone scoping, validation, approvals, and SHA-256 locking.
2. Modular FastAPI application runner for HTTP API consumption.
"""

import argparse
import json
import os
import sys
import uuid
from typing import Any, Dict
from dotenv import load_dotenv

# Ensure workspace is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
for path in (BASE_DIR, PARENT_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

load_dotenv()

from fastapi import FastAPI
from ProofPay.api.router import router as scoping_router
from ProofPay.api.verification_router import router as verification_router
from ProofPay.agents.scoping_agent.graph import ScopingAgentRunner
from ProofPay.agents.scoping_agent.state import STATUS_NEEDS_HUMAN_EDIT
from ProofPay.agents.scoping_agent.criteria_library import CRITERIA_REGISTRY
from ProofPay.services.database import db

app = FastAPI(
    title="ProofPay API - AI Payment Protection & Milestone Escrow",
    version="1.1.0",
    description="ProofPay: Agent 1 Scoping and Agent 2 Milestone Verification, orchestrated with LangGraph.",
)
app.include_router(scoping_router)
app.include_router(verification_router)


def print_banner():
    print("=" * 80)
    print("       PROOFPAY — AI-POWERED PAYMENT PROTECTION & RECOVERY PLATFORM       ")
    print("                 Agent 1: Scoping Agent (LangGraph)                       ")
    print("=" * 80)


def print_plan_table(milestones: list[dict]):
    print("\n" + "-" * 80)
    print(f"{'#':<3} | {'Milestone Title':<30} | {'Amount':<10} | {'Deadline':<10} | {'Criteria':<8}")
    print("-" * 80)
    for idx, m in enumerate(milestones, 1):
        crit_count = len(m.get("acceptance_criteria", []))
        amt_str = f"${m.get('payment_amount', 0):.2f}"
        print(f"{idx:<3} | {m.get('title', '')[:30]:<30} | {amt_str:<10} | {m.get('deadline', ''):<10} | {crit_count:<8}")

    print("-" * 80)
    print("\nDETAILED ACCEPTANCE CRITERIA BREAKDOWN:")
    for idx, m in enumerate(milestones, 1):
        print(f"\n  [Milestone {idx}] {m.get('title')}")
        print(f"  Description: {m.get('description')}")
        print(f"  Payment: ${m.get('payment_amount', 0):.2f} | Deadline: {m.get('deadline')}")
        print("  Criteria:")
        for c_idx, c in enumerate(m.get("acceptance_criteria", []), 1):
            crit_type = c.get("type")
            c_def = CRITERIA_REGISTRY.get(crit_type)
            cat = "HARD" if (c_def and c_def.is_hard) else "SOFT"
            must = "YES" if c.get("must_pass") else "NO"
            weight = c.get("weight", 0.0)
            print(f"    {c_idx}. [{cat}] {crit_type} (Weight: {weight*100:.0f}%, Must-Pass: {must})")
            print(f"       Params: {c.get('params')}")


def _collect_clarification_answers(questions: list[str]) -> Dict[str, str]:
    """Ask the operator for a separate answer to every clarification question."""
    answers: Dict[str, str] = {}
    print("\n[STEP 2b] Please answer each clarification question separately.")
    for index, question in enumerate(questions, 1):
        print(f"\n  Question {index}: {question}")
        try:
            answer = input("  Your answer: ").strip()
        except EOFError:
            answer = ""
        if answer:
            answers[question] = answer
    return answers


def run_cli_demo():
    """Run an end-to-end interactive CLI demonstration of the Scoping Agent."""
    print_banner()

    sample_description = """Build an e-commerce website with:
1. Homepage
2. Product listing
3. Shopping cart
4. Payment integration
5. Final deployment"""

    total_budget = 1000.0
    currency = "USD"
    deadline = "30 days"
    client_id = "client_001"
    freelancer_id = "freelancer_001"
    thread_id = f"demo_thread_{uuid.uuid4().hex}"

    print("\n[STEP 1] Receiving Project Submission:")
    print(f"  Client ID       : {client_id}")
    print(f"  Freelancer ID   : {freelancer_id}")
    print(f"  Total Budget    : ${total_budget:.2f} {currency}")
    print(f"  Project Deadline: {deadline}")
    print("  Project Scope   :")
    for line in sample_description.strip().splitlines():
        print(f"    {line}")

    if not os.getenv("GOOGLE_API_KEY"):
        print("\n  [NOTICE] GOOGLE_API_KEY is not set in environment or .env.")
        print("  Running with deterministic template fallback / offline mode.")

    runner = ScopingAgentRunner()
    project_payload = {
        "project_description": sample_description,
        "total_budget": total_budget,
        "currency": currency,
        "deadline": deadline,
        "client_id": client_id,
        "freelancer_id": freelancer_id,
    }

    print("\n[STEP 2] Running Scoping Agent Graph...")
    state = runner.start_project(project_payload, thread_id=thread_id)

    def print_execution_state(label: str, current: Dict[str, Any]) -> None:
        print(f"\n  {label}:")
        print(f"  - Status          : {current.get('project_status')}")
        print(f"  - Plan Source     : {current.get('plan_source')}")
        print(f"  - Needs Human Edit: {current.get('needs_human_edit')}")
        print(f"  - LLM Calls Made  : {current.get('llm_call_count')}")
        print(f"  - Validation Errs : {current.get('validation_errors')}")
        print(f"  - Unresolved      : {current.get('unresolved_parameters', [])}")

    print_execution_state("Execution Result", state)

    if state.get("project_status") == "CLARIFICATION_REQUESTED":
        questions = state.get("clarification_questions", [])
        print("\n" + "!" * 80)
        print("  [CLARIFICATION REQUIRED] The Scoping Agent needs additional information:")
        for index, question in enumerate(questions, 1):
            print(f"    {index}. {question}")
        print("!" * 80)

        answers = _collect_clarification_answers(questions)
        if len(answers) != len(questions):
            print("\n[STOP] Clarification was not submitted because one or more answers were blank.")
            print("Run the demo again and answer every question. No milestone approval has started.")
            return

        try:
            state = runner.submit_clarification(
                thread_id=thread_id,
                clarification_answers=answers,
            )
        except ValueError as exc:
            print(f"\n[STOP] Clarification input error: {exc}")
            return
        print_execution_state("Resumed Graph Result", state)

    current_status = state.get("project_status")
    if current_status in ("CLARIFICATION_REQUESTED", "NEEDS_CLARIFICATION", "ERROR"):
        print(f"\n[STOP] Cannot proceed. Current status: {current_status}")
        if state.get("error_message"):
            print(f"  Reason: {state.get('error_message')}")
        return

    milestones = state.get("milestones", [])
    if milestones:
        print_plan_table(milestones)

    # Human-edit drafts are deliberately not approvable.
    blocking_reasons = (
        state.get("needs_human_edit_reasons")
        or state.get("validation_errors")
        or state.get("unresolved_parameters")
        or []
    )
    if (
        current_status == STATUS_NEEDS_HUMAN_EDIT
        or state.get("needs_human_edit")
        or state.get("validation_errors")
        or state.get("unresolved_parameters")
    ):
        print("\n" + "!" * 80)
        print("  SCOPING BLOCKED — HUMAN INPUT REQUIRED")
        for reason in blocking_reasons:
            print(f"  - {reason}")
        print("  Approval workflow has not started.")
        print("  No plan hash, lock timestamp, or plan.approved event should exist.")
        print("!" * 80)
        return

    if current_status not in ("DRAFT", "PENDING_APPROVAL") or not milestones:
        print(f"\n[STOP] Plan is not ready for approval. Current status: {current_status}")
        return

    print("\n" + "=" * 80)
    print("                    HUMAN-IN-THE-LOOP APPROVAL WORKFLOW")
    print("=" * 80)

    print("\n[STEP 3] Client Review & Approval:")
    print(f"  Client '{client_id}' must review the displayed milestone plan.")
    try:
        client_decision = input("  Client approval (y/n): ").strip().lower()
    except EOFError:
        client_decision = "n"
    client_approved = client_decision in ("y", "yes")
    client_comment = ""
    if not client_approved:
        try:
            client_comment = input("  Reason / requested changes (optional): ").strip()
        except EOFError:
            client_comment = ""
    state_client = runner.submit_approval(
        thread_id=thread_id,
        user_id=client_id,
        role="client",
        approved=client_approved,
        comment=client_comment,
    )
    if state_client.get("error_message"):
        print(f"  [APPROVAL BLOCKED] {state_client['error_message']}")
        return
    print(f"  - Client Approved    : {state_client.get('client_approved')}")
    print(f"  - Freelancer Approved: {state_client.get('freelancer_approved')}")
    print(f"  - Project Status     : {state_client.get('project_status')}")
    if not client_approved:
        print("  [REVISION REQUIRED] Client did not approve. No plan was locked.")
        return

    print("\n[STEP 4] Freelancer Review & Approval:")
    print(f"  Freelancer '{freelancer_id}' must independently review the same plan.")
    try:
        freelancer_decision = input("  Freelancer approval (y/n): ").strip().lower()
    except EOFError:
        freelancer_decision = "n"
    freelancer_approved = freelancer_decision in ("y", "yes")
    freelancer_comment = ""
    if not freelancer_approved:
        try:
            freelancer_comment = input("  Reason / requested changes (optional): ").strip()
        except EOFError:
            freelancer_comment = ""
    final_state = runner.submit_approval(
        thread_id=thread_id,
        user_id=freelancer_id,
        role="freelancer",
        approved=freelancer_approved,
        comment=freelancer_comment,
    )
    if final_state.get("error_message"):
        print(f"  [APPROVAL BLOCKED] {final_state['error_message']}")
        return
    if not freelancer_approved:
        print("  [REVISION REQUIRED] Freelancer did not approve. No plan was locked.")
        print(f"  Reason: {final_state.get('needs_human_edit_reasons')}")
        return

    print("\n[STEP 5] Plan Lock Result:")
    print(f"  - Client Approved    : {final_state.get('client_approved')}")
    print(f"  - Freelancer Approved: {final_state.get('freelancer_approved')}")
    print(f"  - Final Status       : {final_state.get('project_status')}")
    print(f"  - SHA-256 Plan Hash  : {final_state.get('plan_hash')}")
    print(f"  - Locked Timestamp   : {final_state.get('approved_at')}")

    project_id = final_state.get("project_id")
    emitted_events = [
        event for event in db.get_emitted_events("plan.approved")
        if event.get("payload", {}).get("project_id") == project_id
        and event.get("payload", {}).get("plan_hash") == final_state.get("plan_hash")
    ]
    print("\n[STEP 6] Domain Events Emitted:")
    for event in emitted_events:
        print(f"  - Event: {event['event_name']} at {event['emitted_at']}")
        print(f"    Payload: {json.dumps(event['payload'], indent=6)}")

    success = bool(
        final_state.get("project_status") == "PLAN_APPROVED"
        and final_state.get("plan_hash")
        and final_state.get("approved_at")
        and emitted_events
    )
    print("\n" + "=" * 80)
    if success:
        print("  PROOFPAY SCOPING AGENT DEMO COMPLETED SUCCESSFULLY")
    else:
        print("  SCOPING NOT COMPLETED — PLAN WAS NOT LOCKED")
        if final_state.get("error_message"):
            print(f"  Reason: {final_state['error_message']}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ProofPay Scoping Agent Runner")
    parser.add_argument("--serve", action="store_true", help="Start the FastAPI web server")
    parser.add_argument("--port", type=int, default=8000, help="Port for the FastAPI web server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host for the FastAPI server")
    args = parser.parse_args()

    if args.serve:
        import uvicorn
        print(f"Starting ProofPay API server at http://{args.host}:{args.port}")
        uvicorn.run("ProofPay.main:app", host=args.host, port=args.port, reload=True)
    else:
        run_cli_demo()

