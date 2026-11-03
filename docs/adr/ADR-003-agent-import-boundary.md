# ADR-003: Agent Import Boundary

**Status:** Accepted  
**Date:** 2026-11-03  
**Deciders:** Dev 1 (Tech Lead)

## Context

Agents (scoping, verifier, recovery) must remain testable in isolation and must not accidentally trigger real PayPal calls during unit tests or evaluation runs.

## Decision

A strict import boundary is enforced:

- **Agents** (`backend/app/agents/`) MUST NOT import from `paypal/` or `executor/`.
- **Executor** (`backend/app/executor/`) imports from `paypal/` only.
- **Agents** communicate intent via `Proposal` objects (contracts layer).
- **Policy engine** evaluates `Proposal` objects. Only the executor calls PayPal.

CI enforces this via `backend/tests/unit/test_import_linter.py` which uses `importlinter` or AST scanning to detect violations.

## Consequences

- **Positive:** Agents can be tested with no PayPal credentials at all.
- **Positive:** Clear separation: agent = reasoning, executor = side effects.
- **Negative:** Agents cannot directly query PayPal for context (must use a data-fetching service layer that is allowed to be called by agents without triggering payment actions).

