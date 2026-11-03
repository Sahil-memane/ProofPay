# ProofPay — Agent 1 Scoping + Agent 2 Verification

ProofPay Agent 1 converts a client/freelancer project brief into an agreed, validated, and cryptographically locked milestone plan.

## Agent 1 responsibility

1. Receive project description, client ID, freelancer ID, total budget, currency, and overall deadline.
2. Ask clarification questions only when a missing project requirement materially affects scope. Payment provider selection is optional and deferred to implementation; Agent 1 scopes payment integration in provider-neutral terms when no provider is specified.
3. Generate 2–6 milestones with deliverables, payment amounts, deadlines, and acceptance criteria using Gemini.
4. Validate the plan deterministically in Python.
5. Allow a human edit and deterministic revalidation when needed.
6. Collect independent client and freelancer approvals for the exact same plan hash.
7. Revalidate, persist the approved plan and `plan.approved` event atomically, and lock the plan using SHA-256.

**Not Agent 1 responsibilities:** collecting GitHub repository URLs, deployment URLs, pull request IDs, or checking whether deployed code/files actually pass. Those belong to a later milestone-verification component. Agent 1 defines the deliverable and acceptance contract; it does not claim the deliverable has already passed verification.

## Architecture principle

> The LLM proposes, the policy engine decides, code executes.

Gemini output never bypasses Python validation. The approval lock requires a valid plan, no blocking unresolved fields, both project participants' approval flags, and matching approval hashes.

## Database and persistence

The default setup uses a persistent local SQLite database; no hosted database account is required.

```env
DATABASE_URL=sqlite:///./data/proofpay.db
```

The application creates `data/proofpay.db` automatically. It stores project drafts, approval decisions, locked plans, audit events, domain events, and milestone verification submissions/results. The LangGraph SQLite checkpointer stores pending clarification/approval workflow state in the same database file when `langgraph-checkpoint-sqlite` is installed.

For a future hosted PostgreSQL deployment, replace the SQLite repository adapter with a PostgreSQL implementation and provide a PostgreSQL connection URL. This version intentionally does not pretend that a PostgreSQL URL is configured or supported by the SQLite adapter.

## Setup (Windows PowerShell)

Run commands from the folder containing `main.py`:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and set your Gemini key:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
DATABASE_URL=sqlite:///./data/proofpay.db
```

Do not commit or share `.env`. The `.env.example` contains placeholders only.

## Agent 2 — Milestone Verification Agent

Agent 2 is integrated as a separate LangGraph workflow and API router. Agent 1's existing Scoping graph, approval nodes, SHA-256 locking, and `plan.approved` event flow remain unchanged.

The handoff is event-driven and submission-driven:

1. Agent 1 completes both approvals, locks the plan, and persists `plan.approved`.
2. The workflow waits. Agent 2 does **not** run immediately when the plan is approved.
3. The assigned freelancer submits evidence for a specific locked milestone.
4. Agent 2 loads that milestone's acceptance criteria from the immutable approved plan and verifies supported URL/GitHub/file criteria.
5. Criteria that require human judgment (`deliverable_check`, `manual_review`, or unsupported evidence) remain `review_required`; they are never auto-passed.
6. Python calculates the weighted score and decision. Gemini may explain the deterministic result, but cannot change the score or decision.
7. The verification result and audit event are persisted separately; the locked Agent 1 plan is never modified.

Decision values:

- `RELEASE_PROPOSAL` — all criteria are objectively verified and the score is at least 90%. This is only a proposal; it does not transfer funds.
- `CLIENT_REVIEW_REQUIRED` — human review is needed or the score is below the proposal threshold.
- `RESUBMISSION_REQUIRED` — a must-pass criterion failed.

Agent 2 endpoints:

- `POST /api/v1/verification/projects/{project_id}/milestones/{milestone_id}/submissions` — submit milestone evidence and run verification.
- `GET /api/v1/verification/projects/{project_id}/milestones/{milestone_id}/submissions` — retrieve persisted verification attempts.

Example submission body:

```json
{
  "freelancer_id": "freelancer_001",
  "repository": "owner/project",
  "deployment_url": "https://example.com",
  "evidence_url": "https://example.com/demo",
  "files": {
    "docs/architecture.md": {
      "size_kb": 12,
      "content": "# Architecture\n\n## Data Model\n"
    }
  }
}
```

`GITHUB_TOKEN` is optional and can be added to `.env` to increase GitHub API rate limits or access private repositories. Do not commit the token. URL verification accepts public HTTP/HTTPS destinations only; local/private network targets and redirects are rejected. This local API still requires production authentication/authorization before deployment.

## Run the interactive Agent 1 demo

```powershell
python main.py
```

The CLI demo uses example client/freelancer IDs and performs a demonstration approval flow after showing the generated plan. It is a local demo, not an authenticated production payment flow.

## Run the API

```powershell
python main.py --serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for the API documentation.

Key endpoints:

- `POST /api/v1/scoping/projects` — submit a project.
- `POST /api/v1/scoping/projects/{thread_id}/clarification` — answer pending scope questions.
- `POST /api/v1/scoping/projects/{thread_id}/edit` — submit a deterministic plan edit.
- `POST /api/v1/scoping/projects/{thread_id}/approval` — submit client or freelancer approval.
- `GET /api/v1/scoping/projects/{thread_id}` — read current workflow state.
- `GET /api/v1/scoping/projects/{thread_id}/audit` — read persisted audit history.
- Agent 2 endpoints are listed in the Agent 2 section above.

## Tests

```powershell
pytest tests -v
```

The automated tests mock Gemini for deterministic, no-cost tests. The optional live Gemini test runs only when `GOOGLE_API_KEY` is configured.

## Important production boundary

The current API checks that the supplied `user_id` matches the declared client/freelancer participant ID. A real deployment must connect this to ProofPay's authenticated user/session system; request-body IDs alone are not authentication. No payment gateway is called by Agent 1.
