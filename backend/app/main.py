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
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import settings
from backend.app.core.errors import ProofPayError, generic_error_handler, proofpay_error_handler
from backend.app.core.logging import configure_root_logging, get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan — startup and shutdown."""
    configure_root_logging()
    log.info("ProofPay API starting up (DEMO_MODE=%s)", settings.demo_mode)

    # Ensure database tables exist and seed default demo data if needed
    try:
        from backend.app.db.base import Base
        from backend.app.db.session import sync_engine
        import backend.app.db.models  # noqa: F401
        Base.metadata.create_all(bind=sync_engine)
        from backend.scripts.seed_postgres import run as run_seed
        run_seed()
    except Exception as exc:
        log.warning("Database init/seed notice: %s", exc)

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
# In production (Render), the React SPA is served by this same origin,
# so CORS is only needed for external callers. Keep open for hackathon demo.
_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
]
# If APP_BASE_URL is set (Render deploy), add it to allowed origins
if settings.app_base_url and settings.app_base_url not in _CORS_ORIGINS:
    _CORS_ORIGINS.append(settings.app_base_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.onrender\.com",  # all render subdomains
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
from backend.app.api.submissions import router as submissions_router  # noqa: E402
from backend.app.ingestion.receiver import router as ingestion_router  # noqa: E402
from backend.app.api.dashboard import router as dashboard_router  # noqa: E402
from backend.app.api.fixtures import router as fixtures_router  # noqa: E402
from backend.app.api.auth import router as auth_router  # noqa: E402
from backend.app.api.data_views import router as data_views_router  # noqa: E402
from backend.app.api.settings_api import router as settings_api_router  # noqa: E402

app.include_router(cases.router)
app.include_router(sim.router)
app.include_router(projects_router)
app.include_router(submissions_router)
app.include_router(ingestion_router)
app.include_router(reputation_router)
app.include_router(dashboard_router)
app.include_router(fixtures_router)
app.include_router(auth_router)
app.include_router(data_views_router)
app.include_router(settings_api_router)


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


# ── Frontend static files & SPA routing (mount LAST — after all API routes) ──
_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend" / "react-app" / "dist"
if _FRONTEND_DIR.exists():
    from fastapi.responses import FileResponse

    _assets_dir = _FRONTEND_DIR / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    @app.middleware("http")
    async def spa_html_middleware(request: Request, call_next):
        accept = request.headers.get("accept", "")
        path = request.url.path
        # If it's a browser page navigation (accept contains text/html) and not API docs:
        if (
            request.method == "GET"
            and "text/html" in accept
            and not path.startswith(("/docs", "/redoc", "/openapi.json"))
        ):
            static_file = _FRONTEND_DIR / path.lstrip("/")
            if path != "/" and static_file.is_file():
                return FileResponse(static_file)
            index_html = _FRONTEND_DIR / "index.html"
            if index_html.is_file():
                return FileResponse(index_html)

        response = await call_next(request)

        # Fallback for client-side routes returning 404 on direct hit/refresh
        if response.status_code == 404 and request.method == "GET":
            static_file = _FRONTEND_DIR / path.lstrip("/")
            if static_file.is_file():
                return FileResponse(static_file)
            index_html = _FRONTEND_DIR / "index.html"
            if index_html.is_file() and ("text/html" in accept or "*/*" in accept):
                return FileResponse(index_html)
        return response
