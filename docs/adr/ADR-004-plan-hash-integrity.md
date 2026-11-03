# ADR-004: Plan Hash Integrity Guard

**Status:** Accepted  
**Date:** 2026-11-03  
**Deciders:** Dev 1 (Tech Lead)

## Context

The escrow milestone plan is agreed between client and freelancer. We must prevent a party from quietly modifying the plan between agreement and funding, which would change what the escrow covers.

## Decision

When both parties approve the plan, a SHA-256 `plan_hash` is computed over the canonical JSON representation of all milestones (sorted by `sequence`, with amounts rounded to 2dp). The hash is stored on the project.

The `POST /projects/{id}/fund` endpoint requires the caller to provide `plan_hash` in the request body, and rejects (403) any request where the submitted hash does not match the stored one.

If a milestone is edited after approval, all approvals are reset and `plan_hash` is cleared.

## Consequences

- **Positive:** Tamper-evident. Any mid-flight change is detectable.
- **Positive:** Hash is visible in the audit log, providing legal evidence.
- **Negative:** Clients must re-read and re-submit the hash after any edit — extra UX step.
- **Implementation:** `backend/app/escrow/plan_hash.py` → `compute_plan_hash(milestones)`.
