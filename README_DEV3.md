# ProofPay — Dev 3 Handover & Architecture Guide

**Author**: Dev 3 (Synthetic Data, Simulator, Reconciliation Engine, Recovery Agent & Evaluation)  
**Role**: Autonomous Debt Recovery, Reconciliation & Evaluation Subsystem  
**Core Architectural Law**: *"The agent proposes, the policy decides, code executes."*  
Recovery code never directly imports PayPal or email transport code; it only builds `Proposal` objects.

---

## 1. Temporary Stubs & Replacement Guide

All temporary stand-ins for teammates' components live exclusively in `backend/app/stubs/`. Each file contains `# TEMP: replaced by <real folder>` at the top.

| Stub File (`backend/app/stubs/`) | Replaced By | Description & Exports | Owner |
| :--- | :--- | :--- | :--- |
| `contracts_stub.py` | `contracts/` | `Proposal`, `PolicyDecision`, `Verdict`, `ActionKind`, `CaseState`, `FINAL_STATES` | Dev 1 |
| `clock.py` | `core/clock/` | `utcnow()`, `set_time()`, `advance_time()`, `simulate_days()`, `reset()`, `register_tick_listener()` | Dev 1 |
| `audit.py` | `audit/` | `log_event(event_type, payload)`, `get_events()`, `clear()` | Dev 1 |
| `policy.py` | `policy/` | `check(proposal) -> PolicyDecision`, 48h gap, quiet hours, cap, $200 limit | Dev 2 |
| `executor.py` | `executor/` | `execute(proposal, decision) -> receipt` (idempotency enforcement, outbox dispatch) | Dev 2 |
| `llm.py` | `llm/` | `call(prompt, system_prompt, schema, case_id) -> dict`, max 2 budget tracker | Dev 2 |
| `scheduler.py` | `scheduler/` | `enqueue(func, *args, **kwargs)`, `cancel_for_case(case_id)`, `remove_job(id)` | Dev 1 |
| `repositories.py` | `db/` | `case_repo` (`create`, `get`, `update`, `list_all`, `reset`), `contact_repo` (`add`, `list_for_case`) | Dev 1 |

---

## 2. Public Functions Others Should Call

Other developers (Dev 1, Dev 2, Dev 4) should integrate with these primary interface functions:

### A. Lifecycle & Operations
- **`process_case(case_id: str | None = None, trigger: dict | None = None) -> dict`**  
  `backend.app.agents.recovery.agent:process_case`  
  Main entry point for case recovery. Ingests triggers (`failed_payment`, `overdue_invoice`, `funding_failed`), dedupes, executes reconciliation check, diagnosis, prioritization, proposal building, policy evaluation, and post-result handling.
- **`halt_case(case_id: str, reason: str = "manual_halt", actor: str = "operator") -> dict`**  
  `backend.app.recovery.state_machine:halt_case`  
  Halts a recovery case and automatically cancels all scheduled jobs for that case. Safe to call idempotently.
- **`reopen(case: dict, actor: str = "human", reason: str = "human_operator_reopened") -> dict`**  
  `backend.app.recovery.state_machine:reopen`  
  Audited human operator override to reopen a `HALTED` or `UNRECOVERED` case back to `OPEN`. Rejects non-human actors.

### B. Reconciliation Engine
- **`check_already_paid(case: dict) -> str`**  
  `backend.app.reconciliation.matcher:check_already_paid`  
  Core operational query: *"has this person already paid, in any source?"* Returns `"auto_match"` (≥0.90), `"human_review"` (0.60–0.89), or `"no_match"`.
- **`pre_release_check(milestone: dict) -> bool`**  
  `backend.app.reconciliation.escrow_recon:pre_release_check`  
  Verifies that a valid funding capture exists for the full milestone amount before escrow release. Missing captures block release and are logged to the exception list.
- **`post_release_check(milestone: dict) -> bool`**  
  `backend.app.reconciliation.escrow_recon:post_release_check`  
  Verifies that milestone payout appears in records after release. Mismatches are recorded in the exception list.

