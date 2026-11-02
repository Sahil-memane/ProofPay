# TEMP: replaced by scheduler/
"""Stub scheduler — records jobs, supports cancellation per case."""
from __future__ import annotations
from typing import Any, Callable

_jobs: list[dict[str, Any]] = []


def enqueue(func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
    """Enqueue a job (stub: records it, returns a fake job id)."""
    job_id = f"job-{len(_jobs):04d}"
    _jobs.append({"func": func.__name__, "args": args, "kwargs": kwargs, "id": job_id})
    return job_id


def cancel_for_case(case_id: str) -> int:
    """Cancel all pending scheduled actions for the given case (safe if none)."""
    global _jobs
    initial_count = len(_jobs)
    _jobs = [
        j for j in _jobs
        if j.get("kwargs", {}).get("case_id") != case_id
        and case_id not in str(j.get("args", ()))
    ]
    return initial_count - len(_jobs)


def remove_job(job_id: str) -> None:
    """Remove a single job by id once executed."""
    global _jobs
    _jobs = [j for j in _jobs if j.get("id") != job_id]


def get_jobs() -> list[dict[str, Any]]:
    return list(_jobs)


def reset() -> None:
    _jobs.clear()
