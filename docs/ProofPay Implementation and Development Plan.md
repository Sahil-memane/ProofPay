# ProofPay: Implementation and Development Plan

*Team Antigravity | 4 developers | Prepared 31 Oct 2026 | Hard deadline 12 Nov 2026, 3:00 pm EST (13 Nov, 1:30 am IST). Internal submission target: 11 Nov, evening IST.*

**Delivery principles** (they drive every decision below)

1. **Thin vertical slice first, depth second.** Get fund, verify, release working end to end with stub agents before making any agent smart.
2. **Contracts before code.** Database schema, Proposal and PolicyDecision objects, state-machine enums, event types and the OpenAPI spec are frozen at the end of Phase 0. Later changes go through a PR that all four developers review.
3. **Control spine before agents.** The audit log, idempotent executor and policy engine exist before any agent is allowed to write anything.
4. **Nobody waits for anybody.** Every external dependency (PayPal, LLM, GitHub, backend API) has a fake behind the same interface, so the four lanes run in parallel.
5. **LLM proposes, policy decides, code executes**, enforced structurally: agent modules cannot import the PayPal client (checked in CI).
6. **Integration gates.** At the end of each phase the team runs a scripted scenario on the hosted environment, not on laptops. A phase is done only when its gate passes.

# 1. Team Responsibilities

Names are placeholders; map them to people today. The split follows the project document (frontend, backend, agents) with recovery and data work made its own lane because it is the largest chunk that can start without PayPal.

## 1.1 Roles and responsibilities

| Developer | Role | Responsibilities |
| --- | --- | --- |
| Dev 1 | Tech Lead, Platform and PayPal Integration Engineer | (1) Repo, branch protection, CODEOWNERS, CI/CD, Render blueprint, public webhook URL; (2) Postgres schema and Alembic migrations (single schema owner); (3) FastAPI shell, config, logging, error model; (4) webhook receiver with signature verification and event-ID dedupe, event queue, worker; (5) append-only audit service and audit search; (6) PayPal client layer: OAuth token cache, Orders v2, Payouts, Subscriptions, Invoicing, Payment Links, Disputes; (7) PayPal MCP / Agent Toolkit adapter and the Executor (idempotency keys, retries, ACTION\_FAILED); (8) escrow funding, release and refund APIs; (9) scheduler infrastructure (DB-backed due-actions table, tick endpoint, keep-warm); (10) reputation ledger; (11) Postman collection and APIMatic SDK; (12) merge captain and deploy owner at every integration gate. |
| Dev 2 | AI and Policy Engineer (agents lead) | (1) Shared contracts: Proposal, PolicyDecision, enums; (2) llm\_client wrapper: schema validation, retry once, budgets, fallback, provider interface, FakeLLM; (3) Policy engine / mandate guard: rule registry, policy\_config, budgets, approval tasks; (4) Scoping agent: criteria library, validators, repair call, template fallback, plan\_hash; (5) Verifier agent: GitHub, HTTP and file collectors, SSRF defences, scoring, routing, rationale and post-checks; (6) Dispute agent and evidence pack; (7) cited read-only Q&A backend; (8) prompt-injection hygiene; (9) golden-set suites for every agent and the verifier accuracy report. |
| Dev 3 | Recovery, Reconciliation and Data Engineer | (1) Synthetic data generator with hidden answer key and planted traps; (2) customer simulator with hidden profiles and a controllable Clock; (3) reconciliation service: three-source matching, confidence tiers, precision and recall, exception list; (4) Recovery agent: case state machine, diagnosis rules, prioritisation, strategy table, multilingual templates, ladder, stop checks, tool wiring; (5) scheduler jobs: ladder steps, promise-to-pay, overdue-invoice scan, payday and quiet-hours timing; (6) email and outbox channel; (7) baseline strategy and evaluation harness; (8) bridges from funding failure and un-escrowed invoices into Recovery; (9) deterministic seeding and demo reset. |
| Dev 4 | Frontend and Experience Engineer | (1) Next.js app shell (static export), design tokens, role switcher, generated API client, mock API; (2) intake, plan review, edit and approve with validator errors, funding page with PayPal JS SDK v6 buttons; (3) submission form, verification progress, client review screen; (4) AG Grid unified ledger: master-detail, filters, unrecovered view, audit-trail drawer, CSV export, live updates; (5) headline number, recovery cases grid, case timeline, reconciliation view, dispute evidence-pack view, reputation view; (6) cited Q&A chat UI; (7) policy admin page and demo control panel (inject failure, advance clock, reset demo); (8) polish, accessibility, README and Devpost copy, screenshots, video lead. |

# 2. Repository Setup and Structure

## 2.1 Repository creation checklist (Dev 1, Oct 31)

1. Create the GitHub repository `proofpay` (public from day one, because the submission requires a public repo). Use a monorepo: one PR can change contract, backend and UI together.
2. Add `LICENSE` (MIT or Apache-2.0; it must show in the repo About panel), `README.md` stub, `.gitignore` (Python, Node, env files, data dumps), `.env.example`.
3. Enable secret scanning and push protection. Never commit `.env`. PayPal sandbox secrets live only in Render and in each developer's local `.env`.
4. Protect `main`: require a PR, one approval, passing status checks (backend CI, web CI, import-boundary check), linear history.
5. Add `.github/CODEOWNERS` from the matrix in 1.3 and a PR template.
6. Create the project board with columns Backlog, In progress, In review, Done. Create one card per block in section 6 and assign owners.
7. Create labels: area/backend, area/web, area/agents, area/recovery, contract-change, blocker, gate.
8. Add `docker-compose.yml` (Postgres), `Makefile`, `.pre-commit-config.yaml` (ruff, ruff-format, mypy on contracts and policy, prettier, eslint).
9. Add GitHub Actions workflows (2.7), verify a trivial PR runs them green.
10. Add `docs/adr/` and write the first decision records as they are made (2.9).
11. Add `render.yaml` skeleton and connect Render to the repo (Phase 0, block 0.7).
12. Each developer clones, runs `make up && make test`, and opens a first PR (a one-line change) to prove access and CI.

## 2.2 Directory structure

```
proofpay/
├── README.md  LICENSE  render.yaml  docker-compose.yml  Makefile  .env.example
├── .github/ (CODEOWNERS, pull_request_template.md, workflows/)
├── contracts/                 # generated JSON schemas + openapi.json, committed
├── backend/
│   ├── pyproject.toml
│   ├── alembic/versions/
│   ├── app/
│   │   ├── main.py            # FastAPI app, mounts web static export
│   │   ├── core/              # config, logging, clock, errors, security, demo-mode flags
│   │   ├── db/                # session, models/, repositories/
│   │   ├── contracts/         # Proposal, PolicyDecision, enums, NormalizedEvent (Dev 2)
│   │   ├── api/               # routers: projects, milestones, ledger, cases, audit,
│   │   │                      #   qa, reputation, dashboard, sim, internal, webhooks
│   │   ├── ingestion/         # signature verify, dedupe, queue, worker, normalizer, handlers
│   │   ├── paypal/            # auth, client, orders, payouts, subscriptions, invoicing,
│   │   │                      #   disputes, gateway (rest | mcp), fake_paypal
│   │   ├── executor/          # ONLY importer of paypal/ and channels/
│   │   ├── policy/            # engine, rules/, config loader, approvals
│   │   ├── llm/               # client, providers/, prompts/, fake_llm
│   │   ├── agents/            # scoping/, verifier/, recovery/, dispute/, qa/
│   │   ├── collectors/        # github, http_prober, file_inspector
│   │   ├── escrow/            # state machine, ledger, funding, release, refund
│   │   ├── recovery/          # case state machine, diagnose, prioritize, strategy,
│   │   │                      #   templates/, tools
│   │   ├── reconciliation/   # normalizer, matcher, tiers, metrics
│   │   ├── scheduler/         # due_actions, tick, jobs/
│   │   ├── audit/             # writer, search, hash chain
│   │   ├── reputation/
│   │   ├── channels/          # email adapter, outbox
│   │   ├── simulator/         # datagen/, profiles, sim events
│   │   └── eval/              # baseline, runner, metrics, report
│   ├── tests/ (unit/, property/, golden/, scenarios/, fixtures/)
│   └── scripts/ (seed.py, demo_reset.py, replay_event.py, run_eval.py)
├── web/
│   ├── package.json  next.config.js (output: 'export')
│   ├── src/app/ (intake, project, ledger, cases, recon, audit, reputation, qa, admin)
│   ├── src/components/ (ledger-grid, plan-editor, evidence-form, status-chip,
│   │                    policy-banner, headline, case-timeline)
│   ├── src/lib/ (generated api client, hooks, formatters)
│   └── mocks/ (MSW handlers from OpenAPI)
├── data/ (generated/, answer_key/)   # answer_key read only by eval and recon metrics
├── fixtures/                  # demo evidence: sample sites, files, GitHub fixture repo notes
├── postman/  sdk/ (APIMatic output)
└── docs/ (adr/, erd.md, sponsors.md, demo-script.md, runbook.md, architecture/ diagrams)
```

