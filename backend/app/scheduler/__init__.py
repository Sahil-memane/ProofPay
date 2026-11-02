"""
Scheduler package — re-exports matching the stubs.scheduler interface.
Also provides async versions for direct use.
"""
from backend.app.scheduler.core import (
    cancel_for_case_sync as cancel_for_case,
    enqueue_sync as enqueue,
    get_jobs,
    remove_job,
    reset,
    start,
    shutdown,
    tick_pending,
)

__all__ = [
    "enqueue",
    "cancel_for_case",
    "remove_job",
    "get_jobs",
    "reset",
    "start",
    "shutdown",
    "tick_pending",
]
