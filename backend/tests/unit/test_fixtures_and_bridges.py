"""
Unit tests for Step 12: Fixtures, Escrow Bridges, and Milestone Reconciliation.
"""
from pathlib import Path
import pytest

from backend.app.api.fixtures import get_flaky, get_site_a, get_site_b, reset_flaky_counter
from backend.app.reconciliation.escrow_recon import (
    clear_exception_list,
    get_exception_list,
    post_release_check,
    pre_release_check,
)
from backend.app.reconciliation.normalizer import ReconRecord
from backend.app.recovery.bridges import (
    clear_published_events,
    get_published_events,
    handle_funding_failed,
    handle_instalment_failed,
    on_escrow_case_state_change,
    open_case_for_overdue_invoice_with_escrow_suggestion,
)
from backend.app.recovery.constants import (
    CASE_TYPE_ESCROW_FUNDING,
    CASE_TYPE_OVERDUE_INVOICE,
    EVENT_FUNDING_RESUMED,
    EVENT_PROJECT_FLAGGED,
)
from backend.app.stubs.contracts_stub import CaseState

ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = ROOT / "fixtures"


@pytest.fixture(autouse=True)
def setup_teardown():
    reset_flaky_counter()
    clear_exception_list()
    clear_published_events()
    yield
    reset_flaky_counter()
    clear_exception_list()
    clear_published_events()


# ── Test Demo Sites in api/fixtures.py ────────────────────────────────────────

def test_site_a_contains_pricing_and_contact():
    resp = get_site_a()
    assert resp.status_code == 200
    html = resp.body.decode("utf-8")
    assert "Pricing" in html
    assert "Contact" in html


def test_site_b_missing_pricing():
    resp = get_site_b()
    assert resp.status_code == 200
    html = resp.body.decode("utf-8")
    assert "Pricing" not in html
    assert "Contact" in html


def test_flaky_returns_500_every_third_request():
    # 1: 200
    r1 = get_flaky()
    assert r1.status_code == 200

    # 2: 200
    r2 = get_flaky()
    assert r2.status_code == 200

    # 3: 500
    r3 = get_flaky()
    assert r3.status_code == 500

    # 4: 200
    r4 = get_flaky()
    assert r4.status_code == 200

    # 5: 200
    r5 = get_flaky()
    assert r5.status_code == 200

    # 6: 500
    r6 = get_flaky()
    assert r6.status_code == 500


# ── Test Evidence Fixtures Directory ──────────────────────────────────────────

def test_evidence_fixtures_and_readme():
    readme = FIXTURES_DIR / "README.md"
    assert readme.exists()
    content = readme.read_text(encoding="utf-8")
    assert "pass" in content
    assert "fail" in content
    assert "borderline" in content

    # Test PDF and text files exist
    assert (FIXTURES_DIR / "evidence_complete_spec.pdf").exists()
    assert (FIXTURES_DIR / "evidence_signed_agreement.txt").exists()
    assert (FIXTURES_DIR / "evidence_corrupted_scan.pdf").exists()
    assert (FIXTURES_DIR / "evidence_blank_document.txt").exists()
    assert (FIXTURES_DIR / "evidence_partial_diff.txt").exists()
    assert (FIXTURES_DIR / "evidence_preliminary_mockup.pdf").exists()


# ── Test Escrow Bridges in recovery/bridges.py ────────────────────────────────

def test_funding_failed_opens_escrow_funding_case():
    case = handle_funding_failed(
        project_id="PROJ-ESCROW-001",
        client_id="CUST-CLIENT-01",
        amount_usd=1200.0,
    )
    assert case["case_type"] == CASE_TYPE_ESCROW_FUNDING
    assert case["project_id"] == "PROJ-ESCROW-001"
    assert case["amount_usd"] == 1200.0


