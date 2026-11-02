"""Shared pytest fixtures for ProofPay Dev-3 test suite."""
import pytest
from datetime import datetime, timezone


@pytest.fixture
def utcnow():
    return datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
