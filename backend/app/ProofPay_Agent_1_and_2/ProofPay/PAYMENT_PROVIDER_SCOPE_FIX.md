# Agent 1 — Payment Provider Clarification Fix

## Policy
Payment provider selection is not a prerequisite for Agent 1. Agent 1 scopes the payment-integration deliverable without forcing a Stripe/PayPal/Square decision.

## Changes
- Removed `payment_provider` from deterministic mandatory clarification requirements.
- `receive_project` clears stale `payment_provider` unresolved flags and records `NOT_REQUIRED_FOR_SCOPING` when no provider was supplied.
- Gemini clarification questions that ask the client to select a payment provider, gateway, or processor are filtered out.
- Updated clarity, generation, and repair prompts to require provider-neutral wording when no provider was explicitly named.
- Validation still rejects a provider-specific milestone if the client did not name that provider; it does not reject generic payment integration.
- Removed `payment_provider` from the project-level unresolved-configuration blockers used by plan validation, repair, fallback, and human-edit validation.
- Updated regression tests for provider-optional scoping and stale provider flags.

## Expected behaviour
For a project brief containing “shopping cart and payment integration” without naming a provider, Agent 1 should proceed with a provider-neutral milestone such as “Payment gateway integration” and objective acceptance checks. It must not ask “Which payment provider do you prefer?”

If the client explicitly names a provider in the original scope, that named provider may be reflected in the milestones. If Gemini invents a provider that the client did not specify, deterministic validation flags it for repair rather than silently accepting it.

## Verification
- Python `compileall` passed for the complete project and tests.
- Full `pytest` collection could not run in the packaging environment because `langgraph` is not installed there (`ModuleNotFoundError: langgraph`). Install the project's `requirements.txt` in the user's environment and run `python -m pytest -q` for the full suite.