def test_instalment_failed_opens_escrow_case():
    case = handle_instalment_failed(
        project_id="PROJ-ESCROW-002",
        milestone_id="M-002-1",
        client_id="CUST-CLIENT-02",
        amount_usd=600.0,
    )
    assert case["case_type"] == CASE_TYPE_ESCROW_FUNDING
    assert case["milestone_id"] == "M-002-1"


def test_escrow_case_state_change_publishes_events():
    case = {
        "id": "CASE-ESC-99",
        "case_type": CASE_TYPE_ESCROW_FUNDING,
        "project_id": "PROJ-ESCROW-99",
        "customer_id": "CUST-99",
        "state": CaseState.RECOVERED,
    }
    evt1 = on_escrow_case_state_change(case)
    assert evt1 == EVENT_FUNDING_RESUMED
    published = get_published_events()
    assert len(published) == 1
    assert published[0]["event"] == EVENT_FUNDING_RESUMED
    assert published[0]["payload"]["project_id"] == "PROJ-ESCROW-99"

    # UNRECOVERED publishes project.flagged_for_freelancer
    case["state"] = CaseState.UNRECOVERED
    case["unrecovered_reason"] = "funding_expired"
    evt2 = on_escrow_case_state_change(case)
    assert evt2 == EVENT_PROJECT_FLAGGED
    published = get_published_events()
    assert len(published) == 2
    assert published[1]["event"] == EVENT_PROJECT_FLAGGED


def test_overdue_invoice_with_escrow_suggestion_and_intake_link():
    case = open_case_for_overdue_invoice_with_escrow_suggestion(
        invoice_id="INV-EXT-100",
        customer_id="CUST-OUTSIDE-01",
        amount_usd=450.0,
    )
    assert case["case_type"] == CASE_TYPE_OVERDUE_INVOICE
    assert "To protect future project payments" in case["escrow_suggestion"]
    assert f"/intake?prefill={case['id']}" == case["intake_link"]


# ── Test Reconciliation Pre-Release & Post-Release Checks ────────────────────

def test_missing_capture_blocks_pre_release_check():
    """Check: a missing capture blocks the pre-release check."""
    milestone = {
        "milestone_id": "MILESTONE-001",
        "project_id": "PROJ-100",
        "amount_usd": 500.0,
        "currency": "USD",
        "funding_capture_id": "CAP-NONEXISTENT",
    }
    records: list[ReconRecord] = []  # Empty records -> capture missing!

    passed = pre_release_check(milestone, records=records)
    assert passed is False, "A missing capture must block the pre-release check!"

    # Verify added to exception list
    exceptions = get_exception_list()
    assert len(exceptions) == 1
    assert exceptions[0]["check"] == "pre_release_check"
    assert exceptions[0]["reason"] == "missing_or_partial_funding_capture"
    assert exceptions[0]["milestone_id"] == "MILESTONE-001"


def test_valid_capture_passes_pre_release_check():
    milestone = {
        "milestone_id": "MILESTONE-002",
        "project_id": "PROJ-200",
        "amount_usd": 750.0,
        "currency": "USD",
        "funding_capture_id": "CAP-VALID-750",
    }
    records = [
        ReconRecord(
            source="paypal",
            external_id="CAP-VALID-750",
            amount=750.0,
            currency="USD",
            date="2025-01-10T12:00:00Z",
            customer_ref="CUST-CLIENT",
            reference="MILESTONE-002",
        )
    ]
    passed = pre_release_check(milestone, records=records)
    assert passed is True
    assert len(get_exception_list()) == 0


def test_missing_payout_blocks_post_release_check():
    milestone = {
        "milestone_id": "MILESTONE-003",
        "project_id": "PROJ-300",
        "amount_usd": 300.0,
        "currency": "USD",
        "payout_id": "PAYOUT-MISSING",
    }
    records: list[ReconRecord] = []
    passed = post_release_check(milestone, records=records)
    assert passed is False
    exceptions = get_exception_list()
    assert len(exceptions) == 1
    assert exceptions[0]["check"] == "post_release_check"
    assert exceptions[0]["reason"] == "payout_not_found_in_records"

