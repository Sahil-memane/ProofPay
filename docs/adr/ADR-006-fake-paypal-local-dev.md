# ADR-006: FakePayPal for Local Development

**Status:** Accepted  
**Date:** 2026-11-03  
**Deciders:** Dev 1 (Tech Lead)

## Context

Running against the real PayPal sandbox requires internet access, sandbox credentials, and introduces test flakiness from network conditions. Local development loops must be fast and deterministic.

## Decision

`FakePayPal` (in `backend/app/paypal/fake_paypal.py`) is a full in-process simulator:
- Generates realistic PayPal-shaped response dicts (order IDs, payout batch IDs, etc.).
- Calls `emit_webhook()` which inserts a row directly into the `webhook_events` DB table.
- The ingestion worker picks it up and processes it exactly as a real PayPal webhook.
- No HTTP involved. No credentials needed.
- Supports failure injection via env flags (`FAKE_PAYPAL_PAYOUT_FAIL=1`, etc.).

`.env` always has `PAYPAL_EXEC_MODE=fake`. Only Render dashboard has `rest` for gate runs and the demo video.

## Consequences

- **Positive:** Full end-to-end flow (create order → capture → payout → RELEASED) runnable with `uvicorn` and Postgres locally in < 5 seconds.
- **Positive:** No sandbox credential management during development.
- **Negative:** FakePayPal response shapes must be kept aligned with PayPal API updates.
- **Rule:** Never commit PayPal sandbox credentials to `.env`. Render dashboard only.
