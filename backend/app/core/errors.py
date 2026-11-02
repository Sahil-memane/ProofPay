"""
ProofPay error model.

Standard error classes and the FastAPI exception handler that serialises
them to a consistent JSON shape: {code, message, checks, details}.
"""
from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class ProofPayError(Exception):
    """Base for all domain errors."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(
        self,
        message: str,
        code: str | None = None,
        checks: dict[str, bool] | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.checks = checks or {}
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.checks:
            d["checks"] = self.checks
        if self.details is not None:
            d["details"] = self.details
        return d


class PolicyError(ProofPayError):
    """Raised when a policy check denies an action."""

    status_code = 403
    code = "policy_denied"


PolicyViolationError = PolicyError


class PayPalError(ProofPayError):
    """Raised when a PayPal API call fails."""

    status_code = 502
    code = "paypal_error"

    def __init__(self, message: str, paypal_response: dict | None = None) -> None:
        super().__init__(message, details=paypal_response)
        self.paypal_response = paypal_response or {}


class NotFoundError(ProofPayError):
    status_code = 404
    code = "not_found"


class ConflictError(ProofPayError):
    status_code = 409
    code = "conflict"


class ValidationError(ProofPayError):
    status_code = 422
    code = "validation_error"


class AuthError(ProofPayError):
    status_code = 401
    code = "unauthorized"


# ── FastAPI exception handlers ─────────────────────────────────────────────────

async def proofpay_error_handler(request: Request, exc: ProofPayError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    from backend.app.core.logging import log

    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": "internal_error", "message": "An unexpected error occurred."},
    )