### C. Escrow & Bridge Handlers
- **`handle_funding_failed(project_id, client_id, amount_usd, failure_code) -> dict`**  
  `backend.app.recovery.bridges:handle_funding_failed`  
  Opens a case of type `escrow_funding`.
- **`handle_instalment_failed(project_id, milestone_id, client_id, amount_usd, failure_code) -> dict`**  
  `backend.app.recovery.bridges:handle_instalment_failed`  
  Opens an `escrow_funding` case for a specific milestone failure.
- **`on_escrow_case_state_change(case: dict) -> str | None`**  
  `backend.app.recovery.bridges:on_escrow_case_state_change`  
  Dispatches external domain events: publishes `funding.resumed` on `RECOVERED`; publishes `project.flagged_for_freelancer` on `UNRECOVERED`.

### D. Dev 4 API & Evaluation Endpoints
- `GET /cases?sort=priority`: Prioritized recovery queue.
- `GET /cases?status=HALTED,UNRECOVERED`: Filtered cases with mandatory `reason` on every row.
- `GET /cases/{case_id}`: Case detail with attempt timeline history and safety policy audit trail.
- `GET /outbox`: Inspect messages sent to customer inbox.
- `GET /reconciliation/summary`: `matched`, `review`, and `exception` reconciliation metrics.
- `GET /approvals` & `POST /approvals/{id}/decide`: Ops approval queue for >$200 limit actions.
- `GET /dashboard/headline`: Headline numbers (`recovered_amount`, `at_risk_amount`, `case_count`, `recovered_count`).
- `GET /eval/latest`: Pre-computed benchmark scoreboard comparison.
- `POST /demo/{inject-failure, run-simulator, advance-clock, reset}`: Active only when `DEMO_MODE=True` (returns `404` otherwise).

---

## 3. PayPal & Escrow Event Names to Confirm

These standard event names are stored in `backend/app/recovery/constants.py`:

| Event Constant | Event String | Trigger / Publisher | Action / Effect |
| :--- | :--- | :--- | :--- |
| `EVENT_FUNDING_FAILED` | `funding.failed` | PayPal / Escrow webhook | Opens case of type `escrow_funding` |
| `EVENT_INSTALMENT_FAILED` | `instalment.failed` | Escrow milestone webhook | Opens case of type `escrow_funding` with milestone metadata |
| `EVENT_FUNDING_RESUMED` | `funding.resumed` | ProofPay Recovery Agent | Published when escrow funding case reaches `RECOVERED` |
| `EVENT_PROJECT_FLAGGED` | `project.flagged_for_freelancer` | ProofPay Recovery Agent | Published when escrow funding reaches `UNRECOVERED` |
| `EVENT_INVOICE_PAID` | `invoice.paid` | PayPal webhook | Immediately closes recovery case as `RECOVERED` |
| `EVENT_INVOICE_CANCELLED` | `invoice.cancelled` | PayPal webhook | Closes recovery case as `UNRECOVERED` |
| `EVENT_SUBSCRIPTION_FAILED` | `subscription.payment_failed`| PayPal webhook | Triggers recovery case for failed subscription |

---

## 4. Makefile Targets Needed from Dev 1

Please add the following targets to the repository `Makefile`:

```makefile
# Seed synthetic data, customers, subscriptions, invoices, and answer key
seed:
	python scripts/seed.py

# Run benchmark evaluation comparing ProofPay Recovery Agent vs Naive Baseline
eval:
	python backend/scripts/run_eval.py

# Complete deterministic environment wipe, reseed, and staged demo reset in <30s
demo-reset:
	python backend/scripts/demo_reset.py

# Run Dev 3 test suite
test-dev3:
	python -m pytest backend/tests -v
```

---

## 5. Architectural Invariant Checks
- **Import Boundary**: Validated via `.importlinter` and `test_import_linter.py`. No recovery or reconciliation code imports PayPal or channels.
- **Answer Key Privacy**: Validated via AST in `test_datagen_ast.py`. Only `simulator/`, `reconciliation/metrics.py`, and `eval/` import from `data/answer_key/`.
- **Zero Wrongful Contacts**: Validated via `test_ig3.py`. 100% of already-paid customers receive exactly zero contacts.

