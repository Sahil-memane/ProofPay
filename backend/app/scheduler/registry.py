"""
Scheduler handler registry.
Maps func_name strings → the actual handler callables in scheduler/jobs/handlers.py.
"""
from __future__ import annotations

from backend.app.scheduler.jobs import handlers

HANDLERS = {
    "ladder_step": handlers.ladder_step,
    "payday_retry": handlers.payday_retry,
    "promise_reminder": handlers.promise_reminder,
    "overdue_invoice_scan": handlers.overdue_invoice_scan,
    "escrow_timer": handlers.escrow_timer,
    "scheduled_eval_run": handlers.scheduled_eval_run,
}
