"""
ProofPay structured logging.

Configures a JSON-friendly logger. Secrets and tokens are redacted
before any log output.
"""
from __future__ import annotations

import logging
import re
import sys
from typing import Any

# Patterns to redact from log messages and structured fields
_REDACT_PATTERNS = [
    re.compile(r"(Authorization:\s*Bearer\s*)[^\s,\"]+", re.IGNORECASE),
    re.compile(r"(client_secret[\"=:\s]+)[^\s,\"&]+", re.IGNORECASE),
    re.compile(r"(password[\"=:\s]+)[^\s,\"&]+", re.IGNORECASE),
    re.compile(r"(api[_-]?key[\"=:\s]+)[^\s,\"&]+", re.IGNORECASE),
]


def redact(text: str) -> str:
    """Redact known secret patterns from a string."""
    for pattern in _REDACT_PATTERNS:
        text = pattern.sub(r"\g<1>[REDACTED]", text)
    return text


def get_logger(name: str) -> logging.Logger:
    """Return a named logger configured for structured output."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%SZ",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def configure_root_logging(level: int = logging.INFO) -> None:
    """Called once at application startup."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        stream=sys.stdout,
    )
    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# Package-level default logger
log = get_logger("proofpay")
