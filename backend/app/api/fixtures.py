"""
Fixtures API Router (Thin FastAPI router).

Endpoints:
  GET /fixtures/traps      - Inspection of planted evaluation traps
  GET /fixtures/customers  - Generated customer fixtures
  GET /fixtures/invoices   - Generated overdue invoices
  GET /fixtures/escrow     - Escrow projects with evidence fixture names
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/fixtures", tags=["fixtures"])

ROOT = Path(__file__).resolve().parents[3]
DATA_KEY = ROOT / "data" / "answer_key"
DATA_GEN = ROOT / "data" / "generated"

_FLAKY_REQUEST_COUNT = 0


def _read_json_safe(path: Path) -> Any:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@router.get("/traps")
def list_traps() -> list[dict[str, Any]]:
    return _read_json_safe(DATA_KEY / "traps.json")


@router.get("/customers")
def list_customers() -> list[dict[str, Any]]:
    return _read_json_safe(DATA_GEN / "customers.json")


@router.get("/invoices")
def list_invoices() -> list[dict[str, Any]]:
    return _read_json_safe(DATA_GEN / "invoices.json")


@router.get("/escrow")
def list_escrow_projects() -> list[dict[str, Any]]:
    return _read_json_safe(DATA_GEN / "escrow_projects.json")


# ── Demo Test Sites ───────────────────────────────────────────────────────────

@router.get("/site-a", response_class=HTMLResponse)
def get_site_a() -> HTMLResponse:
    """Demo test site A: contains both 'Pricing' and 'Contact'."""
    html_content = """<!DOCTYPE html>
<html>
<head><title>Site A - Compliant Merchant</title></head>
<body>
    <h1>Welcome to Store A</h1>
    <nav>
        <a href="/pricing">Pricing</a>
        <a href="/contact">Contact</a>
    </nav>
    <main>
        <section id="pricing">
            <h2>Our Pricing</h2>
            <p>Clear plans with transparent pricing terms.</p>
        </section>
        <section id="contact">
            <h2>Contact Us</h2>
            <p>Email: support@store-a.example.com</p>
        </section>
    </main>
</body>
</html>"""
    return HTMLResponse(content=html_content, status_code=200)


@router.get("/site-b", response_class=HTMLResponse)
def get_site_b() -> HTMLResponse:
    """Demo test site B: missing 'Pricing' keyword."""
    html_content = """<!DOCTYPE html>
<html>
<head><title>Site B - Non-Compliant Merchant</title></head>
<body>
    <h1>Welcome to Store B</h1>
    <nav>
        <a href="/about">About</a>
        <a href="/contact">Contact</a>
    </nav>
    <main>
        <section id="contact">
            <h2>Contact Us</h2>
            <p>Email: support@store-b.example.com</p>
        </section>
    </main>
</body>
</html>"""
    return HTMLResponse(content=html_content, status_code=200)


@router.get("/flaky")
def get_flaky() -> Response:
    """Demo flaky endpoint: returns HTTP 500 on every third request."""
    global _FLAKY_REQUEST_COUNT
    _FLAKY_REQUEST_COUNT += 1
    if _FLAKY_REQUEST_COUNT % 3 == 0:
        return Response(content="Internal Server Error (Flaky 500)", status_code=500)
    return Response(content='{"status": "ok", "attempt": %d}' % _FLAKY_REQUEST_COUNT, media_type="application/json", status_code=200)


def reset_flaky_counter() -> None:
    global _FLAKY_REQUEST_COUNT
    _FLAKY_REQUEST_COUNT = 0


