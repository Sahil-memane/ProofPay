# ADR-002: Webhook as Source of Truth for State Transitions

**Status:** Accepted  
**Date:** 2026-11-03  
**Deciders:** Dev 1 (Tech Lead)

## Context

PayPal payment actions (capture, payout, refund) are asynchronous. A successful API call does not mean the money has moved — it means the request was accepted. State must only advance when PayPal confirms via webhook.

## Decision

Milestone and project state transitions are **only** driven by inbound webhook events processed by the ingestion worker. The API endpoints (`/fund`, `/capture`, `/submit`) are optimistic — they call PayPal and return immediately, but do NOT advance milestone/project state. State advances when `capture_completed`, `payout_item_succeeded`, or `capture_refunded` webhooks are processed.

Idempotency key convention: `sender_batch_id = f"{milestone_id}:{attempt}"`. The `payout_events.handle_succeeded` handler splits on `:` to recover `milestone_id`.

## Consequences

- **Positive:** Correct even on network partitions, duplicate deliveries, and retry storms.
- **Positive:** FakePayPal's `emit_webhook()` exercises the exact same path as real PayPal.
- **Negative:** UI must poll `/milestones/{id}/submission` (or use SSE) to show real state.
- **Rule:** Never set `milestone.state = "RELEASED"` in the API layer or executor directly. The webhook handler is the only writer.
