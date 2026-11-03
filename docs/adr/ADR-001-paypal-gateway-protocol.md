# ADR-001: PayPal Gateway Protocol Pattern

**Status:** Accepted  
**Date:** 2026-11-03  
**Deciders:** Dev 1 (Tech Lead)

## Context

ProofPay needs to call PayPal APIs in production (REST) while allowing local development and testing without real PayPal credentials. Two modes must be completely transparent to the rest of the application.

## Decision

We define `PayPalGateway` as a structural Protocol (PEP 544) in `backend/app/paypal/gateway.py`. Both `FakePayPal` and `RestPayPalGateway` implement this Protocol via duck-typing. The gateway is selected at startup via `PAYPAL_EXEC_MODE` env var (`fake` | `rest`). `get_gateway()` in `backend/app/paypal/__init__.py` returns the correct instance.

## Consequences

- **Positive:** Full code path is identical in fake and real mode. FakePayPal emits real webhooks into the ingestion worker via `emit_webhook()`, so the entire system is exercised locally.
- **Positive:** Zero mock patching in tests — just set `PAYPAL_EXEC_MODE=fake`.
- **Negative:** FakePayPal must be kept in sync with PayPal API response shapes. Divergence = silent test failures.
- **Rule:** `PAYPAL_EXEC_MODE=fake` always in `.env`. Only `rest` in Render dashboard for gate runs.

