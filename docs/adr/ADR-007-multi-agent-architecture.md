# ADR-007: Multi-Agent Architecture (Scoping, Verifier, Recovery)

**Status:** Accepted  
**Date:** 2026-11-03  
**Deciders:** Dev 1 (Tech Lead), Dev 2 (Agent Engineer), Dev 3 (Recovery Engineer)

## Context

ProofPay has three distinct AI-agent-powered workflows that have different authors, different LLM budgets, and different correctness requirements.

## Decision

Three specialised agents, each in its own package:

| Agent | Package | Owner | LLM Role |
|---|---|---|---|
| Scoping | `agents/scoping/` | Dev 2 | Generate milestone plan from job description |
| Verifier | `agents/verifier/` | Dev 2 | Check evidence against acceptance criteria |
| Recovery | `agents/recovery/` | Dev 3 | Diagnose and strategise payment recovery |

**Integration pattern:**
- Each agent is wrapped in an adapter in `backend/app/agents/<name>/agent.py`.
- Adapters provide a clean Python function interface (`run_scoping()`, `run_verification()`, etc.).
- Adapters handle import-path injection (Dev 2's package lives in `ProofPay_Agent_1_and_2/`).
- Adapters provide a stub fallback if the agent package is unavailable (e.g., `langgraph` not installed).
- All agents communicate results via plain `dict` or dataclass — never via shared mutable state.

**LangGraph:** Dev 2 agents use LangGraph StateGraph with SqliteSaver checkpointing. The graph runs in a `run_in_executor` thread pool call from async FastAPI handlers to avoid blocking the event loop.

## Consequences

- **Positive:** Each agent is independently testable, deployable, and replaceable.
- **Positive:** Stub fallbacks mean the API works even if an agent fails to import.
- **Negative:** Import-path injection (`sys.path.insert`) is a code smell but necessary given the hackathon mono-repo structure. Production would use proper packages.

