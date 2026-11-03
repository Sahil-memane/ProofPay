# ADR-005: Policy Engine as Gatekeeper for All PayPal Actions

**Status:** Accepted  
**Date:** 2026-11-03  
**Deciders:** Dev 1 (Tech Lead)

## Context

PayPal actions (payout, refund, order creation) must be guarded against: duplicate releases, releases above configured thresholds, releases without sufficient ledger balance, releases when a dispute is open, and releases before both parties have approved.

## Decision

Every PayPal action goes through `backend/app/policy/engine.evaluate(proposal)` before the executor is called. The engine runs all registered rules for the action type and returns a `PolicyDecision` with verdict: `ALLOW | DENY | NEEDS_APPROVAL`.

- `DENY` is final — never retried with different wording.
- `NEEDS_APPROVAL` creates an approval task; a human approves via `POST /submission-approvals/{id}/decide`.
- `ALLOW` proceeds directly to the executor.

All decisions are written to the audit log with every check result listed.

## Consequences

- **Positive:** Policy is a central chokepoint — adding a new rule protects all action types.
- **Positive:** Rules are pure functions — trivially unit-testable.
- **Positive:** Hackathon demo: change `auto_action_limit` via admin endpoint live on camera.
- **Negative:** Every action incurs policy evaluation overhead (milliseconds; acceptable).

