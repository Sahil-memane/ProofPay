# Agent 1 implementation notes

## Scope finalized

Agent 1 is the Scoping Agent only. It collects project requirements, asks scope-related clarifications, generates milestones, validates the plan, collects two independent approvals, and persists/locks the approved plan.

GitHub repository URLs, pull-request numbers, deployment URLs, hosting platforms, and actual execution checks are not mandatory for Agent 1. A new `deliverable_check` criterion captures the agreed deliverable and objective acceptance checks without inventing a file path. A later verification component is responsible for checking submitted work against this contract.

Payment provider selection is not a prerequisite for Agent 1. If payment integration is in scope and no provider was explicitly supplied, the milestone plan remains provider-neutral (for example, “payment gateway integration according to the provider selected during implementation”). Agent 1 must not ask the client to select Stripe, PayPal, Square, or another provider.

## Persistence

Default local connection string:

```env
DATABASE_URL=sqlite:///./data/proofpay.db
```

The application creates the SQLite database under the ProofPay project directory. It persists drafts, participant approval decisions, audit events, approved plans, and `plan.approved` domain events. The approved plan and domain event are written in one database transaction. A locked plan cannot be downgraded or have its milestones replaced.

`langgraph-checkpoint-sqlite` is included in `requirements.txt` so pending graph state (clarifications and approval workflow state) can survive application restarts.

## Approval behaviour

- Client and freelancer approvals are separate actions.
- Each approval is bound to the participant ID declared on the project and to the current SHA-256 plan hash.
- If either participant rejects, both approvals are invalidated and a revision is required.
- A plan is locked only after both approvals match the exact same current plan hash.
- `plan.approved` is persisted atomically with the locked plan; the event-confirmation node checks that both are durably present.

## Run locally

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and add your own `GOOGLE_API_KEY`.
3. Keep the default `DATABASE_URL` line unless you intentionally want another SQLite file.
4. Run `python main.py` for the interactive CLI demo, or `python main.py --serve` for the API.

## Verification performed while preparing this archive

- Python `compileall`: passed for the project source and tests.
- Direct SQLite checks: passed for reopen persistence, audit/event persistence, atomic approved-plan/event write, and locked-plan immutability.
- `deliverable_check` parameter validation: passed.
- Full pytest suite: not executable in the packaging runtime because LangGraph is not installed there and package installation was unavailable (no package-index network access). The archive contains the expanded test suite; run it after installing `requirements.txt` in the user's Python environment.

## Production integration boundary

The current API validates that the submitted participant ID equals the client/freelancer ID on the project. This is not a substitute for authentication. Before public production deployment, the API must receive identity from ProofPay's real authenticated session/JWT layer rather than trusting a user ID in the request body.

The database adapter in this archive is SQLite-only. The default local URL is ready to use; a hosted PostgreSQL URL must not be supplied to this SQLite adapter until a PostgreSQL repository is implemented.
