"""
ProofPay FastAPI application.

Startup sequence:
  1. Configure logging
  2. Lifespan: start webhook worker + APScheduler
  3. Mount routers: cases, sim, projects, webhooks, audit, tick
  4. Register exception handlers
  5. /healthz endpoint
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.errors import ProofPayError, generic_error_handler, proofpay_error_handler
from backend.app.core.logging import configure_root_logging, get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan — startup and shutdown."""
    configure_root_logging()
    log.info("ProofPay API starting up (DEMO_MODE=%s)", settings.demo_mode)

    # Start APScheduler
    from backend.app.scheduler.core import start as scheduler_start
    scheduler_start()

    # Start webhook ingestion worker
    from backend.app.ingestion.worker import run_worker_loop
    worker_task = asyncio.create_task(run_worker_loop(), name="webhook-worker")

    yield  # Application runs here

    # Shutdown
    log.info("ProofPay API shutting down")
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    from backend.app.scheduler.core import shutdown as scheduler_shutdown
    scheduler_shutdown()


app = FastAPI(
    title="ProofPay API",
    version="0.1.0",
    description="AI-powered collections, payment recovery, and freelance escrow.",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────────────────────
app.add_exception_handler(ProofPayError, proofpay_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, generic_error_handler)  # type: ignore[arg-type]

# ── Routers ───────────────────────────────────────────────────────────────────
from backend.app.api import cases, sim  # noqa: E402
from backend.app.api.projects import router as projects_router  # noqa: E402
from backend.app.api.reputation import router as reputation_router  # noqa: E402
from backend.app.ingestion.receiver import router as ingestion_router  # noqa: E402

app.include_router(cases.router)
app.include_router(sim.router)
app.include_router(projects_router)
app.include_router(ingestion_router)
app.include_router(reputation_router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/healthz", tags=["meta"])
async def healthz() -> dict[str, str]:
    """Health check — verifies DB connectivity."""
    db_status = "ok"
    try:
        from backend.app.db.session import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        log.warning("DB health check failed: %s", exc)
        db_status = "unavailable"

    return {"status": "ok", "db": db_status, "version": "0.1.0"}


# ── Internal tick endpoint ─────────────────────────────────────────────────────
@app.post("/internal/tick", tags=["meta"])
async def internal_tick(x_tick_token: str = Header(default="")) -> dict[str, object]:
    """
    Drives the scheduler on Render's free tier (no cron worker needed).
    Called by GitHub Actions keepwarm.yml every 5 minutes.
    Also processes any pending webhook events.
    """
    if x_tick_token != settings.internal_tick_token:
        raise HTTPException(status_code=401, detail="Invalid tick token")

    from backend.app.scheduler.core import tick_pending
    from backend.app.core.clock import utcnow

    jobs_executed = await tick_pending()

    return {
        "ticked": True,
        "jobs_executed": jobs_executed,
        "time": utcnow().isoformat(),
    }


# ── Audit endpoint ────────────────────────────────────────────────────────────
@app.get("/audit", tags=["meta"])
async def get_audit_log(
    case_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Return recent audit events, optionally filtered by case_id."""
    from backend.app.audit import get_events
    events = get_events(case_id=case_id)
    return events[:limit]
