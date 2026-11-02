"""
Unit tests for Escrow, PayPal, and Reputation modules.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.contracts.enums import MilestoneState, ProjectState
from backend.app.escrow.funding import fund_project
from backend.app.escrow.plan_hash import compute_plan_hash
from backend.app.escrow.state_machine import (
    InvalidEscrowTransitionError,
    can_transition_milestone,
    can_transition_project,
    transition_milestone,
    transition_project,
)
from backend.app.main import app
from backend.app.paypal.fake_paypal import FakePayPal
from backend.app.reputation.ledger import get_score, record_event, reset as reset_reputation


# ── Plan Hash Tests ───────────────────────────────────────────────────────────

def test_plan_hash_determinism():
    milestones_a = [
        {"id": "m1", "title": "Milestone 1", "amount": 100.0, "criteria": [{"rule": "test"}]},
        {"id": "m2", "title": "Milestone 2", "amount": 200.0, "criteria": []},
    ]
    milestones_b = [
        {"title": "Milestone 1", "criteria": [{"rule": "test"}], "amount": 100.0, "id": "m1"},
        {"amount": 200.0, "criteria": [], "id": "m2", "title": "Milestone 2"},
    ]
    hash_a = compute_plan_hash(milestones_a)
    hash_b = compute_plan_hash(milestones_b)
    assert hash_a == hash_b
    assert len(hash_a) == 64  # SHA-256 hex


def test_plan_hash_tamper_detection():
    milestones = [{"id": "m1", "amount": 100.0, "criteria": []}]
    tampered = [{"id": "m1", "amount": 100.01, "criteria": []}]
    assert compute_plan_hash(milestones) != compute_plan_hash(tampered)


# ── State Machine Tests ───────────────────────────────────────────────────────

def test_project_state_transitions():
    assert can_transition_project(ProjectState.DRAFT, ProjectState.PLAN_APPROVED)
    assert can_transition_project(ProjectState.PLAN_APPROVED, ProjectState.FUNDED)
    assert not can_transition_project(ProjectState.DRAFT, ProjectState.FUNDED)
    assert not can_transition_project(ProjectState.COMPLETED, ProjectState.DRAFT)

    tgt = transition_project("proj-1", ProjectState.PLAN_APPROVED, current=ProjectState.DRAFT)
    assert tgt == ProjectState.PLAN_APPROVED

    with pytest.raises(InvalidEscrowTransitionError):
        transition_project("proj-1", ProjectState.COMPLETED, current=ProjectState.DRAFT)


def test_milestone_state_transitions():
    assert can_transition_milestone(MilestoneState.DRAFT, MilestoneState.FUNDED)
    assert can_transition_milestone(MilestoneState.FUNDED, MilestoneState.SUBMITTED)
    assert can_transition_milestone(MilestoneState.SUBMITTED, MilestoneState.VERIFYING)
    assert can_transition_milestone(MilestoneState.VERIFYING, MilestoneState.RELEASED)
    assert not can_transition_milestone(MilestoneState.DRAFT, MilestoneState.RELEASED)

    tgt = transition_milestone("m-1", MilestoneState.FUNDED, current=MilestoneState.DRAFT)
    assert tgt == MilestoneState.FUNDED

    with pytest.raises(InvalidEscrowTransitionError):
        transition_milestone("m-1", MilestoneState.RELEASED, current=MilestoneState.DRAFT)


# ── Fake PayPal Tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fake_paypal_lifecycle():
    fake = FakePayPal()
    order = await fake.create_order(amount=250.0, currency="USD", request_id="req-123")
    assert order["id"].startswith("FAKE-ORDER-")
    assert order["status"] == "CREATED"

    capture = await fake.capture_order(order_id=order["id"], request_id="cap-123")
    assert capture["status"] == "COMPLETED"
    assert "id" in capture or "capture_id" in capture

    payout = await fake.create_payout(
        recipient_email="dev@example.com",
        amount=250.0,
        currency="USD",
        sender_batch_id="batch-1",
    )
    assert payout["batch_header"]["batch_status"] == "PENDING"
    assert "payout_batch_id" in payout["batch_header"]


# ── Reputation Tests ──────────────────────────────────────────────────────────

def test_reputation_scoring_and_clamping():
    reset_reputation()
    subject = "user-alice"
    assert get_score(subject)["score"] == 50

    score = record_event(subject, "on_time_release")
    assert score == 55

    score = record_event(subject, "dispute_lost")
    assert score == 45

    # Negative events cannot drop below 0
    for _ in range(15):
        record_event(subject, "dispute_lost")
    assert get_score(subject)["score"] == 0

    # Positive events cannot exceed 100
    for _ in range(30):
        record_event(subject, "on_time_release")
    assert get_score(subject)["score"] == 100


# ── API End-to-End Escrow Flow Tests ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_escrow_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create project
        res = await client.post(
            "/projects",
            json={
                "job_description": "Full-stack payment integration contract",
                "total_amount": 500.0,
                "currency": "USD",
                "client_id": "client-test",
                "freelancer_id": "freelancer-test",
            },
        )
        assert res.status_code == 201
        data = res.json()
        project_id = data["project"]["id"]
        assert data["project"]["state"] == "DRAFT"
        assert len(data["milestones"]) == 1

        # 2. Get project
        get_res = await client.get(f"/projects/{project_id}")
        assert get_res.status_code == 200
        assert get_res.json()["project"]["id"] == project_id

        # 3. Client approves
        app1 = await client.post(f"/projects/{project_id}/approve", json={"party": "client"})
        assert app1.status_code == 200
        assert app1.json()["project"]["client_approved"] is True
        assert app1.json()["project"]["state"] == "DRAFT"

        # 4. Freelancer approves -> State moves to PLAN_APPROVED and hash is locked
        app2 = await client.post(f"/projects/{project_id}/approve", json={"party": "freelancer"})
        assert app2.status_code == 200
        assert app2.json()["project"]["freelancer_approved"] is True
        assert app2.json()["project"]["state"] == "PLAN_APPROVED"
        plan_hash = app2.json()["project"]["plan_hash"]
        assert plan_hash is not None

        # 5. Tampered plan hash fails
        bad_fund = await client.post(
            f"/projects/{project_id}/fund",
            json={"plan_hash": "bad-hash-tampered"},
        )
        assert bad_fund.status_code in (403, 409)

        # 6. Valid fund creates order
        fund_res = await client.post(
            f"/projects/{project_id}/fund",
            json={"plan_hash": plan_hash},
        )
        assert fund_res.status_code == 200
        order_id = fund_res.json()["order_id"]
        assert order_id is not None

        # 7. Capture order -> moves to FUNDED
        cap_res = await client.post(
            f"/projects/{project_id}/capture",
            json={"order_id": order_id},
        )
        assert cap_res.status_code == 200
        assert cap_res.json()["status"] == "COMPLETED"
        assert "capture_id" in cap_res.json()
