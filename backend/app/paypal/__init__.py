"""
PayPal package — factory for the active gateway implementation.

Usage:
    from backend.app.paypal import get_gateway
    gateway = get_gateway()
    order = await gateway.create_order(...)
"""
from __future__ import annotations

from backend.app.paypal.gateway import PayPalGateway


def get_gateway() -> PayPalGateway:
    """Return the configured PayPal gateway (real REST or FakePayPal)."""
    from backend.app.core.config import settings

    if settings.is_fake_paypal:
        from backend.app.paypal.fake_paypal import FakePayPal
        return FakePayPal()

    from backend.app.paypal.rest_gateway import RestPayPalGateway
    return RestPayPalGateway()


__all__ = ["get_gateway", "PayPalGateway"]
