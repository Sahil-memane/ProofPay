"""
APScheduler-backed scheduler.

Uses the scheduled_actions DB table as source of truth — jobs survive Render
free-tier sleep cycles and process restarts.

Replaces stubs/scheduler.py. The stub re-exports from here.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from backend.app.core.logging import get_logger

log = get_logger(__name__)

# In-memory fallback for tests/startup
_fallback_jobs: list[dict[str, Any]] = []

# APScheduler instance (created lazily to avoid import-time side-effects)
_scheduler: Any = None


def _get_scheduler() -> Any:
    global _scheduler
    if _scheduler is None:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


def start() -> None:
    """Start the APScheduler. Called from FastAPI lifespan."""
    sched = _get_scheduler()
    if not sched.running:
        sched.start()
        log.info("APScheduler started")


def shutdown() -> None:
    """Gracefully stop APScheduler. Called from FastAPI lifespan."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("APScheduler shut down")


async def enqueue(
    func_name: str,
    *,
    due_at: datetime | None = None,
    delay_seconds: float = 0,
    case_id: str | None = None,
    kwargs: dict[str, Any] | None = None,
) -> str:
    """
    Schedule a job.
    Writes to scheduled_actions table; also schedules via APScheduler for precision.
    Falls back to in-memory list if DB is unavailable.
    """
    if due_at is None:
        from backend.app.core.clock import utcnow
        from datetime import timedelta
        due_at = utcnow() + timedelta(seconds=delay_seconds)

    job_id = str(uuid.uuid4())
    job_kwargs = kwargs or {}

    try:
        from backend.app.db.session import AsyncSessionLocal
        from backend.app.db.models.support import ScheduledAction

        async with AsyncSessionLocal() as session:
            row = ScheduledAction(
                id=job_id,
                func_name=func_name,
                kwargs=job_kwargs,
                due_at=due_at,
                status="pending",
                case_id=case_id,
            )
            session.add(row)
            await session.commit()
    except Exception as exc:
        log.warning("enqueue DB unavailable (%s), using fallback", exc)
        _fallback_jobs.append({
            "id": job_id,
            "func": func_name,
            "kwargs": job_kwargs,
            "due_at": due_at.isoformat(),
            "case_id": case_id,
        })

    # Also tell APScheduler to wake at due_at
    try:
        sched = _get_scheduler()
        if sched.running:
            sched.add_job(
                _tick_wrapper,
                trigger="date",
                run_date=due_at,
                args=[func_name, job_kwargs],
                id=job_id,
                replace_existing=True,
            )
    except Exception as exc:
        log.debug("APScheduler add_job skipped: %s", exc)

    return job_id


def enqueue_sync(
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> str:
    """
    Sync enqueue shim — matches the stubs.scheduler interface.
    Records job in fallback list immediately; async enqueue writes to DB later.
    """
    job_id = f"job-{len(_fallback_jobs):04d}"
    _fallback_jobs.append({
        "id": job_id,
        "func": func.__name__,
        "args": args,
        "kwargs": kwargs,
    })
    return job_id


async def cancel_for_case(case_id: str) -> int:
    """Cancel all pending scheduled actions for a case."""
    count = 0
    try:
        from backend.app.db.session import AsyncSessionLocal
        from backend.app.db.models.support import ScheduledAction
        from sqlalchemy import update

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                update(ScheduledAction)
                .where(
                    ScheduledAction.case_id == case_id,
                    ScheduledAction.status == "pending",
                )
                .values(status="cancelled")
            )
            await session.commit()
            count = result.rowcount or 0
    except Exception:
        # Fallback
        before = len(_fallback_jobs)
        _fallback_jobs[:] = [j for j in _fallback_jobs if j.get("case_id") != case_id]
        count = before - len(_fallback_jobs)

    return count


def cancel_for_case_sync(case_id: str) -> int:
    """Sync shim matching stubs.scheduler interface."""
    before = len(_fallback_jobs)
    _fallback_jobs[:] = [
        j for j in _fallback_jobs
        if j.get("kwargs", {}).get("case_id") != case_id
        and case_id not in str(j.get("args", ()))
    ]
    return before - len(_fallback_jobs)


def remove_job(job_id: str) -> None:
    """Remove from fallback list (APScheduler jobs auto-remove after firing)."""
    _fallback_jobs[:] = [j for j in _fallback_jobs if j.get("id") != job_id]
    try:
        sched = _get_scheduler()
        if sched.running:
            sched.remove_job(job_id)
    except Exception:
        pass


def get_jobs() -> list[dict[str, Any]]:
    """Return pending in-memory jobs (for stubs compat)."""
    return list(_fallback_jobs)


def reset() -> None:
    """Clear all in-memory jobs (tests only)."""
    _fallback_jobs.clear()


async def tick_pending() -> int:
    """
    Called from /internal/tick. Processes all pending scheduled_actions
    that are due. Returns number of jobs executed.
    """
    executed = 0
    try:
        from backend.app.db.session import AsyncSessionLocal
        from backend.app.db.models.support import ScheduledAction
        from sqlalchemy import select, update
        from backend.app.core.clock import utcnow

        async with AsyncSessionLocal() as session:
            now = utcnow()
            stmt = (
                select(ScheduledAction)
                .where(ScheduledAction.status == "pending", ScheduledAction.due_at <= now)
                .with_for_update(skip_locked=True)
                .limit(20)
            )
            rows = (await session.execute(stmt)).scalars().all()
            for row in rows:
                row.status = "running"
            await session.commit()

            for row in rows:
                await _run_job(row.id, row.func_name, row.kwargs)
                executed += 1

    except Exception as exc:
        log.debug("tick_pending DB unavailable: %s", exc)

    return executed


async def _run_job(job_id: str, func_name: str, kwargs: dict[str, Any]) -> None:
    from backend.app.db.session import AsyncSessionLocal
    from backend.app.db.models.support import ScheduledAction
    from sqlalchemy import update
    from backend.app.core.clock import utcnow

    try:
        from backend.app.scheduler.registry import HANDLERS
        handler = HANDLERS.get(func_name)
        if handler:
            result = handler(**kwargs)
            if asyncio.iscoroutine(result):
                await result
            status = "done"
            error = None
        else:
            log.warning("No handler registered for func_name=%s", func_name)
            status = "done"
            error = None
    except Exception as exc:
        status = "failed"
        error = str(exc)[:1000]
        log.error("Scheduled job %s (%s) failed: %s", job_id, func_name, exc, exc_info=True)

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(ScheduledAction)
                .where(ScheduledAction.id == job_id)
                .values(status=status, error=error, executed_at=utcnow())
            )
            await session.commit()
    except Exception as exc:
        log.warning("Could not update job status for %s: %s", job_id, exc)


def _tick_wrapper(func_name: str, kwargs: dict[str, Any]) -> None:
    """APScheduler calls this sync — we create a task."""
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_run_job(func_name, func_name, kwargs))
    except RuntimeError:
        pass