The web app is a static export served by FastAPI, so there is one Render service, one origin (no CORS) and one cold start. Static export cannot pre-render unknown ids, so detail pages use query strings (`/project?id=...`) instead of dynamic route segments, and the app uses no server-only Next.js features.

## 2.4 Technology baseline

- **Backend:** Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2 with Alembic, Pydantic v2, httpx, APScheduler (in-process), pandas, rapidfuzz, Jinja2, zoneinfo, pytest, Hypothesis, ruff, mypy, import-linter.
- **Web:** Node 20, Next.js (App Router, static export), TypeScript, AG Grid, PayPal JS SDK v6, openapi-typescript, MSW, Playwright (smoke only).
- **Data and hosting:** PostgreSQL (Render free instance; Oracle Always Free VM as fallback), Postgres full-text search (Elastic only if a free tier covers judging).
- **Tooling:** GitHub Actions, Newman for the Postman collection, APIMatic for the SDK.
- **AG Grid note (decide in Phase 0):** master-detail rows are an AG Grid Enterprise feature. Check the sponsor's Devpost page for a trial or licence key. Fallback: Community grid with a custom expandable detail panel or side drawer.

## 2.5 Environment variables (`.env.example`)

`DATABASE_URL`, `APP_BASE_URL`, `DEMO_MODE`, `SIMULATOR_ENABLED`, `INTERNAL_TICK_TOKEN`, `POLICY_SIGNING_KEY`, `PAYPAL_MODE=sandbox`, `PAYPAL_BASE_URL`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`, `PAYPAL_EXEC_MODE=rest|mcp`, `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL_CHEAP`, `LLM_MODEL_QA`, `LLM_DAILY_CAP`, `GITHUB_TOKEN` (read-only), `SMTP_HOST/PORT/USER/PASSWORD` or `EMAIL_MODE=outbox`, `NEXT_PUBLIC_API_BASE`, `NEXT_PUBLIC_PAYPAL_CLIENT_ID`, `AGGRID_LICENSE_KEY`.

## 2.6 Local environment

`make up` (docker-compose Postgres), `make migrate`, `make seed`, `make dev-api` (Uvicorn reload), `make dev-web`, `make test`, `make lint`, `make replay EVENT=<id>`, `make eval`, `make demo-reset`. Webhooks cannot reach laptops, so local work uses `/sim/events` and the replay script; real PayPal webhooks are tested only against the Render URL, which exists from Phase 0.

## 2.7 CI/CD

- **backend CI:** ruff, mypy, import-linter, pytest (unit, property, golden, scenarios with FakePayPal and FakeLLM), OpenAPI diff check (fails if the committed `contracts/openapi.json` is stale).
- **web CI:** eslint, type-check, `next build` (static export), generated client up to date.
- **newman.yml:** runs the Postman collection against the hosted URL on demand (manual trigger) and nightly.
- **keepwarm.yml:** scheduled workflow calling `/healthz` and `/internal/tick` with the tick token every 5 minutes (also drives the scheduler when the free service sleeps).
- **CD:** Render auto-deploys `main` with health check `/healthz` and a pre-deploy migration command. Production values live only in the Render dashboard.

## 2.8 Test strategy and fakes

- **Unit:** every policy rule, validator, collector, state transition.
- **Property (Hypothesis):** random plan edits never yield amounts that do not sum; random event orderings never leave a terminal state; the policy engine never returns allow when any check failed.
- **Golden sets:** 10 job descriptions for Scoping; labelled submissions (clear pass, clear fail, borderline) for the Verifier; planted-trap records for reconciliation.
- **Scenario tests:** S1 to S8 listed in 6.8 (block 4.8), run with FakePayPal in CI and against the hosted environment at gates.
- **Fakes:** `FakePayPal` (same interface as the gateway, programmable failures, emits webhooks into the ingestion path), `FakeLLM` (canned or scripted JSON, can return invalid JSON to test fallbacks), `FakeGitHub` and recorded HTTP fixtures, MSW mock API for the web app.

## 2.9 Decision records

Keep short ADRs in `docs/adr/`: ADR-001 Payouts or fallback release path; ADR-002 MCP tool inventory and exec mode; ADR-003 static-export web app served by FastAPI; ADR-004 LLM provider and budgets; ADR-005 AG Grid edition; ADR-006 hosting and keep-warm; ADR-007 auto-release timer semantics.

# 6. Detailed Development Roadmap

## 6.1 Dependency analysis and build order

- **Everything depends on** the schema and shared contracts, so they are Phase 0.
- **Every write path** (escrow release, refund, recovery action) depends on the same three parts: policy engine, audit service, executor. These form the spine and are built in Phase 1, before any agent can act.
- **Critical path** (longest chain, cannot be parallelised): schema, then webhook ingestion and PayPal client, then Orders funding, then Scoping and plan lock, then collectors and Verifier, then policy release rules, then executor payout, then payout webhook, then ledger UI. Roughly six working days. A slip here moves the deadline, so Dev 1 and Dev 2 protect it first.
- **Lanes that need no PayPal:** data generator, simulator and reconciliation (Dev 3); the UI against mocks (Dev 4); collectors against fixtures (Dev 2). They start on day one and plug in at gates.
- **Late joins:** Recovery agent needs policy, executor and scheduler (available 3 to 4 Nov); Dispute agent needs both engines (7 Nov); reputation needs releases and recoveries (7 Nov); Q&A needs audit data (7 Nov).
- **Why escrow first:** it is the primary demo path and holds the never-cut features (fund, verify, release, mandate guard, dispute halt, audit log, AG Grid ledger, hosted demo, video). Recovery is the second act and starts early only in its dependency-free parts.
- **Integration order:** the system is assembled in six steps, each a gate: contracts and environment (IG-0), plan to funded (IG-1), full escrow path (IG-2), recovery loop (IG-3), trust layer and cross-engine flows (IG-4), deployed and rehearsed (IG-5).

## 6.2 Calendar at a glance (IST)

| Phase | Dates | Goal | Gate |
| --- | --- | --- | --- |
| 0. Foundations and contracts | 31 Oct to 1 Nov (noon) | Repo, CI, sandbox verified, schema and contracts frozen, Render live | IG-0 |
| 1. Spine and plan-to-fund | 1 Nov (pm) to 3 Nov | Ingestion, audit, policy, executor, Scoping, funding; data and simulator ready | IG-1 |
| 2. Escrow engine complete | 3 Nov to 6 Nov | Collectors, Verifier, release via Payouts/MCP, review, refund, ledger v1 | IG-2 |
| 3. Recovery engine | 3 Nov to 7 Nov | Reconciliation, Recovery loop, scheduler, invoice chaser, baseline | IG-3 |
| 4. Trust layer and integration | 6 Nov to 8 Nov | Dispute agent, reputation, Q&A, bridges, scenario suite | IG-4, feature freeze |
| 5. Hardening, polish, sponsor deliverables | 9 Nov | Bug bash, security pass, seed data, Postman, SDK, README | IG-5 prep |
| 6. Deploy, rehearsal, video | 10 Nov | Clean deploy, judge dry-run, recorded and uploaded video | IG-5 |
| 7. Submission | 11 Nov (12 Nov morning is emergency buffer only) | Devpost submitted and verified | Done |

## 6.4 Phase 0: Foundations and Contracts (31 Oct to 1 Nov noon)

**Owners:** all four; Dev 1 leads. **Goal:** every developer runs the system locally, CI is green, PayPal sandbox facts are verified, contracts are frozen, a public URL exists.

**Block 0.1 Repository and CI (Dev 1)**

1. Execute checklist 2.1 end to end and merge the skeleton.
2. Verify all four developers can open a PR and see CI pass.
3. Seed the board with one card per block in this section.

**Block 0.2 PayPal sandbox and day-1 checks (Dev 1, Dev 3 pairs on checks)**

1. Create or confirm the developer account. Create sandbox accounts: one Business for the ProofPay platform, one Personal buyer (client), one account to receive payouts (freelancer).
2. Create the REST app, record client ID and secret in the Render dashboard and local `.env` only.
3. **Payouts check:** send a 1 USD payout via API from the Business account. If it fails for lack of access, trigger **Decision D-1**: release will use Orders plus Invoicing (record in ADR-001); the executor interface does not change.
4. **MCP check:** run the PayPal MCP / Agent Toolkit quickstart, list the tools it exposes, and record exactly which of our actions (create order, capture, payout, invoice, reminder) it can perform in ADR-002. Anything it cannot do goes through the REST client behind the same `PayPalGateway` interface; `PAYPAL_EXEC_MODE` switches between them.
5. **Orders check:** create and capture a test order with the sandbox buyer.
6. **Webhook check (after block 0.7):** register the Render URL, store the webhook ID, subscribe to candidate events, and confirm exact names in the docs: capture completed, capture denied, capture refunded, payouts batch and item success/denied/failed, subscription payment failed, invoice paid, invoice cancelled, dispute created/updated/resolved. Confirm signature verification works on a real delivery.
7. Record all outcomes in `docs/adr/` and `docs/sponsors.md`.

**Block 0.3 Data model and migrations (Dev 1)**

1. Tables: users, customers, projects (with plan\_hash), milestones (criteria JSON, state, amount, deadline), submissions, ledger\_entries (funding, hold, release, refund), cases, attempts, transactions, reconciliation\_records, reconciliation\_matches, webhook\_events, executor\_actions, audit\_log, reputation\_events, reputation, policy\_config, llm\_usage, disputes, evidence\_packs, outbox\_messages, scheduled\_actions, approval\_tasks, eval\_runs.
2. Integrity rules in the schema: unique `webhook_events.event_id`; unique `executor_actions.idempotency_key`; at most one release ledger entry per milestone; amounts as integer minor units or Decimal with currency; audit\_log insert-only (revoke UPDATE and DELETE, add trigger).
3. State columns use enums that mirror the two state machines in the project document, section 7.
4. Write the initial Alembic migration and a `policy_config` seed (limits, thresholds, quiet hours, budgets). Publish `docs/erd.md`.

**Block 0.4 Shared contracts (Dev 2 authors, Dev 1 reviews)**

1. Pydantic models: Proposal, PolicyDecision and Check (exactly the shapes in the agent specification, sections 0.2 and 0.3), NormalizedEvent, AuditEntry, error codes.
2. Enums for milestone states, case states, actors, action types.
3. Protocols for `LLMClient`, `PayPalGateway`, `Collector`, `Clock`; `FakeLLM` and `FakePayPal` stubs so others can code against them today.
4. Generate JSON schemas into `/contracts`.

**Block 0.5 API contract (Dev 1 and Dev 4)**

1. Draft the OpenAPI spec with these endpoints: projects (create, get, edit milestone, approve, fund, capture); milestone submissions and review; unified ledger list and detail; cases list, detail and approve; audit search and export; dashboard headline; reconciliation summary; reputation by subject; Q\&A; policy config get/update (demo); `/webhooks/paypal`; `/sim/events`; `/internal/tick`; `/healthz`.
2. Generate the TypeScript client and MSW handlers; Dev 4 builds against them immediately.

**Block 0.6 Frontend scaffold (Dev 4)**

1. Create the Next.js app with static export, shell layout, navigation (Escrow, Recovery, Ledger, Reconciliation, Audit, Reputation, Q&A, Admin), design tokens and status-chip component.
2. Add the role switcher (client, freelancer, merchant, admin) as demo auth.
3. Install AG Grid and resolve D-3 (Enterprise key or Community fallback), record in ADR-005.

**Block 0.7 Hosting skeleton (Dev 1)**

1. Write `render.yaml`: one web service (FastAPI serving the static web build, with worker loop and scheduler in-process) and one Postgres; health check; pre-deploy migrate command.
2. Deploy a hello-world build, measure cold start and idle sleep, check free database limits and expiry. If Render cannot hold, trigger the Oracle VM fallback (ADR-006).
3. Add the keep-warm workflow and the `/internal/tick` token.

**Block 0.8 LLM provider and wrapper (Dev 2)**

1. Choose a free-tier provider after testing real rate limits; record in ADR-004.
2. Implement `llm_client.call(task, json_schema, budget_key)`: schema validation, one retry on invalid JSON, fallback to rule path, call logging; budgets read from `llm_usage` (2 calls per case or milestone, plus daily cap).
3. Implement the untrusted-input helper that places job text, evidence and customer replies in delimited data fields, never in the system prompt.

**Block 0.9 Developer environment (Dev 1)**

1. docker-compose, Makefile targets, `.env.example`, pre-commit.
2. A smoke test (`make smoke`) that boots the API, applies migrations and hits `/healthz`.

**Exit criteria (IG-0, 1 Nov 14:00)**

- All four developers ran `make up && make test` locally and merged a PR.
- Schema, contracts and OpenAPI merged; TypeScript client and mocks generated.
- Public Render URL live with health check; webhook registered and a real sandbox event received and signature-verified.
- D-1 (Payouts), D-2 (MCP vs REST), D-3 (AG Grid edition), D-4 (LLM provider) decided and recorded.
- Import-boundary check and CI green on main.

## 6.5 Phase 1: Spine and Plan-to-Fund (1 Nov afternoon to 3 Nov)

**Owners:** Dev 1 (spine, PayPal, funding), Dev 2 (policy, Scoping), Dev 3 (data, simulator), Dev 4 (intake, plan, funding UI). **Goal:** the control spine exists (events in, audit out, policy decides, executor acts) and the first half of the escrow path works on the hosted environment: intake, plan, approval, funding, FUNDED.

**Block 1.1 Ingestion and event pipeline (Dev 1)**

1. The webhook route reads the raw body, verifies the PayPal signature (transmission ID, time, certificate URL, algorithm, signature, webhook ID) using PayPal's verification API, and returns 200 quickly.
2. Insert into `webhook_events` with `ON CONFLICT (event_id) DO NOTHING`, status pending. Duplicates are acknowledged and ignored.
3. A worker loop (asyncio task in the web process) claims rows with `FOR UPDATE SKIP LOCKED`, normalises to NormalizedEvent, dispatches through a registry (event type to handler), marks done, retries with backoff, and parks repeated failures as dead-letter with an audit row.
4. `/sim/events` accepts simulated events in demo mode (internal token header, no PayPal signature) and feeds the same queue, so simulated and real events share one code path.
5. `scripts/replay_event.py` re-queues a stored event for debugging.
6. Tests: the same event five times gives one processing; a bad signature is rejected; a failing handler retries, then dead-letters.

**Block 1.2 Audit service (Dev 1)**

1. One function `audit.write(subject, actor, decision, reason, inputs, checks, paypal_id, outcome)`; actors are agent, policy, executor, human, system.
2. Insert-only enforcement (privileges plus trigger). Add `prev_hash` and `row_hash` columns for a tamper-evident chain; it is cheap and strengthens the audit story.
3. Postgres full-text index (tsvector with GIN) over reason and subject; endpoints for search, per-subject timeline and CSV export.
4. Rule: no state transition anywhere without an audit row in the same transaction. A test helper asserts it.

**Block 1.3 PayPal client v1 (Dev 1)**

1. Async httpx client; OAuth client-credentials with the token cached until shortly before expiry and refreshed on 401.
2. Orders v2 create, get, capture; Payouts create and get (extended in Phase 2). Every write sends `PayPal-Request-Id`.
3. Exponential backoff on 429 and 5xx, no retry on 4xx validation errors; typed errors; request logging with secrets and tokens redacted.
4. Implement `PayPalGateway` for rest mode. `FakePayPal` mirrors it, has switches for failure injection, and can emit webhooks into ingestion.

**Block 1.4 Executor v1 (Dev 1)**

1. `executor.execute(proposal, decision)`: verifies the signed allow decision, checks `executor_actions` for the idempotency key (subject ID + action + attempt), performs the action, records the result, writes audit rows before and after.
2. State change and ledger entry happen in one DB transaction; the PayPal call sits outside it and the result is confirmed by webhook (the webhook is the source of truth).
3. Failure path: retry with backoff, then ACTION\_FAILED and escalate\_to\_human. Amount mismatch stops and flags.
4. Action registry for now: create\_order and capture\_order; extended later with payout, refund, retry, reminder and payment link.

**Block 1.5 Policy engine v1 (Dev 2): highest priority of the phase**

1. Rule registry: each rule is a function taking context and returning a Check. The engine runs every rule registered for the action type and aggregates (any deny wins, then needs\_approval, then allow). The output is the PolicyDecision object. A deny is final and never retried with different wording.
2. Escrow rules: max\_project\_total, min\_milestone\_amount, max\_release\_amount, auto\_action\_limit (needs\_approval above it), recipient\_verified, milestone\_funded, ledger\_balance\_sufficient, no\_open\_dispute, no\_duplicate\_release, amount\_matches\_milestone, llm\_budget.
3. Recovery rules (added now so Dev 3 can code against them): contact\_cap (4), min\_gap\_48h, quiet\_hours (9 pm to 8 am customer time), opt\_out, channel\_allowlist (email, payment link), daily\_action\_cap, no\_open\_dispute, auto\_action\_limit (200 USD).
4. `policy_config` loader with a 30-second cache and an admin endpoint to change a limit (used on camera to demonstrate the guard).
5. needs\_approval creates an `approval_tasks` row; approval issues a decision the executor accepts.
6. Every decision is audited with all checks listed.
7. Tests: one per rule, table-driven scenarios, and a property test that allow implies every check passed.

**Block 1.6 Scoping agent (Dev 2)**

1. Criteria library as a versioned JSON registry: type, parameter schema, collector name, default weight, hard or soft (url\_returns\_200, url\_contains\_text, github\_pr\_merged, github\_checks\_passing, repo\_file\_exists, file\_type\_size, file\_has\_sections, manual\_review).
2. Pipeline: pre-validate (length, currency, budget within limits), LLM call 1 (2 to 6 milestones, schema-constrained, library types only), validators, repair (LLM call 2 with the exact error list), then template fallback (single milestone or split by thirds, flagged for human edit). Clarification path: at most 3 questions, asked once.
3. Validators are pure code shared with the edit endpoint: amounts sum to the total (rounding fixed on the last milestone), deadlines ordered and inside the project deadline, at least one hard criterion per milestone, hard criteria carry at least 70 percent of the weight, library membership, complete params, each amount between the minimum and the per-release cap.
4. Persist DRAFT. Every edit reruns validators with no LLM call. Approval by both parties locks the plan: `plan_hash` is the SHA-256 of canonical JSON (sorted keys) of milestones and criteria; state becomes PLAN\_APPROVED.
5. Golden set of 10 job descriptions plus Hypothesis property tests (random edits never break the sum).

**Block 1.7 Escrow API and funding (Dev 1)**

1. Endpoints: create project (invokes Scoping), get, edit milestone, approve (per party), fund, capture.
2. Server-side funding guard: no order unless both approvals exist and `plan_hash` matches the stored hash; the order amount equals the project total.
3. Create an Orders v2 order (intent CAPTURE, currency from the project) and return the order ID to the JS SDK; the capture endpoint is called from the client on approval.
4. The capture-completed webhook handler is the source of truth: write the ledger FUNDING entry, move milestones to FUNDED, audit, store the PayPal capture ID. Capture denied or amount mismatch: stop, flag, emit a `funding.failed` event (consumed by Recovery in Phase 4).
5. Test against the sandbox buyer and against FakePayPal in CI.

**Block 1.8 Synthetic data generator (Dev 3)**

1. A seeded generator in `simulator/datagen` so every run is identical.
2. Produce customers (id, email, language, timezone, opt-out, history), about 90 failed-subscription events, about 60 overdue invoices, PayPal-format transactions, a merchant sales CSV and a bank statement CSV (200+ reconciliation records across three sources), and 10+ escrow projects with evidence fixtures.
3. Plant every trap from the project document: already paid by bank transfer, duplicates, partial refunds, fee deductions and rounding gaps (for example 0.03), timing offsets, customers who dispute if chased early, hard declines that look like fraud, promise-to-pay that is kept or broken, borderline evidence, over-limit releases.
4. Write the hidden answer key to `data/answer_key/` (true profile per customer, true matches, expected verifier labels). Add loaders (`make seed`) and a test that nothing outside the allowed modules imports the answer key.

**Block 1.9 Customer simulator (Dev 3)**

1. Profiles: pays after one reminder, needs payment link, needs card update, prefers split or Pay Later, ignores everything, disputes if chased early, already paid elsewhere.
2. `respond(case, action, now)` returns events (payment success, free-text reply, dispute, opt-out) with seeded probabilities that depend on how well the action matches the hidden cause.
3. A `Clock` abstraction (real or fake) so tests and the demo can advance time; events enter through `/sim/events`.
4. Unit tests per profile; export the assumptions text for the honesty panel in the UI.

**Block 1.10 Frontend: intake, plan, funding (Dev 4)**

1. Intake form (job text, total, currency, optional deadline, parties) with a scoping progress state; clarification questions shown once.
2. Plan editor: editable milestone table, criteria chips with weight and must-pass, validator errors from 422 responses shown inline and blocking the save; per-party approval buttons and a locked state showing plan\_hash.
3. Funding page: PayPal JS SDK v6 buttons, sandbox buyer instructions, success and failure states; waits for FUNDED by polling.
4. Project detail page with a state timeline. Switch from MSW mocks to the real API as endpoints land on 2 Nov.

**Block 1.11 Postman v0 (Dev 1)**

1. Collection folders for auth, orders (create, capture) and webhook simulation, plus an environment file with placeholders.

**Integration Gate IG-1 (3 Nov evening, hosted URL, Dev 1 runs it)**

1. Paste a job description; the plan appears (real LLM). Break an amount sum in the editor; the save is blocked and the rule is named.
2. Both parties approve; plan\_hash is shown.
3. The buyer funds via the PayPal sandbox; the real webhook arrives and is signature-verified; milestones turn FUNDED; audit rows are visible; the ledger lists them.
4. Replay the same webhook five times: still one ledger entry.
5. Call the funding endpoint with a tampered plan: refused.
6. Policy unit suite green; seeded dataset loads; one simulated event travels through `/sim/events` into the audit log.

**Exit criteria (Phase 1)**

- The IG-1 script passes on the hosted environment with no manual database edits.
- Scoping golden set: 10 of 10 outputs pass every validator; property tests green.
- Policy engine rules v1 merged with tests; the executor refuses a proposal with no allow decision.
- Datagen output and answer key committed; simulator profile tests green.
- All new endpoints appear in `contracts/openapi.json`; the web client is regenerated.

## 6.6 Phase 2: Escrow Engine Complete (3 Nov to 6 Nov)

**Owners:** Dev 2 (Verifier), Dev 1 (release path, refund, timers), Dev 4 (ledger and submission UI), Dev 3 (fixtures and support). **Goal:** the never-cut path works end to end (fund, submit, verify, review or auto-release, payout, ledger) and the mandate guard blocks an over-limit release on screen.

**Block 2.1 Evidence collectors (Dev 2)** Shared contract: every collector returns a Fact `{criterion_id, passed, value, source, checked_at}` and never raises on remote failure; a remote failure becomes a failed fact with a reason, or VERIFY\_DELAYED when it is a rate limit or outage.

1. GitHub collector: PR state and merged flag, combined status or check runs, files changed; read-only token; ETag caching; on 403 or 429, back off, then mark VERIFY\_DELAYED (never a fail).
2. HTTP prober: only http and https; resolve DNS and reject private, loopback, link-local and metadata ranges, re-checked after every redirect; limited redirects, 5-second timeout, 1 MB body cap; three probes spread over time (shortened in demo mode) with a majority vote; record status code, response time and text-contains result.
3. File inspector: detect type by magic bytes, enforce a size cap (5 MB), compute SHA-256, extract text with safe parsers (PDF, DOCX, Markdown) and check headings. Never execute or render uploaded content; only extracted text goes onward. Store files in Postgres (bytea), because free-tier disks are ephemeral.
4. Tests: an SSRF suite (localhost, 169.254.x.x, 10.x, redirect to an internal host, DNS rebinding case) and recorded-fixture tests per collector.

**Block 2.2 Scoring and routing (Dev 2)**

1. score = sum of weights of passed hard criteria divided by the sum of weights of all hard criteria. Soft (manual\_review) criteria never change the score.
2. Route with thresholds read from policy\_config: score 0.90 or above and every must\_pass passed gives RELEASE\_PENDING; 0.60 to 0.89, or a must\_pass failed with the rest good, or manual-review criteria present, gives IN\_REVIEW; below 0.60 returns to the freelancer (SUBMITTED), and after the attempt limit (default 2 resubmissions) goes to DISPUTED.
3. Unreachable or empty evidence counts as a failed criterion with reason unreachable.
4. Table-driven tests on every threshold edge (0.89, 0.90, 0.59, 0.60).

**Block 2.3 Rationale call (Dev 2)**

1. One LLM call per submission. Input: the fact table plus criterion titles. Output (schema-constrained): a rationale of at most 150 words and one plain line per criterion.
2. Post-checks in code: only known criterion IDs appear; pass or fail shown in the UI always comes from the facts, never from LLM text; an automated test asserts a criterion line never states the opposite verdict.
3. Invalid output, failure or over-budget: generate a template rationale from the facts and log the fallback.

**Block 2.4 Submission API and verification workflow (Dev 1 with Dev 2)**

1. POST submission (GitHub PR URL, deployed URL, optional file upload) is allowed only when the milestone is FUNDED (or SUBMITTED on retry) and attempts remain; state moves to SUBMITTED, then VERIFYING.
2. Verification runs as a worker job, not inside the request; the UI polls progress.
3. Persist the submission row (facts, score, rationale, route), update state, write audit at each step.

**Block 2.5 Payouts, MCP adapter and release path (Dev 1 and Dev 2)**

1. Payouts client: create batch, get item status. Set `sender_batch_id` from milestone ID plus attempt, which blocks duplicates on PayPal's side as well.
2. MCP / Agent Toolkit adapter implementing `PayPalGateway`: maps our actions to the tools recorded in ADR-002, logs tool name and arguments, and is selected by `PAYPAL_EXEC_MODE`. If D-1 triggered the fallback, implement release through Orders plus Invoicing behind the same interface.
3. The Verifier emits a `release_milestone_payout` Proposal. Policy checks: within the per-release limit; above the auto-action limit gives needs\_approval; recipient verified; milestone funded; ledger balance sufficient; no open dispute; no earlier release.
4. Reconciliation gate hook: confirm the funding capture exists in PayPal records (GET capture) before releasing. A mismatch stops and flags.
5. The executor calls the payout with the idempotency key. The payout-item-succeeded webhook (confirm the exact name) moves the milestone to RELEASED, writes the ledger entry, writes the reputation event (stub until Phase 4) and audits.
6. Failures: API error retries, then ACTION\_FAILED and escalation; denied payout item flags for a human; a duplicate webhook has exactly one effect.
7. Over-limit path: needs\_approval creates an approval task; a hard deny shows in the UI with the failed rule.

**Block 2.6 Client review flow (Dev 1 API, Dev 4 UI)**

1. IN\_REVIEW screen: fact table, rationale, manual-review checkboxes, approve or reject with a reason.
2. Approve goes through the release path above; reject returns to the freelancer (attempts left) or DISPUTED at the limit; everything audited.

**Block 2.7 Refund path (Dev 1)**

1. `refund_milestone` Proposal for cancellation or a dispute resolved for the client. Policy checks: no payout already made for that milestone, amount at most the remaining held balance.
2. The executor calls the capture refund; the capture-refunded webhook moves the milestone to REFUNDED and writes the ledger entry.

**Block 2.8 Escrow timers (Dev 1)**

1. Scheduler jobs from `scheduled_actions`: submission-deadline reminders, stale IN\_REVIEW reminders to the client, stale-escrow reminders to both parties.
2. Decision D-5 (ADR-007) on auto-release for a silent client. Recommended: after the timer, raise an auto-release Proposal only for IN\_REVIEW milestones scoring at least 0.75, still subject to every policy rule. Confirm with the team before building.

**Block 2.9 AG Grid ledger v1 (Dev 4)**

1. Unified rows from `/ledger`: type, subject, parties, amount, status chip, next action, updated.
2. Filters by status, type and amount range; sorting; a saved default view.
3. Master-detail (or the drawer fallback per ADR-005): submission facts, criteria results, rationale, PayPal IDs, audit timeline.
4. Row click opens the audit trail; CSV export.
5. Live updates: poll `/ledger?since=<cursor>` every 3 seconds, apply row transactions and flash changed rows.

**Block 2.10 Submission and review UI (Dev 4)**

1. Freelancer: evidence form (PR URL, deployed URL, file), attempts remaining, live verification progress with per-criterion pass or fail from facts.
2. Client: review screen and a release confirmation showing the PayPal payout ID.
3. Policy banner: when a deny occurs, show 'Blocked by policy' with the rule name and full check list; an admin page changes a limit live.

**Block 2.11 Demo fixtures (Dev 3 with Dev 2)**

1. Create a public fixture GitHub repo with a merged PR and passing CI, plus a branch with failing CI.
2. Serve fixture sites from the app: `/fixtures/site-a` (passes), `/fixtures/site-b` (missing text), and a flaky route that fails every third request to exercise the majority vote.
3. Provide sample PDFs and documents for the file inspector; label each of the 10+ seeded submissions as pass, fail or borderline in the answer key.

**Block 2.12 Verifier evaluation (Dev 2)**

1. Run the labelled submissions and report agreement with the labels: every clear case correct, borderline cases routed to IN\_REVIEW.
2. Run the rationale-versus-facts consistency test.
3. Show that a duplicate submission event and a duplicate webhook each produce exactly one payout.

**Block 2.13 Postman additions (Dev 1)**

1. Add payouts and webhook-simulation requests with test assertions.

**Integration Gate IG-2 (6 Nov night, hosted URL)**

1. A clear-pass submission scores 1.00, a proposal is raised, policy allows, the reconciliation gate passes, the payout goes out via MCP or REST, the webhook arrives, the milestone is RELEASED, the ledger row updates live and the audit trail is complete.
2. A borderline submission lands in IN\_REVIEW with a rationale; the client approves; the payout follows.
3. A failing submission twice ends in DISPUTED after the attempt limit.
4. An over-limit release is blocked with the rule named; the admin raises the limit; the needs\_approval path completes.
5. Replaying a payout webhook gives one payout; an injected payout failure ends in ACTION\_FAILED with escalation.
6. One refund is demonstrated.

**Exit criteria (Phase 2)**

- IG-2 passes twice in a row on the hosted environment.
- Verifier agrees with the planted labels on all clear cases; the rationale never contradicts the fact table.
- No duplicate payouts under any replay test; every transition has an audit row.
- The ledger shows live updates and the audit drawer works.
- Postman collection v1 runs green via Newman against the hosted URL.

## 6.7 Phase 3: Recovery Engine (3 Nov to 7 Nov)

**Owners:** Dev 3 (lead), Dev 1 (PayPal subscription, invoicing and link calls, scheduler infrastructure), Dev 2 (policy rules, LLM calls), Dev 4 (recovery UI). **Goal:** failed subscriptions and overdue invoices are detected, reconciled, diagnosed, acted on under policy limits, and stopped at the right time, with the headline number and the agent-versus-baseline comparison produced from the 150+ seeded cases. Dev 3 starts this phase before the escrow path is finished: blocks 3.1 to 3.5 need only Python, the seeded data and FakePayPal.

**Block 3.1 Reconciliation core (Dev 3)**

1. Normalise the three sources (PayPal transactions, merchant sales CSV, bank CSV) into `reconciliation_records`: source, external ID, amount, currency, date, customer reference.
2. Matching pipeline in three passes: exact ID; amount plus date window (default 3 days) plus customer; fuzzy match with rapidfuzz on name and reference.
3. Tolerances for fee deductions, currency rounding gaps such as 0.03, partial refunds, duplicates and timing offsets between PayPal and the bank.
4. Confidence score to tier: auto-match, human review, exception. Thresholds sit in policy\_config.
5. Expose `check_already_paid(case)` (read tool): auto-match closes the case as PAID\_ELSEWHERE with zero contact; human-review tier holds the case, creates a review task and sends nothing; no match continues.
6. Metrics against the hidden answer key: match rate, precision and recall; an exception list with a reason per record.
7. Tests built from every planted trap; the bank-transfer payer must never be contacted.

**Block 3.2 Case model and state machine (Dev 3)**

1. Implement the case state machine from the project document: OPEN, RECONCILING, DIAGNOSED, ACTION\_PENDING\_APPROVAL (if large), ACTION\_SENT, AWAITING\_RESULT, then RECOVERED, HALTED, UNRECOVERED or PAID\_ELSEWHERE.
2. A single transition function with an allowed-transitions table; terminal states cannot change except through an explicit human-reopen endpoint, which is audited.
3. Case creation from three triggers: failed subscription payment event, overdue invoice scan, and internal funding-failure event. Dedupe by event ID.
4. Tests: a property test over random event orderings proves no terminal case ever moves.

**Block 3.3 Diagnosis (Dev 3)**

1. Rule table (YAML in `recovery/config`) mapping failure code and invoice status to: insufficient funds, expired card, temporary hold, forgot to pay, large overdue invoice, suspicious hard decline.
2. Only free-text customer replies (for example I'll pay Friday) use LLM call 1 with schema-constrained output {diagnosis, promised\_date}; the call is budgeted and falls back to a log-only note.
3. Tests per diagnosis; reply-parsing tests including injection strings inside replies.

**Block 3.4 Prioritisation and daily queue (Dev 3)**

1. priority = amount times recovery likelihood from a rule table keyed by diagnosis and history.
2. `/cases?sort=priority` and a daily action queue respecting the daily action cap.

**Block 3.5 Strategy, templates and timing (Dev 3)**

1. Diagnosis-to-action table exactly as in the agent specification (insufficient funds: payday-aligned retry plus short reminder; expired card: payment-method update request; temporary hold: wait, retry once; forgot to pay: friendly reminder, then payment link; large overdue invoice: split or Pay Later offer; promise to pay: log, remind the day before; suspicious hard decline: no retry, escalate).
2. Escalation ladder per diagnosis (for example reminder, then payment link, then split offer, then human).
3. Templates by diagnosis and language (start with English and Hindi, add two more only if time allows) in Jinja2 with autoescape; every email carries an opt-out line.
4. Timing: payday alignment (config days), customer-timezone quiet hours with zoneinfo, 48-hour minimum gap.
5. LLM call 2 is optional and used only when no template fits.

**Block 3.6 Tool layer and executor wiring (Dev 3 with Dev 1)**

1. Tool registry with the spec's tools: get\_case, get\_customer\_history, check\_already\_paid (reads); schedule\_retry, send\_invoice\_reminder, create\_payment\_link, offer\_split\_payment, log\_promise\_to\_pay (gated writes); escalate\_to\_human (ungated).
2. Dev 1 implements the PayPal side behind the gateway: Subscriptions (retry or capture outstanding balance), Invoicing (create, send, remind, record payment), payment links (an Orders v2 order whose approval URL goes in the email), Pay Later split offer (payment-link page showing the Pay Later button via JS SDK v6).
3. Email channel: `EMAIL_MODE=outbox` stores messages in `outbox_messages` and shows them in the UI (default for the demo); SMTP or a free provider is optional and gated by the channel allowlist.
4. Every write tool call is a Proposal; the executor attaches idempotency keys such as case ID plus ladder step.

**Block 3.7 Recovery agent loop (Dev 3)**

1. `process_case(case_id, trigger)` implements the seven steps from the specification: create or load the case; Gate 1 already-paid check; diagnose; prioritise; select strategy and timing; propose, policy check, execute; observe and stop check.
2. After each action the case waits for the webhook or simulator result, then evaluates the hard stops: payment received gives RECOVERED; dispute opened gives HALTED with zero further contacts; opt-out gives HALTED; contact cap of 4 gives UNRECOVERED with reason; paid elsewhere gives PAID\_ELSEWHERE.
3. Promise-to-pay: log the date, schedule a reminder the day before; if missed, resume the ladder at the next step.
4. Amounts above the auto-action limit move to ACTION\_PENDING\_APPROVAL and create an approval task.
5. LLM budget: at most 2 calls per case; counters in `llm_usage`; the share of cases handled with no LLM call is computed for the metrics.
6. Failure handling: duplicate webhook processed once; PayPal error retries then ACTION\_FAILED and escalation; policy block is logged and escalated, never bypassed; amount mismatch on retry stops and flags.

**Block 3.8 Scheduler (Dev 1 infrastructure, Dev 3 jobs)**

1. APScheduler runs inside the web process, but the source of truth is the `scheduled_actions` table (due\_at, status, payload), so restarts and free-tier sleeps lose nothing.
2. `/internal/tick` (token protected) processes everything due; it is called by the in-process loop every 30 seconds and by the keep-warm workflow every 5 minutes.
3. Jobs: ladder steps, payday-aligned retries, promise-to-pay reminders, overdue-invoice scan, escrow timers, scheduled evaluation runs.
4. Demo time travel: an admin endpoint advances the fake Clock so a multi-day ladder plays out in seconds on camera. It exists only when `DEMO_MODE` is on.

**Block 3.9 Overdue invoice scanner (Dev 3 with Dev 1)**

1. Scan invoices (database rows for the 60 seeded cases plus a handful of real sandbox invoices) and open a case for each overdue one.
2. The invoice-paid webhook (confirm exact name) closes the case as RECOVERED and adds to the headline number; an invoice cancelled event closes it as UNRECOVERED with reason.

**Block 3.10 Frontend: recovery views (Dev 4)**

1. Cases grid (AG Grid): status, diagnosis, priority, contacts used, next step, amount; filters by status and intervention.
2. Case detail with a timeline of attempts, each with its policy checks and audit link.
3. Unrecovered and halted view with a reason on every row.
4. Headline banner: Recovered $X of $Y at risk across N cases; shown first on the dashboard.
5. Approval queue for large actions; reconciliation view with tabs for matched, review and exception, showing confidence tiers.
6. Demo control panel: inject a failure event, run the simulator, advance the clock, reset the demo.

**Block 3.11 Baseline and evaluation harness (Dev 3)**

1. The same runner with `strategy=baseline` (retry three times, same email to everyone) and `strategy=agent`, on identical seeded cases and the same random seed.
2. Metrics (project document, section 14): recovered over at-risk and recovery rate; recovery by intervention type; contacts per recovery; customers wrongly contacted (already paid); disputes avoided; reconciliation precision and recall; unsafe actions blocked by the guard; share of cases with no LLM call; estimated cost per recovered dollar (labelled as an estimate); unrecovered cases with reasons.
3. Store each run in `eval_runs`; expose `/eval/latest`; `make eval` prints the comparison table; a UI page renders it.

**Integration Gate IG-3 (7 Nov night, hosted URL)**

1. Run the 150+ seeded cases through the agent on the hosted environment; the headline number appears.
2. Zero contacts to any already-paid customer (bank-transfer traps) while the baseline contacts them.
3. Inject a dispute mid-ladder: the case halts and no further action is proposed or executed.
4. No case exceeds 4 contacts and no two contacts are under 48 hours apart (checked by query).
5. Agent-versus-baseline table generated from the same cases.

**Exit criteria (Phase 3)**

- IG-3 passes on the hosted environment.
- Reconciliation precision and recall computed against the answer key and shown in the UI.
- Terminal-state property tests and contact-cap tests green.
- Every recovery write passes through policy and executor; audit rows exist for every ladder step.
- Share of cases handled with no LLM call is reported.

## 6.8 Phase 4: Trust Layer and Whole-System Integration (6 Nov to 8 Nov)

**Owners:** Dev 2 (Dispute agent, Q&A), Dev 1 (reputation, disputes webhook, hardening), Dev 3 (bridges, evaluation), Dev 4 (remaining views). **Goal:** the two engines behave as one system. A dispute halts everything, reputation is shared, funding failures feed Recovery, and the whole thing is explainable and searchable. Feature freeze at the end of 8 Nov.

**Block 4.1 Dispute agent (Dev 2)**

1. Trigger: dispute webhooks (confirm exact event names) and simulated dispute events.
2. Deterministic halt first, before any LLM call: the Recovery case moves to HALTED, pending scheduled actions for that subject are cancelled, and the matching escrow milestone is frozen through `freeze_milestone` (ungated, since it only makes things safer). All of it is audited.
3. Evidence pack assembler (code): submission history, verifier facts and rationale, contact history, ledger entries, timestamps, audit references, stored in `evidence_packs`.
4. At most one LLM call to write a short summary; template fallback if it fails.
5. The agent proposes a response (accept or contest) and a human decides in the UI. Submitting the response to PayPal is a stretch item, gated and executed only through the executor.

**Block 4.2 Funding failure feeds Recovery (Dev 3 with Dev 1)**

1. Consume the `funding.failed` and instalment-failed events from Phase 1 and open a case of type escrow\_funding.
2. The same ladder runs; on RECOVERED the project funding state resumes, on UNRECOVERED the project is flagged for the freelancer.

**Block 4.3 Un-escrowed invoices feed Recovery (Dev 3)**

1. A freelancer's overdue invoice created outside escrow becomes a Recovery case.
2. The outreach template and the case view carry an escrow suggestion for the next project, with a link that pre-fills the intake form.

**Block 4.4 Reconciliation for escrow (Dev 3 with Dev 1)**

1. Pre-release check: the funding capture exists in PayPal records for the full amount. Post-release check: the payout appears in PayPal transaction data.
2. Escrow rows appear in the reconciliation view with their match status; mismatches go to the exception list with a reason.

**Block 4.5 Reputation ledger (Dev 1)**

1. A simple transparent formula: start at 50, add points for on-time release, on-time payment and recovery; subtract for dispute lost and missed deadline; weights live in policy\_config; clamp to 0 to 100.
2. Every change is a `reputation_events` row linked to its audit entry; the score is recomputed from events, so replays are idempotent.
3. `GET /reputation/{subject}` returns the score and the event list; replace the Phase 2 stub in the release handler.
4. Tests: a replay of the same events gives the same score; each event type changes the score by its configured weight.

**Block 4.6 Cited read-only Q&A (Dev 2 backend, Dev 4 UI)**

1. Retrieval: Postgres full-text search over audit rows plus case and milestone summaries; return the top records with their IDs.
2. One LLM call (larger model allowed, daily cap enforced by policy) answers only from the retrieved records and returns citation IDs.
3. Post-check in code: every cited ID must be in the retrieved set; otherwise show the answer as uncited or fall back to a list of the records.
4. Read-only: the endpoint has no tools and refuses requests to change anything. Audit text is passed as delimited data, never as instructions.
5. UI: chat panel with clickable citations that open the audit row; sample questions such as Why wasn't case 42 recovered? and Why was milestone 2 held?
6. Scope cut: a basic cited answer is enough; drop streaming and follow-ups first.

**Block 4.7 Policy admin and demo controls (Dev 4 with Dev 1)**

1. Admin page lists policy\_config with edit, shows the policy-block log and the pending approval tasks.
2. Demo controls (inject failure, advance clock, reset demo) are visible only when `DEMO_MODE` is on and the admin role is selected.

**Block 4.8 Cross-engine scenario suite (all four)** Automate these as pytest scenarios (FakePayPal) and as a Postman or Newman run against the hosted URL:

1. S1 happy path: fund, submit, verify, auto-release, ledger and reputation updated.
2. S2 borderline: IN\_REVIEW, client approves, release.
3. S3 over-limit release blocked by the mandate guard, then approved after a limit change.
4. S4 duplicate webhook: one ledger entry and one payout.
5. S5 dispute mid-ladder: Recovery case HALTED and escrow milestone frozen.
6. S6 already-paid customer: PAID\_ELSEWHERE with zero contacts.
7. S7 funding failure: Recovery case opens, ladder runs, project funding resumes on recovery.
8. S8 payout API failure: ACTION\_FAILED, escalation task created, no duplicate on retry.

**Block 4.9 Dashboard headline and metrics (Dev 4 with Dev 3)**

1. First screen: Recovered $X of $Y at risk across N cases, then escrow released, disputes avoided, unsafe actions blocked, and reputation highlights.
2. A small honesty panel lists the simulator assumptions and the limits from the project document, section 18.

**Integration Gate IG-4 (8 Nov night, hosted URL)**

1. Run S1 to S8 on the hosted environment in one sitting.
2. Open a dispute on a milestone that also has a Recovery case: both halt, the evidence pack appears, a human decides.
3. Ask the Q&A two sample questions; citations resolve to real rows.
4. Reputation score changes after a release and after a recovery, with each change linked to its audit entry.
5. Feature freeze declared: from here only bug fixes, polish and deliverables.

**Exit criteria (Phase 4)**

- S1 to S8 pass on the hosted environment.
- A dispute halts Recovery and freezes the milestone in the same transaction, proven by the audit trail.
- Q&A citations are always verifiable; no write path exists in Q&A.
- Reputation score is reproducible from events.
- Remaining work list contains only bugs, polish and sponsor deliverables.

## 6.9 Phase 5: Hardening, Polish and Sponsor Deliverables (9 Nov)

**Owners:** all four. Only bug fixes and deliverables; no new features. **Goal:** a stable, secure, demo-ready product with every sponsor and submission deliverable prepared.

**Block 5.1 Bug bash and triage (all, morning)**

1. Each developer walks the full demo script as a judge would, on the hosted URL, in a fresh browser profile.
2. Log every defect on the board with severity: P0 breaks the demo path, P1 visible glitch, P2 cosmetic. Fix P0 and P1 first; P2 only if time remains.

**Block 5.2 UI polish (Dev 4)**

1. Loading, empty and error states on every screen; consistent status chips and copy; keyboard focus and colour contrast; layouts checked at laptop and phone widths.
2. Remove developer-only UI; keep the honesty panel and the demo control panel (behind admin role and DEMO\_MODE).
3. Prepare screenshots for the README and Devpost gallery.

**Block 5.3 Seed data and demo reset (Dev 3)**

1. `make demo-reset` and the admin Reset button truncate and reseed deterministically in under 30 seconds.
2. Seeded states: one project at each escrow stage, the 150+ recovery cases ready to run, a pre-computed evaluation run plus the ability to rerun it live.
3. Final numbers frozen for the video: recovered $X of $Y, baseline comparison, verifier agreement, reconciliation precision and recall.

**Block 5.4 Security and robustness pass (Dev 1 and Dev 2)**

1. Scan the repo and history for secrets; rotate any sandbox key that was ever committed.
2. Production flags: `/sim/events`, clock control and reset exist only with `DEMO_MODE` and a token; webhook signature verification confirmed on real deliveries.
3. Rate limits and size limits on public endpoints, upload caps, strict CORS (same origin), redacted logs.
4. Re-run the SSRF suite and the prompt-injection tests; dependency audit for the backend and web.
5. Confirm the policy engine and executor cannot be bypassed: the import-boundary check and the unsigned-decision test pass.

**Block 5.5 Postman collection (****Dev 1)**

1. Folders: auth, orders, payouts, invoice and reminder, retry, webhook simulation with automated tests.
2. Environment template with placeholders only; Newman run documented in the README; collection published to a workspace and linked.

**Block 5.6 APIMatic SDK (Dev 1)**

1. Generate a typed PayPal SDK from the OpenAPI spec and use it for a defined subset (for example Orders and Payouts models). Document how it was used in the README and `docs/sponsors.md`.
2. Timebox to 90 minutes; if integration causes friction, keep the SDK for typed models and documentation only.

**Block 5.7 Elastic decision (Dev 1)**

1. Decision D-6 was due 7 Nov: use Elastic only if a free tier covers the judging period. Otherwise state clearly in the README that Postgres full-text search powers audit search.

**Block 5.8 README and Devpost text (Dev 4 lead, all contribute)**

1. README structure: overview, live demo URL and sandbox test credentials, role switcher guide, architecture diagrams (system layers, agent pipeline, sponsor map), features by module, setup (local and Render), environment variables, running tests and the evaluation, Postman usage, sponsor usage table, every AI tool and sponsor tool and what it does, honest limits, license. Keep headings skimmable because judging may include automated analysis.
2. Devpost description: features and functionality, every AI tool and sponsor tool with its role, and what was built during the hackathon.
3. Re-check each target sponsor's Devpost requirements and tick off every extra deliverable.

**Block 5.9 Performance and cold start (Dev 1)**

1. Measure cold start and first-request latency on Render; confirm the keep-warm workflow works; note the database expiry date and plan around it.
2. Pre-warm script run before recording and before submission.

**Exit criteria (Phase 5, IG-5 prep)**

- No open P0 or P1 defects; S1 to S8 still green after fixes.
- Security checklist complete; no secrets in the repo or history.
- Postman collection runs green; SDK documented; README draft complete.
- Demo reset works in under 30 seconds and produces the same state every time.

## 6.10 Phase 6: Deploy, Rehearsal and Video (10 Nov)

**Owners:** Dev 1 (deploy), Dev 4 (video lead), Dev 3 (judge dry-run), Dev 2 (fixes and rehearsal support). **Goal:** a clean production deployment that anyone can open, and a recorded, uploaded video under 3 minutes.

**Block 6.1 Release candidate and clean deploy (Dev 1)**

1. Code freeze at noon IST: tag `v1.0-rc`; only P0 fixes with two approvals after this point.
2. Prove the blueprint is reproducible: deploy from `render.yaml` into a fresh environment with a fresh Postgres, set environment variables, run migrations.
3. Register the production webhook URL in the PayPal dashboard and confirm a real signed delivery; confirm the sandbox credentials in the README work.
4. Run `make demo-reset` against production, then the Newman smoke run and S1 to S8.
5. Start the keep-warm schedule and record the production URL in the README.

**Block 6.2 Judge dry-run (Dev 3, with Dev 2)**

1. Someone who did not build the page follows only the README in a private browser window and records time to first success and every point of confusion.
2. Fix documentation gaps immediately; fix product issues only if P0.

**Block 6.3 Video script and recording (Dev 4 lead, all review)**

1. Follow the project document's outline: 0:00 to 0:20 problem with one freelancer story; 0:20 to 1:00 describe a job, plan appears, client funds via PayPal Checkout; 1:00 to 1:50 submit work, verifier scores, payout fires via MCP, AG Grid updates live; 1:50 to 2:20 mandate guard refuses an over-limit release and a dispute halts the case with its evidence pack; 2:20 to 2:45 recovery headline versus baseline and the already-paid customer with zero contact; 2:45 to 3:00 reputation, stack and sponsors, impact line.
2. Write a shot list with exact click paths and pre-seeded states; rehearse twice before recording. Aim for 2:50 total.
3. Record at 1080p on the target device (the browser), voice-over or captions, no copyrighted music, no third-party trademarks beyond what the product screens unavoidably show.
4. Upload to YouTube as public; open the link in a logged-out window to confirm playback and length under 3 minutes.
5. Cut the Q&A demo from the video if time runs over; keep it in the live app.

**Block 6.4 Contingency (Dev 1)**

1. If production misbehaves after noon, roll back to the last good deploy and record from that; if the PayPal sandbox is down, record using the verified Postman and simulator evidence and note it in the description.

**Exit criteria (IG-5)**

- Production URL passes the Newman smoke run and S1 to S8 from a clean state.
- The judge dry-run succeeds from the README alone.
- Video is public on YouTube, under 3 minutes, plays logged out.
- No uncommitted changes; the deployed commit equals the tagged release candidate.

## 6.11 Phase 7: Submission (11 Nov, with 12 Nov morning as emergency buffer only)

**Owners:** all four, together on one call; Dev 4 types the form, Dev 1 verifies the technical fields. **Goal:** submitted and verified on Devpost with buffer to spare.

**Block 7.1 Devpost submission (all)**

1. Fill every field: description (every AI and sponsor tool named with its role), repo link, hosted URL, sandbox credentials, video link, team members, built-with tags, sponsor prize selections.
2. Confirm the repository is public with the license visible in About and no secrets; confirm the README renders correctly.
3. Submit by evening IST on 11 Nov. Do not wait for the final hour.

**Block 7.2 Post-submission verification (all)**

1. Check that the submission shows as submitted, not draft; open each link from a logged-out window and from a phone.
2. Clone the repository into a fresh folder and follow the README setup once.
3. Confirm webhooks still arrive and the keep-warm job runs.

**Block 7.3 Judging-period watch (Dev 1)**

1. No deploys except a team-approved hotfix. Check health daily; note Render and database expiry dates and extend or migrate before judging ends.

**Exit criteria (Phase 7)**

- Devpost shows a completed submission with all required items (repo, working demo, video, description, README).
- Every link works logged out; the demo environment is warm and reset to the seeded state.

## 6.12 Scope-cut order and schedule triggers

**Never cut:** the escrow path (fund, verify, release), the mandate guard, the dispute halt, the audit log, the AG Grid ledger, the hosted demo and the video.

**Cut in this order when behind:** (1) Bryntum, Zapier and Elastic (Postgres search stays); (2) Q&A beyond one basic cited answer; (3) subscription recovery depth (keep invoice chasing and the reconciliation gate); (4) reputation sophistication (keep the simple transparent formula). Cut scope, not time.

| Checkpoint | If missed | Action |
| --- | --- | --- |
| IG-0 by 1 Nov 18:00 | Contracts or sandbox facts unsettled | Dev 3 and Dev 4 stop feature work and unblock Dev 1; the gate may slip by 12 hours at most |
| IG-1 by 3 Nov midnight | Plan-to-fund unstable | Dev 3 helps Dev 1 and Dev 2 until it passes; templates limited to English and Hindi; Postman v0 deferred |
| IG-2 by 7 Nov noon | Escrow path unstable | Freeze Recovery at invoice chasing plus reconciliation gate; Q&A basic only; master-detail becomes a drawer |
| IG-3 by 8 Nov noon | Recovery loop unstable | Run the baseline comparison on a subset; hide unfinished recovery views |
| IG-4 by 8 Nov night | Trust layer incomplete | Feature freeze regardless; ship what passes its scenarios; remove unfinished screens from navigation |
| Video not recorded by 10 Nov 18:00 | Rehearsal overran | Re-record a shorter cut from the verified path; drop the Q&A and reputation beats first |

## 6.13 Risk register

| Risk | Early signal | Mitigation | Owner |
| --- | --- | --- | --- |
| Payouts not enabled on sandbox | D-1 check fails on day one | Release through Orders plus Invoicing behind the same gateway interface | Dev 1 |
| MCP / Agent Toolkit lacks a needed tool | ADR-002 inventory | REST gateway behind the same interface for that action; state accurately in the README which actions use MCP | Dev 1 |
| Free LLM tier rate-limited or poor JSON | 429s or invalid output in tests | Budgets, schema retry once, rule and template fallbacks, FakeLLM in CI, cheap model for routine work | Dev 2 |
| Render sleep or database expiry | Cold start over 30 seconds; expiry date near judging | Keep-warm workflow, pre-warm script, Oracle VM fallback, note expiry dates | Dev 1 |
| Webhooks missing or late | Order paid but milestone not FUNDED | Replay tool, periodic reconcile job polling order and capture status, simulated events for demo | Dev 1 |
| Verifier flakiness (GitHub limits, flaky URL) | VERIFY\_DELAYED spikes | Authenticated read-only token, majority vote, fixture repo and sites, never a fail from an outage | Dev 2 |
| Schema churn breaks lanes | Frequent migration conflicts | Contract-change protocol, single schema owner, generated clients | Dev 1 |
| AG Grid master-detail licence | D-3 unresolved | Community grid with a drawer detail panel | Dev 4 |
| Prompt injection through evidence, job text or replies | Odd instructions in test data | Delimited data fields, schema-only outputs, policy gate on every write | Dev 2 |
| Demo state corrupted before recording | Unexpected rows or states | Deterministic seeds, one-click reset, rehearsal after every deploy | Dev 3 |
| A developer unavailable for a day | Standup flag | Backups in 1.2; Tech Lead re-balances the board the same day | Dev 1 |
| Scope inflation | New cards appearing after 6 Nov | Feature freeze rules and cut order above | Dev 1 |

## 6.14 Decision log

| ID | Decision | Owner | Due | Default if undecided |
| --- | --- | --- | --- | --- |
| D-1 | Is Payouts available on the sandbox business account? | Dev 1 | 31 Oct | Orders plus Invoicing release path |
| D-2 | MCP or REST execution per action | Dev 1 | 2 Nov | REST, with MCP for the actions it supports |
| D-3 | AG Grid edition and licence | Dev 4 | 1 Nov | Community grid with drawer detail |
| D-4 | Free-tier LLM provider | Dev 2 | 31 Oct | The provider that passes the rate-limit test |
| D-5 | Auto-release timer semantics | Dev 1 and Dev 2 | 3 Nov | Reminders only |
| D-6 | Use Elastic or not | Dev 1 | 7 Nov | Postgres full-text search |
| D-7 | Sponsor prize target | All | 1 Nov | AG Grid first, Render fallback (per project document) |
| D-8 | Final project name | All | 1 Nov | ProofPay |
| D-9 | Hosting: Render or Oracle VM | Dev 1 | 1 Nov | Render |
| D-10 | Languages for outreach templates | Dev 3 | 3 Nov | English and Hindi |

## 6.15 Definition of done and quality bars

**Every task:** merged to main with tests, audit rows for every state change, works on the hosted environment, no secrets, board card closed.

**Scoping agent done when:** the golden set of 10 job descriptions passes every validator; property tests show edits never produce plans whose amounts do not sum; a plan cannot be funded without both approvals and a matching plan\_hash.

**Verifier done when:** seeded submissions (clear pass, clear fail, borderline) route as labelled; the rationale never contradicts the fact table; a duplicate event or webhook produces exactly one payout; an over-limit release is blocked by the guard.

**Recovery agent done when:** over 150 seeded cases produce zero contacts to already-paid customers; a dispute mid-ladder halts the case with no further action; no case exceeds 4 contacts or has two contacts under 48 hours apart; the no-LLM share is reported; the agent-versus-baseline table is produced from identical cases.

**Dispute agent done when:** a dispute event halts the Recovery case and freezes the milestone before any LLM call, and the evidence pack contains submission history, verifier rationale, contact history and timestamps.

**Phase done when:** its integration gate script passes on the hosted environment and its exit criteria are ticked on the board.

**Release done when:** the production URL passes the smoke run from a clean state, the video is public, and the Devpost submission shows as submitted.
