"""ProofPay core package."""
from backend.app.core.clock import (
    advance_time,
    register_tick_listener,
    reset,
    set_time,
    simulate_days,
    utcnow,
)
from backend.app.core.config import settings
from backend.app.core.errors import (
    AuthError,
    ConflictError,
    NotFoundError,
    PayPalError,
    PolicyError,
    ProofPayError,
    ValidationError,
)

__all__ = [
    "settings",
    "utcnow",
    "set_time",
    "reset",
    "advance_time",
    "simulate_days",
    "register_tick_listener",
    "ProofPayError",
    "PolicyError",
    "PayPalError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "AuthError",
]
