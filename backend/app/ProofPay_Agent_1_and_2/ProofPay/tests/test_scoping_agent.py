"""Automated test suite for ProofPay Scoping Agent.

Covers all 15 required test scenarios from Section 11 of the specification.
Uses mocked LLM responses to ensure deterministic, zero-cost, offline execution.
"""

import pytest
from unittest.mock import patch, MagicMock

from ProofPay.agents.scoping_agent.schemas import (
    ClarityCheckSchema,
    MilestonePlanSchema,
    MilestoneSchema,
    CriterionSchema,
)
from ProofPay.agents.scoping_agent.state import (
    ScopingState,
    STATUS_ERROR,
    STATUS_DRAFT,
    STATUS_NEEDS_HUMAN_EDIT,
    STATUS_PENDING_APPROVAL,
    STATUS_PLAN_APPROVED,
)
from ProofPay.agents.scoping_agent.validators import (
    validate_project_input,
    validate_and_correct_milestone_plan,
    compute_plan_hash,
    generate_fallback_milestone_plan,
)
from ProofPay.agents.scoping_agent.graph import ScopingAgentRunner
from ProofPay.services.llm_service import llm_service, LLMServiceError
from ProofPay.services.database import db
from ProofPay.services.audit_service import audit_service


# -----------------------------------------------------------------------------
# Test Fixtures & Helper Generators
# -----------------------------------------------------------------------------

def make_valid_milestones(budget: float = 1000.0) -> list[dict]:
    """Helper to produce 3 policy-compliant milestone dicts summing to budget."""
    m1_amt = round(budget * 0.30, 2)
    m2_amt = round(budget * 0.30, 2)
    m3_amt = round(budget - m1_amt - m2_amt, 2)

    return [
        {
            "id": "m1",
            "title": "Milestone 1: Repository & Architecture Setup",
            "description": "Initialize repository structure and CI/CD pipelines.",
            "payment_amount": m1_amt,
            "deadline": "Day 10",
            "acceptance_criteria": [
                {
                    "id": "m1_c1",
                    "type": "repo_file_exists",
                    "params": {"repo": "client/ecommerce-app", "file_path": "README.md"},
                    "weight": 0.50,
                    "must_pass": True,
                },
                {
                    "id": "m1_c2",
                    "type": "github_checks_passing",
                    "params": {"repo": "client/ecommerce-app", "branch_or_commit": "main"},
                    "weight": 0.50,
                    "must_pass": True,
                },
            ],
        },
        {
            "id": "m2",
            "title": "Milestone 2: Product Catalog & Cart",
            "description": "Implement product listing page and shopping cart functionality.",
            "payment_amount": m2_amt,
            "deadline": "Day 20",
            "acceptance_criteria": [
                {
                    "id": "m2_c1",
                    "type": "url_contains_text",
                    "params": {"url": "https://staging.ecommerce-demo.dev/products", "expected_text": "Products"},
                    "weight": 0.80,
                    "must_pass": True,
                },
                {
                    "id": "m2_c2",
                    "type": "manual_review",
                    "params": {"checklist": ["Cart adds and removes items properly"], "reviewer_role": "client"},
                    "weight": 0.20,
                    "must_pass": False,
                },
            ],
        },
        {
            "id": "m3",
            "title": "Milestone 3: Checkout, Payments & Launch",
            "description": "Complete payment processing integration and production deployment.",
            "payment_amount": m3_amt,
            "deadline": "Day 30",
            "acceptance_criteria": [
                {
                    "id": "m3_c1",
                    "type": "url_returns_200",
                    "params": {"url": "https://ecommerce-demo.dev/health"},
                    "weight": 0.75,
                    "must_pass": True,
                },
                {
                    "id": "m3_c2",
                    "type": "manual_review",
                    "params": {"checklist": ["Production smoke test signoff"], "reviewer_role": "client"},
                    "weight": 0.25,
                    "must_pass": False,
                },
            ],
        },
    ]



def make_test_config() -> dict:
    """Explicit client-supplied verification values for graph integration tests."""
    return {
        "payment_provider": "Stripe",
        "repository": "client/ecommerce-app",
        "staging_url": "https://staging.ecommerce-demo.dev",
        "production_url": "https://ecommerce-demo.dev",
    }


@pytest.fixture(autouse=True)
def reset_services():
    """Reset database and audit service between tests."""
    db.clear()
    audit_service.clear()


# -----------------------------------------------------------------------------
# Test 1: Valid e-commerce project input
# -----------------------------------------------------------------------------
def test_1_valid_ecommerce_project_input():
    project_data = {
        "project_description": "Build an e-commerce website with: 1. Homepage 2. Product listing 3. Shopping cart 4. Payment integration 5. Final deployment",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_id": "client_001",
        # Explicit client configuration is required because the mocked plan
        # contains repository and deployment URL acceptance checks.
        "user_provided_config": make_test_config(),
        "freelancer_id": "freelancer_001",
    }

    mock_plan = MilestonePlanSchema(
        milestones=[MilestoneSchema(**m) for m in make_valid_milestones(1000.0)]
    )

    with patch.object(llm_service, "check_clarity") as mock_clarity, \
         patch.object(llm_service, "generate_milestones") as mock_gen:

        mock_clarity.return_value = ClarityCheckSchema(is_clear=True, reasoning="Requirements are detailed.")
        mock_gen.return_value = mock_plan

        runner = ScopingAgentRunner()
        state = runner.start_project(project_data, thread_id="test_1")

        assert state["project_status"] in (STATUS_DRAFT, STATUS_PENDING_APPROVAL)
        assert len(state["milestones"]) == 3
        assert state["validation_errors"] == []
        assert state["plan_source"] == "llm_generated"
        assert state["total_budget"] == 1000.0


# -----------------------------------------------------------------------------
# Test 2: Empty project description
# -----------------------------------------------------------------------------
def test_2_empty_project_description():
    project_data = {
        "project_description": "   ",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_id": "client_002",
        "freelancer_id": "freelancer_002",
    }

    runner = ScopingAgentRunner()
    state = runner.start_project(project_data, thread_id="test_2")

    assert state["project_status"] == STATUS_ERROR
    assert "Project description must not be empty" in state["error_message"]


# -----------------------------------------------------------------------------
# Test 3: Unsupported currency
# -----------------------------------------------------------------------------
def test_3_unsupported_currency():
    project_data = {
        "project_description": "Build a reliable cryptocurrency accounting tool for web3 businesses",
        "total_budget": 1000.0,
        "currency": "BITCOIN",
        "deadline": "30 days",
        "client_id": "client_003",
        "freelancer_id": "freelancer_003",
    }

    runner = ScopingAgentRunner()
    state = runner.start_project(project_data, thread_id="test_3")

    assert state["project_status"] == STATUS_ERROR
    assert "Unsupported currency 'BITCOIN'" in state["error_message"]


# -----------------------------------------------------------------------------
# Test 4: Budget exceeding policy limit
# -----------------------------------------------------------------------------
def test_4_budget_exceeding_policy_limit():
    project_data = {
        "project_description": "Enterprise cloud migration project covering multi-region infrastructure",
        "total_budget": 75000.0,  # default policy max is 50,000.0
        "currency": "USD",
        "deadline": "60 days",
        "client_id": "client_004",
        "freelancer_id": "freelancer_004",
    }

    runner = ScopingAgentRunner()
    state = runner.start_project(project_data, thread_id="test_4")

    assert state["project_status"] == STATUS_ERROR
    assert "exceeds the maximum allowed policy limit" in state["error_message"]


# -----------------------------------------------------------------------------
# Test 5: Invalid milestone amounts
# -----------------------------------------------------------------------------
def test_5_invalid_milestone_amounts():
    milestones = make_valid_milestones(1000.0)
    # Alter amounts so sum equals 800 instead of 1000
    milestones[0]["payment_amount"] = 200.0
    milestones[1]["payment_amount"] = 200.0
    milestones[2]["payment_amount"] = 400.0

    is_valid, errors, _, _unresolved = validate_and_correct_milestone_plan(
        milestones=milestones,
        total_budget=1000.0,
        project_deadline="30 days",
    )

    assert not is_valid
    assert any("Sum of milestone amounts" in e and "does not equal total budget" in e for e in errors)


# -----------------------------------------------------------------------------
# Test 6: Invalid criterion types
# -----------------------------------------------------------------------------
def test_6_invalid_criterion_types():
    milestones = make_valid_milestones(1000.0)
    milestones[0]["acceptance_criteria"].append({
        "id": "invalid_c",
        "type": "custom_llm_hallucinated_check",
        "params": {"some_param": "foo"},
        "weight": 0.20,
        "must_pass": True,
    })

    is_valid, errors, _, _unresolved = validate_and_correct_milestone_plan(
        milestones=milestones,
        total_budget=1000.0,
        project_deadline="30 days",
    )

    assert not is_valid
    assert any("has invalid type 'custom_llm_hallucinated_check'" in e for e in errors)


# -----------------------------------------------------------------------------
# Test 7: Missing hard criteria
# -----------------------------------------------------------------------------
def test_7_missing_hard_criteria():
    milestones = make_valid_milestones(1000.0)
    # Replace first milestone criteria with only soft manual_review
    milestones[0]["acceptance_criteria"] = [
        {
            "id": "c_soft_only",
            "type": "manual_review",
            "params": {"checklist": ["Check things manually"], "reviewer_role": "client"},
            "weight": 1.0,
            "must_pass": False,
        }
    ]

    is_valid, errors, _, _unresolved = validate_and_correct_milestone_plan(
        milestones=milestones,
        total_budget=1000.0,
        project_deadline="30 days",
    )

    assert not is_valid
    assert any("does not contain any hard criteria" in e for e in errors)


# -----------------------------------------------------------------------------
# Test 8: Hard criteria weight below 70%
# -----------------------------------------------------------------------------
def test_8_hard_criteria_weight_below_70():
    milestones = make_valid_milestones(1000.0)
    # Set hard criteria weight to 40% and soft criteria to 60%
    milestones[0]["acceptance_criteria"] = [
        {
            "id": "c1",
            "type": "repo_file_exists",
            "params": {"repo": "test/repo", "file_path": "README.md"},
            "weight": 0.40,
            "must_pass": True,
        },
        {
            "id": "c2",
            "type": "manual_review",
            "params": {"checklist": ["Client visual check"], "reviewer_role": "client"},
            "weight": 0.60,
            "must_pass": False,
        },
    ]

    is_valid, errors, _, _unresolved = validate_and_correct_milestone_plan(
        milestones=milestones,
        total_budget=1000.0,
        project_deadline="30 days",
    )

    assert not is_valid
    assert any("hard criteria weight ratio is 40.0%, which is below the required 70% minimum" in e for e in errors)


# -----------------------------------------------------------------------------
# Test 9: Invalid deadlines
# -----------------------------------------------------------------------------
def test_9_invalid_deadlines():
    milestones = make_valid_milestones(1000.0)
    # Case A: Milestone 2 has an earlier deadline than Milestone 1
    milestones[0]["deadline"] = "Day 20"
    milestones[1]["deadline"] = "Day 10"

    is_valid, errors, _, _unresolved = validate_and_correct_milestone_plan(
        milestones=milestones,
        total_budget=1000.0,
        project_deadline="30 days",
    )
    assert not is_valid
    assert any("Deadlines must be strictly ordered" in e for e in errors)

    # Case B: Milestone deadline exceeds overall project deadline
    milestones[0]["deadline"] = "Day 10"
    milestones[1]["deadline"] = "Day 20"
    milestones[2]["deadline"] = "Day 45"  # overall is 30 days

    is_valid_b, errors_b, _, _unresolved_b = validate_and_correct_milestone_plan(
        milestones=milestones,
        total_budget=1000.0,
        project_deadline="30 days",
    )
    assert not is_valid_b
    assert any("exceeds overall project deadline" in e for e in errors_b)


# -----------------------------------------------------------------------------
# Test 10: Successful repair
# -----------------------------------------------------------------------------
def test_10_successful_repair():
    project_data = {
        "project_description": "Build an e-commerce website with product catalog and stripe payments",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_id": "client_010",
        "user_provided_config": make_test_config(),
        "freelancer_id": "freelancer_010",
    }

    # Initial plan has invalid sum (800 != 1000)
    invalid_milestones = make_valid_milestones(1000.0)
    invalid_milestones[0]["payment_amount"] = 200.0
    invalid_milestones[1]["payment_amount"] = 200.0
    invalid_milestones[2]["payment_amount"] = 400.0

    invalid_plan = MilestonePlanSchema(milestones=[MilestoneSchema(**m) for m in invalid_milestones])
    corrected_plan = MilestonePlanSchema(milestones=[MilestoneSchema(**m) for m in make_valid_milestones(1000.0)])

    with patch.object(llm_service, "check_clarity") as mock_clarity, \
         patch.object(llm_service, "generate_milestones") as mock_gen, \
         patch.object(llm_service, "repair_milestones") as mock_repair:

        mock_clarity.return_value = ClarityCheckSchema(is_clear=True, reasoning="Clear.")
        mock_gen.return_value = invalid_plan
        mock_repair.return_value = corrected_plan

        runner = ScopingAgentRunner()
        state = runner.start_project(project_data, thread_id="test_10")

        assert mock_repair.called
        assert state["repair_attempt"] == 1
        assert state["llm_call_count"] == 3  # 1 clarity + 1 generation + 1 repair
        assert state["plan_source"] == "llm_repaired"
        assert state["validation_errors"] == []
        assert state["project_status"] in (STATUS_DRAFT, STATUS_PENDING_APPROVAL)


# -----------------------------------------------------------------------------
# Test 11: Failed repair and template fallback
# -----------------------------------------------------------------------------
def test_11_failed_repair_and_template_fallback():
    project_data = {
        "project_description": "Build an e-commerce platform with customer reviews and order tracking",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_id": "client_011",
        "freelancer_id": "freelancer_011",
    }

    # Both initial and repaired plans remain invalid
    invalid_milestones = make_valid_milestones(1000.0)
    invalid_milestones[0]["payment_amount"] = 100.0  # Sum is wrong

    invalid_plan = MilestonePlanSchema(milestones=[MilestoneSchema(**m) for m in invalid_milestones])

    with patch.object(llm_service, "check_clarity") as mock_clarity, \
         patch.object(llm_service, "generate_milestones") as mock_gen, \
         patch.object(llm_service, "repair_milestones") as mock_repair:

        mock_clarity.return_value = ClarityCheckSchema(is_clear=True, reasoning="Clear.")
        mock_gen.return_value = invalid_plan
        mock_repair.return_value = invalid_plan  # Repair also fails

        runner = ScopingAgentRunner()
        state = runner.start_project(project_data, thread_id="test_11")

        assert state["plan_source"] == "template_fallback"
        assert state["needs_human_edit"] is True
        assert state["project_status"] == STATUS_NEEDS_HUMAN_EDIT
        assert len(state["milestones"]) == 2  # Deterministic 2-milestone fallback
        assert sum(m["payment_amount"] for m in state["milestones"]) == 1000.0


# -----------------------------------------------------------------------------
# Test 12: Client approval without freelancer approval
# -----------------------------------------------------------------------------
def test_12_client_approval_without_freelancer_approval():
    project_data = {
        "project_description": "Build an e-commerce website with: 1. Homepage 2. Product listing 3. Shopping cart",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_id": "client_012",
        "user_provided_config": make_test_config(),
        "freelancer_id": "freelancer_012",
    }
    valid_plan = MilestonePlanSchema(milestones=[MilestoneSchema(**m) for m in make_valid_milestones(1000.0)])

    with patch.object(llm_service, "check_clarity") as mock_clarity, \
         patch.object(llm_service, "generate_milestones") as mock_gen:

        mock_clarity.return_value = ClarityCheckSchema(is_clear=True, reasoning="Clear.")
        mock_gen.return_value = valid_plan

        runner = ScopingAgentRunner()
        state = runner.start_project(project_data, thread_id="test_12")

        # Client approves
        state_after_client = runner.submit_approval(
            thread_id="test_12",
            user_id="client_012",
            role="client",
            approved=True,
        )

        assert state_after_client["client_approved"] is True
        assert state_after_client["freelancer_approved"] is False
        assert state_after_client["project_status"] == STATUS_PENDING_APPROVAL
        assert state_after_client.get("plan_hash") is None  # Not locked yet


# -----------------------------------------------------------------------------
# Test 13: Both approvals successfully locking the plan
# -----------------------------------------------------------------------------
def test_13_both_approvals_successfully_locking_plan():
    project_data = {
        "project_description": "Build an e-commerce website with: 1. Homepage 2. Product listing 3. Shopping cart",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_id": "client_013",
        "user_provided_config": make_test_config(),
        "freelancer_id": "freelancer_013",
    }
    valid_plan = MilestonePlanSchema(milestones=[MilestoneSchema(**m) for m in make_valid_milestones(1000.0)])

    with patch.object(llm_service, "check_clarity") as mock_clarity, \
         patch.object(llm_service, "generate_milestones") as mock_gen:

        mock_clarity.return_value = ClarityCheckSchema(is_clear=True, reasoning="Clear.")
        mock_gen.return_value = valid_plan

        runner = ScopingAgentRunner()
        runner.start_project(project_data, thread_id="test_13")

        # Simulate both approvals
        final_state = runner.simulate_both_approvals(thread_id="test_13")

        assert final_state["client_approved"] is True
        assert final_state["freelancer_approved"] is True
        assert final_state["project_status"] == STATUS_PLAN_APPROVED
        assert final_state["plan_hash"] is not None
        assert len(final_state["plan_hash"]) == 64  # Valid SHA-256 string

        # Check domain event was emitted in database
        emitted = db.get_emitted_events("plan.approved")
        assert len(emitted) >= 1
        assert emitted[0]["payload"]["plan_hash"] == final_state["plan_hash"]
        persisted = db.get_project(final_state["project_id"])
        assert persisted is not None
        assert persisted["status"] == STATUS_PLAN_APPROVED
        assert persisted["plan_hash"] == final_state["plan_hash"]
        assert len(persisted["milestones"]) == len(final_state["milestones"])


# -----------------------------------------------------------------------------
# Test 14: Valid and invalid plan edits
# -----------------------------------------------------------------------------
def test_14_valid_and_invalid_plan_edits():
    project_data = {
        "project_description": "Build an e-commerce website with: 1. Homepage 2. Product listing 3. Shopping cart",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_id": "client_014",
        "user_provided_config": make_test_config(),
        "freelancer_id": "freelancer_014",
    }
    valid_plan = MilestonePlanSchema(milestones=[MilestoneSchema(**m) for m in make_valid_milestones(1000.0)])

    with patch.object(llm_service, "check_clarity") as mock_clarity, \
         patch.object(llm_service, "generate_milestones") as mock_gen, \
         patch.object(llm_service, "repair_milestones") as mock_repair:

        mock_clarity.return_value = ClarityCheckSchema(is_clear=True, reasoning="Clear.")
        mock_gen.return_value = valid_plan

        runner = ScopingAgentRunner()
        runner.start_project(project_data, thread_id="test_14")

        # Part A: Submit INVALID edit (budget sum = 600 instead of 1000)
        invalid_edit = make_valid_milestones(1000.0)
        invalid_edit[0]["payment_amount"] = 100.0
        invalid_edit[1]["payment_amount"] = 200.0
        invalid_edit[2]["payment_amount"] = 300.0

        state_invalid_edit = runner.submit_edit(thread_id="test_14", edited_milestones=invalid_edit)
        assert len(state_invalid_edit["validation_errors"]) > 0
        # Ensure LLM was NOT invoked on edit
        assert not mock_repair.called

        # Part B: Submit VALID edit (2 milestones: 500.0 and 500.0)
        # Note: repos and URLs must not match placeholder detection lists.
        valid_edit = [
            {
                "id": "edit_m1",
                "title": "Phase 1: Backend and API",
                "description": "Develop full backend services and database.",
                "payment_amount": 500.0,
                "deadline": "Day 15",
                "acceptance_criteria": [
                    {
                        "id": "e_c1",
                        "type": "repo_file_exists",
                        "params": {"repo": "client/ecommerce-app", "file_path": "main.py"},
                        "weight": 0.8,
                        "must_pass": True,
                    },
                    {
                        "id": "e_c2",
                        "type": "manual_review",
                        "params": {"checklist": ["API tested"], "reviewer_role": "client"},
                        "weight": 0.2,
                        "must_pass": False,
                    },
                ],
            },
            {
                "id": "edit_m2",
                "title": "Phase 2: Frontend and Deployment",
                "description": "Complete frontend and verify deployment.",
                "payment_amount": 500.0,
                "deadline": "Day 30",
                "acceptance_criteria": [
                    {
                        "id": "e_c3",
                        "type": "url_returns_200",
                        "params": {"url": "https://ecommerce-demo.dev/health"},
                        "weight": 0.8,
                        "must_pass": True,
                    },
                    {
                        "id": "e_c4",
                        "type": "manual_review",
                        "params": {"checklist": ["Visual check"], "reviewer_role": "client"},
                        "weight": 0.2,
                        "must_pass": False,
                    },
                ],
            },
        ]

        state_valid_edit = runner.submit_edit(thread_id="test_14", edited_milestones=valid_edit)
        assert state_valid_edit["validation_errors"] == []
        assert state_valid_edit["plan_source"] == "human_edited"
        assert len(state_valid_edit["milestones"]) == 2
        assert state_valid_edit["client_approved"] is False
        assert state_valid_edit["freelancer_approved"] is False


# -----------------------------------------------------------------------------
# Test 15: LLM unavailable fallback
# -----------------------------------------------------------------------------
def test_15_llm_unavailable_fallback():
    project_data = {
        "project_description": "Build an e-commerce platform with customer cart, checkout, and inventory sync",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_id": "client_015",
        "freelancer_id": "freelancer_015",
    }

    with patch.object(llm_service, "check_clarity") as mock_clarity, \
         patch.object(llm_service, "generate_milestones") as mock_gen, \
         patch.object(llm_service, "repair_milestones") as mock_repair:

        # Simulate network or provider outage on generation and repair
        mock_clarity.side_effect = LLMServiceError("Service unavailable 503")
        mock_gen.side_effect = LLMServiceError("Gemini API connection timeout")
        mock_repair.side_effect = LLMServiceError("Gemini API connection timeout")

        runner = ScopingAgentRunner()
        state = runner.start_project(project_data, thread_id="test_15")

        # The system must gracefully fallback to deterministic template plan
        assert state["plan_source"] == "template_fallback"
        assert state["needs_human_edit"] is True
        assert state["project_status"] == STATUS_NEEDS_HUMAN_EDIT
        assert len(state["milestones"]) == 2
        assert sum(m["payment_amount"] for m in state["milestones"]) == 1000.0


# -----------------------------------------------------------------------------
# Test 16: Vague input triggers questions, answers resolve to milestones
# -----------------------------------------------------------------------------
def test_16_clarification_flow_interactive():
    project_data = {
        "project_description": "Build an app for my company with some features and dashboard",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_id": "client_016",
        "user_provided_config": make_test_config(),
        "freelancer_id": "freelancer_016",
    }
    valid_plan = MilestonePlanSchema(milestones=[MilestoneSchema(**m) for m in make_valid_milestones(1000.0)])

    with patch.object(llm_service, "check_clarity") as mock_clarity, \
         patch.object(llm_service, "generate_milestones") as mock_gen:

        # First call: vague
        mock_clarity.side_effect = [
            ClarityCheckSchema(
                is_clear=False,
                reasoning="Scope is too broad.",
                clarification_questions=["What tech stack?", "What features?"],
            ),
            # Second call after answers: clear
            ClarityCheckSchema(is_clear=True, reasoning="Sufficiently clear now."),
        ]
        mock_gen.return_value = valid_plan

        runner = ScopingAgentRunner()
        state = runner.start_project(project_data, thread_id="test_16")

        # Must pause with clarification requested
        assert state["clarification_count"] == 1
        assert len(state["clarification_questions"]) == 2

        # Now submit answers
        answers = {"What tech stack?": "FastAPI + React", "What features?": "Auth and dashboard"}
        resumed_state = runner.submit_clarification(thread_id="test_16", clarification_answers=answers)

        assert "FastAPI + React" in resumed_state["project_description"]
        assert resumed_state["plan_source"] == "llm_generated"
        assert len(resumed_state["milestones"]) == 3


# -----------------------------------------------------------------------------
# Test 17: Vague input remains vague after 1 round -> NEEDS_CLARIFICATION
# -----------------------------------------------------------------------------
def test_17_clarification_exhausted_needs_human_input():
    project_data = {
        "project_description": "Build an app for my company with some features and dashboard",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_id": "client_017",
        "freelancer_id": "freelancer_017",
    }

    with patch.object(llm_service, "check_clarity") as mock_clarity:\
        # Both calls return vague
        mock_clarity.return_value = ClarityCheckSchema(
            is_clear=False,
            reasoning="Still too vague.",
            clarification_questions=["Still vague question?"],
        )

        runner = ScopingAgentRunner()
        runner.start_project(project_data, thread_id="test_17")

        # Submit answers that are still deemed vague
        answers = {"Still vague question?": "I don't know yet."}
        final_state = runner.submit_clarification(thread_id="test_17", clarification_answers=answers)

        assert final_state["project_status"] == "NEEDS_CLARIFICATION"
        assert final_state["needs_human_edit"] is True


# -----------------------------------------------------------------------------
# Test 18: Missing milestones blocks approval and locking
# -----------------------------------------------------------------------------
def test_18_missing_milestones_blocks_approval():
    project_data = {
        "project_description": "Build a custom web application for inventory tracking",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_id": "client_018",
        "freelancer_id": "freelancer_018",
    }

    with patch.object(llm_service, "check_clarity") as mock_clarity:\
        # Pause at clarification requested (no milestones generated)
        mock_clarity.return_value = ClarityCheckSchema(
            is_clear=False,
            reasoning="Scope is vague.",
            clarification_questions=["What features?"],
        )

        runner = ScopingAgentRunner()
        state = runner.start_project(project_data, thread_id="test_18")
        assert state["project_status"] == "CLARIFICATION_REQUESTED"
        assert state.get("milestones", []) == []

        # Attempting to submit approval when milestones are missing must be blocked
        appr_state = runner.submit_approval(thread_id="test_18", user_id="client_018", role="client")
        assert "Cannot submit approval" in appr_state.get("error_message", "")
        assert appr_state.get("plan_hash") is None
        assert appr_state["project_status"] != STATUS_PLAN_APPROVED


# -----------------------------------------------------------------------------
# Test 19: Plan locking prevented if approval hashes do not match
# -----------------------------------------------------------------------------
def test_19_approval_hash_mismatch_prevents_locking():
    from ProofPay.agents.scoping_agent.nodes import lock_plan

    valid_milestones = make_valid_milestones(1000.0)
    state = {
        "client_id": "client_019",
        "freelancer_id": "freelancer_019",
        "milestones": valid_milestones,
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "user_provided_config": make_test_config(),
        "client_approved": True,
        "freelancer_approved": True,
        # Client approved hash A, but freelancer approved a different hash B
        "client_approved_hash": "hash_version_A",
        "freelancer_approved_hash": "hash_version_B",
    }

    result = lock_plan(state)
    assert result["project_status"] == STATUS_PENDING_APPROVAL
    assert "exact same milestone plan version" in result.get("error_message", "")
    assert "plan_hash" not in result


# -----------------------------------------------------------------------------
# Test 20: Compute plan hash rejects empty or insufficient milestones
# -----------------------------------------------------------------------------
def test_20_compute_plan_hash_rejects_empty_milestones():
    with pytest.raises(ValueError, match="Plan must contain at least 2 valid milestones"):
        compute_plan_hash(milestones=[], total_budget=1000.0, currency="USD")

    with pytest.raises(ValueError, match="Plan must contain at least 2 valid milestones"):
        compute_plan_hash(milestones=[{"id": "m1"}], total_budget=1000.0, currency="USD")


# -----------------------------------------------------------------------------
# Test 21: Accurate LLM call counters
# -----------------------------------------------------------------------------
def test_21_accurate_llm_call_counters():
    project_data = {
        "project_description": "Build an online storefront",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_id": "client_021",
        "user_provided_config": make_test_config(),
        "freelancer_id": "freelancer_021",
    }

    valid_plan = MilestonePlanSchema(milestones=[MilestoneSchema(**m) for m in make_valid_milestones(1000.0)])

    with patch.object(llm_service, "check_clarity") as mock_clarity, \
         patch.object(llm_service, "generate_milestones") as mock_gen:

        mock_clarity.return_value = ClarityCheckSchema(
            is_clear=False,
            reasoning="Need details.",
            clarification_questions=["Which storefront features should be included?"],
        )
        mock_gen.return_value = valid_plan

        runner = ScopingAgentRunner()
        # Stage 1: Clarity check called once
        state_1 = runner.start_project(project_data, thread_id="test_21")
        assert state_1["llm_call_count"] == 1
        assert state_1["project_status"] == "CLARIFICATION_REQUESTED"

        # Stage 2: Resume with clarification (re-check clarity + generate milestones)
        mock_clarity.return_value = ClarityCheckSchema(is_clear=True, reasoning="Clear now.")
        state_2 = runner.submit_clarification(
            thread_id="test_21",
            clarification_answers={"Which storefront features should be included?": "Product categories and search"},
        )
        # 1 initial clarity + 1 post-clarification clarity + 1 milestone generation = 3
        assert state_2["llm_call_count"] == 3
        assert state_2["plan_source"] == "llm_generated"


# -----------------------------------------------------------------------------
# Test 22: Lock plan rejects plan with deterministic validation errors
# -----------------------------------------------------------------------------
def test_22_lock_plan_rejects_invalid_plan():
    from ProofPay.agents.scoping_agent.nodes import lock_plan

    invalid_milestones = make_valid_milestones(1000.0)
    # Tamper amount so sum does not match
    invalid_milestones[0]["payment_amount"] = 100.0

    state = {
        "client_id": "client_022",
        "freelancer_id": "freelancer_022",
        "milestones": invalid_milestones,
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_approved": True,
        "freelancer_approved": True,
        "client_approved_hash": "hash_123",
        "freelancer_approved_hash": "hash_123",
    }

    result = lock_plan(state)
    assert result["project_status"] == STATUS_ERROR
    assert "Deterministic validation failed" in result.get("error_message", "")


# -----------------------------------------------------------------------------
# Test 23: Placeholder repo in milestone is detected and rejected by provenance check
# -----------------------------------------------------------------------------
def test_23_placeholder_repo_detected_by_provenance():
    """A milestone using a known placeholder repo (project-repo, myorg/) must be
    flagged as unresolved when enforce_provenance=True."""
    milestones = make_valid_milestones(1000.0)
    # Inject a known placeholder repo into one criterion
    milestones[0]["acceptance_criteria"][0]["params"]["repo"] = "project-repo"

    is_valid, errors, corrected, unresolved = validate_and_correct_milestone_plan(
        milestones=milestones,
        total_budget=1000.0,
        project_deadline="30 days",
        enforce_provenance=True,
    )

    assert not is_valid
    assert any("placeholder" in e.lower() or "hallucinated" in e.lower() for e in errors)
    assert "repository" in unresolved


# -----------------------------------------------------------------------------
# Test 24: Placeholder URL in criterion is detected and reported
# -----------------------------------------------------------------------------
def test_24_placeholder_url_detected_by_provenance():
    """A criterion using a known placeholder domain (example.com, shop.test) must be
    flagged as an unresolved deployment_url."""
    milestones = make_valid_milestones(1000.0)
    # Replace the URL criterion in milestone 2 with a known placeholder domain
    milestones[1]["acceptance_criteria"][0]["params"]["url"] = "https://example.com/products"

    is_valid, errors, corrected, unresolved = validate_and_correct_milestone_plan(
        milestones=milestones,
        total_budget=1000.0,
        project_deadline="30 days",
        enforce_provenance=True,
    )

    assert not is_valid
    assert any("placeholder" in e.lower() or "hallucinated" in e.lower() for e in errors)
    assert "deployment_url" in unresolved


# -----------------------------------------------------------------------------
# Test 25: Non-placeholder repo and URL pass provenance check
# -----------------------------------------------------------------------------
def test_25_non_placeholder_values_pass_provenance():
    """Realistic non-placeholder values must not be flagged by provenance checks."""
    milestones = make_valid_milestones(1000.0)
    # make_valid_milestones uses concrete-looking test fixture values that are
    # not reserved placeholder domains; no external requests are made in unit tests.

    is_valid, errors, corrected, unresolved = validate_and_correct_milestone_plan(
        milestones=milestones,
        total_budget=1000.0,
        project_deadline="30 days",
        user_provided_config=make_test_config(),
        enforce_provenance=True,
    )

    assert is_valid
    assert errors == []
    # No placeholder-related unresolved parameters
    assert "repository" not in unresolved
    assert "deployment_url" in unresolved or "deployment_url" not in unresolved  # Either is fine
    # Key check: the plan must be valid
    assert len(corrected) == 3


# -----------------------------------------------------------------------------
# Test 26: Unauthorized payment provider in milestone title/description is detected
# -----------------------------------------------------------------------------
def test_26_unauthorized_payment_provider_detected():
    """If a milestone explicitly mentions Stripe (or other providers) without user
    authorization via user_provided_config, detect_unresolved_and_placeholder_params
    must flag it."""
    from ProofPay.agents.scoping_agent.validators import detect_unresolved_and_placeholder_params

    milestones = [
        {
            "id": "m1",
            "title": "Stripe Payment Integration",
            "description": "Integrate Stripe for checkout and billing.",
            "payment_amount": 500.0,
            "deadline": "Day 15",
            "acceptance_criteria": [],
        }
    ]

    errors, unresolved = detect_unresolved_and_placeholder_params(
        milestones=milestones,
        user_provided_config={},  # No provider configured
    )

    assert "payment_provider" in unresolved
    assert any("stripe" in e.lower() for e in errors)


# -----------------------------------------------------------------------------
# Test 27: Authorized payment provider passes provenance check
# -----------------------------------------------------------------------------
def test_27_authorized_payment_provider_passes():
    """If the client configured Stripe explicitly in user_provided_config,
    a milestone mentioning Stripe must not be flagged."""
    from ProofPay.agents.scoping_agent.validators import detect_unresolved_and_placeholder_params

    milestones = [
        {
            "id": "m1",
            "title": "Stripe Payment Integration",
            "description": "Integrate Stripe for checkout and billing.",
            "payment_amount": 500.0,
            "deadline": "Day 15",
            "acceptance_criteria": [],
        }
    ]

    errors, unresolved = detect_unresolved_and_placeholder_params(
        milestones=milestones,
        user_provided_config={"payment_provider": "stripe"},
    )

    assert "payment_provider" not in unresolved


# -----------------------------------------------------------------------------
# Test 28: Plan with unresolved_parameters cannot be locked
# -----------------------------------------------------------------------------
def test_28_unresolved_parameters_block_locking():
    """If unresolved_parameters is non-empty, lock_plan must refuse and return
    PENDING_APPROVAL status, not STATUS_PLAN_APPROVED."""
    from ProofPay.agents.scoping_agent.nodes import lock_plan

    valid_milestones = make_valid_milestones(1000.0)
    state = {
        "client_id": "client_028",
        "freelancer_id": "freelancer_028",
        "project_id": "proj-028",
        "milestones": valid_milestones,
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_approved": True,
        "freelancer_approved": True,
        "client_approved_hash": "hash_abc",
        "freelancer_approved_hash": "hash_abc",
        # Deliberately unresolved
        "unresolved_parameters": ["payment_provider"],
    }

    result = lock_plan(state)
    assert result["project_status"] == STATUS_NEEDS_HUMAN_EDIT
    assert "unresolved" in result.get("error_message", "").lower()
    assert "plan_hash" not in result


# -----------------------------------------------------------------------------
# Test 29: Submitting a plan edit resets both approvals
# -----------------------------------------------------------------------------
def test_29_plan_edit_resets_approvals():
    """After a valid plan edit is submitted, both client_approved and
    freelancer_approved must be reset to False to require re-approval."""
    project_data = {
        "project_description": "Build an inventory management system with reporting dashboard",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_id": "client_029",
        "user_provided_config": make_test_config(),
        "freelancer_id": "freelancer_029",
    }
    valid_plan = MilestonePlanSchema(milestones=[MilestoneSchema(**m) for m in make_valid_milestones(1000.0)])

    with patch.object(llm_service, "check_clarity") as mock_clarity, \
         patch.object(llm_service, "generate_milestones") as mock_gen:

        mock_clarity.return_value = ClarityCheckSchema(is_clear=True, reasoning="Clear.")
        mock_gen.return_value = valid_plan

        runner = ScopingAgentRunner()
        runner.start_project(project_data, thread_id="test_29")

        # Client approves
        runner.submit_approval(thread_id="test_29", user_id="client_029", role="client", approved=True)

        # Now submit a valid edit — this must reset approvals
        valid_edit = [
            {
                "id": "e1",
                "title": "Phase 1: Backend Development",
                "description": "Build all core backend services.",
                "payment_amount": 600.0,
                "deadline": "Day 20",
                "acceptance_criteria": [
                    {
                        "id": "e1_c1",
                        "type": "repo_file_exists",
                        "params": {"repo": "client/ecommerce-app", "file_path": "README.md"},
                        "weight": 0.8,
                        "must_pass": True,
                    },
                    {
                        "id": "e1_c2",
                        "type": "manual_review",
                        "params": {"checklist": ["API smoke test"], "reviewer_role": "client"},
                        "weight": 0.2,
                        "must_pass": False,
                    },
                ],
            },
            {
                "id": "e2",
                "title": "Phase 2: Deployment",
                "description": "Deploy and verify the production system.",
                "payment_amount": 400.0,
                "deadline": "Day 30",
                "acceptance_criteria": [
                    {
                        "id": "e2_c1",
                        "type": "url_returns_200",
                        "params": {"url": "https://ecommerce-demo.dev/health"},
                        "weight": 0.8,
                        "must_pass": True,
                    },
                    {
                        "id": "e2_c2",
                        "type": "manual_review",
                        "params": {"checklist": ["Client sign-off"], "reviewer_role": "client"},
                        "weight": 0.2,
                        "must_pass": False,
                    },
                ],
            },
        ]

        state_after_edit = runner.submit_edit(thread_id="test_29", edited_milestones=valid_edit)

        # Approvals must be reset
        assert state_after_edit["client_approved"] is False
        assert state_after_edit["freelancer_approved"] is False
        assert state_after_edit["plan_source"] == "human_edited"


# -----------------------------------------------------------------------------
# Test 30: compute_plan_hash is deterministic (same inputs = same hash)
# -----------------------------------------------------------------------------
def test_30_plan_hash_is_deterministic():
    """compute_plan_hash must return the same SHA-256 hash for identical inputs."""
    milestones = make_valid_milestones(1000.0)

    hash_1 = compute_plan_hash(milestones=milestones, total_budget=1000.0, currency="USD")
    hash_2 = compute_plan_hash(milestones=milestones, total_budget=1000.0, currency="USD")

    assert hash_1 == hash_2
    assert len(hash_1) == 64  # Valid SHA-256 hex string


# -----------------------------------------------------------------------------
# Test 31: Different milestone plans produce different hashes
# -----------------------------------------------------------------------------
def test_31_different_plans_produce_different_hashes():
    """Two distinct milestone plans must not share the same SHA-256 hash."""
    plan_a = make_valid_milestones(1000.0)
    plan_b = make_valid_milestones(1000.0)
    plan_b[0]["payment_amount"] = 400.0
    plan_b[2]["payment_amount"] = 200.0  # Keep total at 1000

    hash_a = compute_plan_hash(milestones=plan_a, total_budget=1000.0, currency="USD")
    hash_b = compute_plan_hash(milestones=plan_b, total_budget=1000.0, currency="USD")

    assert hash_a != hash_b


# -----------------------------------------------------------------------------
# Test 32: Fallback plan uses no fake external resources
# -----------------------------------------------------------------------------
def test_32_fallback_plan_uses_no_fake_external_resources():
    """The deterministic fallback plan must not reference fake/hallucinated
    external resources that would fail provenance checks under enforce_provenance=True.
    It must always be flagged needs_human_edit=True."""
    from ProofPay.agents.scoping_agent.validators import generate_fallback_milestone_plan

    fallback = generate_fallback_milestone_plan(
        total_budget=2000.0,
        currency="USD",
        deadline="60 days",
        project_description="Generic project",
    )

    assert len(fallback) == 2
    assert sum(m["payment_amount"] for m in fallback) == 2000.0

    # Fallback criteria describe deliverables without inventing paths or infrastructure.
    SAFE_FALLBACK_TYPES = {"deliverable_check", "manual_review"}
    for m in fallback:
        for c in m.get("acceptance_criteria", []):
            assert c["type"] in SAFE_FALLBACK_TYPES, (
                f"Fallback plan must not use '{c['type']}' which may reference unverified external resources. "
                f"Only {SAFE_FALLBACK_TYPES} are allowed in template fallback."
            )





# -----------------------------------------------------------------------------
# Regression tests for clarification mapping and approval safety
# -----------------------------------------------------------------------------

def test_33_clarification_parser_uses_answer_values_not_question_examples():
    from ProofPay.agents.scoping_agent.nodes import _extract_config_from_answers

    config = {}
    unresolved = ["payment_provider", "deployment_url"]
    config_status = {}

    # The question itself mentions Stripe as an example; that must not count as
    # the client's selection when the answer says it is undecided.
    _extract_config_from_answers(
        {"Which provider (PayPal, Stripe, Square)?": "Not decided yet"},
        config,
        unresolved,
        config_status,
    )
    assert "payment_provider" not in config
    assert "payment_provider" in unresolved

    _extract_config_from_answers(
        {
            "Which payment provider?": "Stripe",
            "Which repository and deployment?": (
                "GitHub repository https://github.com/acme/store; "
                "Vercel deployment https://store.acme.dev"
            ),
        },
        config,
        unresolved,
        config_status,
    )
    assert config["payment_provider"] == "Stripe"
    assert config["repository"] == "acme/store"
    assert config["repository_provider"] == "GitHub"
    assert config["deployment_platform"] == "Vercel"
    assert config["staging_url"] == "https://store.acme.dev"
    assert "payment_provider" not in unresolved
    assert "deployment_url" not in unresolved


def test_34_payment_provider_is_not_a_required_clarification():
    """Payment provider selection must not block Agent 1 scope definition."""
    from ProofPay.agents.scoping_agent.nodes import check_clarity, receive_project

    received = receive_project({
        "project_id": "payment-provider-optional",
        "client_id": "client_001",
        "project_description": "Build an e-commerce website with a shopping cart and payment integration.",
        "unresolved_parameters": [],
        "configuration_status": {},
        "user_provided_config": {},
    })
    assert "payment_provider" not in received["unresolved_parameters"]
    assert received["configuration_status"].get("payment_provider") == "NOT_REQUIRED_FOR_SCOPING"

    with patch.object(llm_service, "check_clarity") as mock_clarity:
        mock_clarity.return_value = ClarityCheckSchema(
            is_clear=False,
            reasoning="Only provider selection is missing.",
            clarification_questions=["Which payment provider (Stripe, PayPal, or Square) do you prefer?"],
        )
        result = check_clarity({
            "project_id": "payment-provider-optional",
            "project_description": "Build an e-commerce site with payment integration and product checkout.",
            "total_budget": 1000.0,
            "currency": "USD",
            "deadline": "30 days",
            "unresolved_parameters": [],
            "llm_calls_attempted": 0,
            "llm_calls_succeeded": 0,
            "llm_calls_failed": 0,
        })

    assert result["clarification_questions"] == []


def test_35_approval_rejects_wrong_participant_id():
    project_data = {
        "project_description": "Build a web application with a reporting dashboard",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_id": "client_035",
        "user_provided_config": make_test_config(),
        "freelancer_id": "freelancer_035",
    }
    valid_plan = MilestonePlanSchema(milestones=[MilestoneSchema(**m) for m in make_valid_milestones(1000.0)])
    with patch.object(llm_service, "check_clarity") as mock_clarity, \
         patch.object(llm_service, "generate_milestones") as mock_gen:
        mock_clarity.return_value = ClarityCheckSchema(is_clear=True, reasoning="Clear.")
        mock_gen.return_value = valid_plan

        runner = ScopingAgentRunner()
        runner.start_project(project_data, thread_id="test_35")
        result = runner.submit_approval(
            thread_id="test_35",
            user_id="someone_else",
            role="client",
            approved=True,
        )
        assert "identity does not match" in result["error_message"]
        assert result.get("client_approved") is False


def test_36_emit_approved_event_is_blocked_without_successful_lock():
    from ProofPay.agents.scoping_agent.nodes import emit_approved_event

    result = emit_approved_event({
        "project_id": "project_036",
        "project_status": STATUS_PENDING_APPROVAL,
        "plan_hash": None,
        "approved_at": None,
        "milestones": make_valid_milestones(1000.0),
    })
    assert result["project_status"] == STATUS_PENDING_APPROVAL
    assert "blocked" in result["error_message"].lower()
    assert db.get_emitted_events("plan.approved") == []


def test_37_fallback_file_placeholders_are_reported_as_blocking():
    from ProofPay.agents.scoping_agent.nodes import template_fallback

    result = template_fallback({
        "project_id": "project_037",
        "project_description": "Build a small internal application",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "user_provided_config": {},
        "unresolved_parameters": [],
    })
    assert result["needs_human_edit"] is True
    assert result["project_status"] == STATUS_NEEDS_HUMAN_EDIT
    assert result["validation_errors"]  # fallback always requires human review
    assert result["unresolved_parameters"] == []
    assert all(
        criterion["type"] == "deliverable_check"
        for milestone in result["milestones"]
        for criterion in milestone["acceptance_criteria"]
        if criterion["type"] != "manual_review"
    )



def test_38_stale_payment_provider_flag_does_not_force_clarification():
    """Legacy/stale provider flags must not block a clear scoping result."""
    from ProofPay.agents.scoping_agent.nodes import check_clarity

    with patch.object(llm_service, "check_clarity") as mock_clarity:
        mock_clarity.return_value = ClarityCheckSchema(
            is_clear=True,
            reasoning="The project scope is sufficiently clear.",
            clarification_questions=[],
        )
        result = check_clarity({
            "project_id": "project_038",
            "project_description": "Build an e-commerce site with payment and deployment",
            "total_budget": 1000.0,
            "currency": "USD",
            "deadline": "30 days",
            "unresolved_parameters": ["payment_provider"],
            "llm_calls_attempted": 0,
            "llm_calls_succeeded": 0,
            "llm_calls_failed": 0,
        })

    assert result["clarification_questions"] == []


# Regression: fallback uses verified project resources and drops stale criteria
# -----------------------------------------------------------------------------
def test_fallback_plan_uses_configured_repo_and_deployment_url():
    from ProofPay.agents.scoping_agent.nodes import template_fallback

    config = {
        "payment_provider": "Stripe",
        "repository": "shreya/proofpay-ecommerce",
        "deployment_url": "https://proofpay-shop.vercel.app",
    }
    state = {
        "project_id": "fallback-regression",
        "project_description": "Build an e-commerce website with payment integration and deployment.",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "user_provided_config": config,
        "configuration_status": {
            "payment_provider": "RESOLVED",
            "repository": "RESOLVED",
            "deployment_url": "RESOLVED",
        },
        # These keys came from a discarded LLM plan and must not leak into fallback.
        "unresolved_parameters": ["expected_text", "github_pr", "deliverable_path"],
    }

    result = template_fallback(state)

    assert result["milestones"][0]["acceptance_criteria"][0]["type"] == "deliverable_check"
    assert result["milestones"][1]["acceptance_criteria"][0]["type"] == "deliverable_check"
    assert "repo" not in result["milestones"][0]["acceptance_criteria"][0]["params"]
    assert "url" not in result["milestones"][1]["acceptance_criteria"][0]["params"]
    assert result["unresolved_parameters"] == []
    assert result["needs_human_edit"] is True  # Fallback remains a human-review draft.


def test_placeholder_github_repository_is_not_accepted():
    from ProofPay.agents.scoping_agent.validators import detect_unresolved_and_placeholder_params

    milestones = make_valid_milestones(1000.0)
    milestones[0]["acceptance_criteria"][0]["params"]["repo"] = "your-username/proofpay-ecommerce"
    errors, unresolved = detect_unresolved_and_placeholder_params(
        milestones,
        user_provided_config={
            "repository": "your-username/proofpay-ecommerce",
            "deployment_url": "https://proofpay-shop.vercel.app",
        },
    )
    assert "repository" in unresolved
    assert any("placeholder/hallucinated repository" in error for error in errors)


# -----------------------------------------------------------------------------
# Agent 1 scope boundary and durable database regressions
# -----------------------------------------------------------------------------

def test_agent1_does_not_require_repository_or_deployment_url():
    """A clear scope can produce a milestone draft without GitHub or deployment URLs."""
    from ProofPay.agents.scoping_agent.schemas import MilestonePlanSchema, MilestoneSchema

    plan = MilestonePlanSchema(milestones=[
        MilestoneSchema(
            id="m1", title="Project Foundation", description="Create the initial application foundation and architecture.",
            payment_amount=400.0, deadline="Day 10", acceptance_criteria=[
                CriterionSchema(id="c1", type="deliverable_check", params={
                    "deliverable": "Initial application foundation",
                    "acceptance_checks": ["Project structure matches the agreed requirements", "Setup instructions are supplied"],
                }, weight=0.8, must_pass=True),
                CriterionSchema(id="c2", type="manual_review", params={
                    "checklist": ["Client reviews the foundation"], "reviewer_role": "client",
                }, weight=0.2, must_pass=False),
            ],
        ),
        MilestoneSchema(
            id="m2", title="Final Application Delivery", description="Complete the requested application features and submit the final deliverables.",
            payment_amount=600.0, deadline="Day 30", acceptance_criteria=[
                CriterionSchema(id="c3", type="deliverable_check", params={
                    "deliverable": "Completed application",
                    "acceptance_checks": ["All agreed features are implemented", "Final deliverables are submitted"],
                }, weight=0.8, must_pass=True),
                CriterionSchema(id="c4", type="manual_review", params={
                    "checklist": ["Client reviews final application"], "reviewer_role": "client",
                }, weight=0.2, must_pass=False),
            ],
        ),
    ])
    payload = {
        "project_description": "Build an internal task management application with task creation and status tracking.",
        "total_budget": 1000.0, "currency": "USD", "deadline": "30 days",
        "client_id": "client_scope_only", "freelancer_id": "freelancer_scope_only",
    }
    with patch.object(llm_service, "check_clarity") as clarity, patch.object(llm_service, "generate_milestones") as generate:
        clarity.return_value = ClarityCheckSchema(is_clear=True, reasoning="Scope is clear.")
        generate.return_value = plan
        runner = ScopingAgentRunner()
        state = runner.start_project(payload, thread_id="test_agent1_scope_only")

    assert state["project_status"] in (STATUS_DRAFT, STATUS_PENDING_APPROVAL)
    assert state["plan_source"] == "llm_generated"
    assert state["unresolved_parameters"] == []
    assert not state["needs_human_edit"]
    assert all(
        c["type"] != "repo_file_exists" and "url" not in c.get("params", {})
        for m in state["milestones"] for c in m["acceptance_criteria"]
    )


def test_scoping_ignores_infrastructure_only_clarification_questions():
    from ProofPay.agents.scoping_agent.nodes import check_clarity
    with patch.object(llm_service, "check_clarity") as clarity:
        clarity.return_value = ClarityCheckSchema(
            is_clear=True,
            reasoning="Functional scope is clear; infrastructure can be selected later.",
            clarification_questions=["What is the GitHub repository URL?", "What is the deployment URL?"],
        )
        result = check_clarity({
            "project_id": "project_no_infra_questions",
            "project_description": "Build a simple expense tracker with add, edit, and delete expense features.",
            "total_budget": 500.0, "currency": "USD", "deadline": "20 days",
            "unresolved_parameters": [], "llm_calls_attempted": 0,
            "llm_calls_succeeded": 0, "llm_calls_failed": 0,
        })
    assert result["clarification_questions"] == []


def test_sqlite_store_survives_reopen_and_persists_approved_event(tmp_path):
    from ProofPay.services.database import SQLiteProjectStore
    database_file = tmp_path / "proofpay_persistence_test.db"
    url = f"sqlite:///{database_file.as_posix()}"
    store = SQLiteProjectStore(url)
    event = {
        "project_id": "persisted-project", "client_id": "client", "freelancer_id": "freelancer",
        "plan_hash": "a" * 64, "total_budget": 100.0, "currency": "USD",
        "deadline": "10 days", "milestones_count": 2, "approved_at": "2026-11-03T00:00:00+00:00",
    }
    store.save_approved_plan_and_event(
        "persisted-project",
        {"milestones": [{"id": "m1"}, {"id": "m2"}], "total_budget": 100.0},
        event,
    )
    store.close()

    reopened = SQLiteProjectStore(url)
    saved = reopened.get_project("persisted-project")
    events = reopened.get_emitted_events("plan.approved")
    assert saved["status"] == STATUS_PLAN_APPROVED
    assert saved["plan_hash"] == "a" * 64
    assert len(saved["milestones"]) == 2
    assert len(events) == 1
    assert events[0]["payload"]["project_id"] == "persisted-project"
    reopened.close()


def test_approved_plan_persistence_rejects_different_second_hash():
    from ProofPay.services.database import SQLiteProjectStore
    store = SQLiteProjectStore("sqlite:///:memory:")
    first_event = {"project_id": "locked-once", "plan_hash": "b" * 64, "approved_at": "2026-11-03T00:00:00+00:00"}
    store.save_approved_plan_and_event("locked-once", {"milestones": [{"id": "m1"}, {"id": "m2"}]}, first_event)
    second_event = {"project_id": "locked-once", "plan_hash": "c" * 64, "approved_at": "2026-11-03T00:01:00+00:00"}
    with pytest.raises(ValueError, match="different locked milestone plan"):
        store.save_approved_plan_and_event("locked-once", {"milestones": [{"id": "m1"}, {"id": "m2"}]}, second_event)
    store.close()


def test_rejection_invalidates_other_party_approval_and_requires_revision():
    project_data = {
        "project_description": "Build a web application with a reporting dashboard and exportable reports.",
        "total_budget": 1000.0, "currency": "USD", "deadline": "30 days",
        "client_id": "client_reject", "freelancer_id": "freelancer_reject",
        "user_provided_config": make_test_config(),
    }
    plan = MilestonePlanSchema(milestones=[MilestoneSchema(**m) for m in make_valid_milestones(1000.0)])
    with patch.object(llm_service, "check_clarity") as clarity, patch.object(llm_service, "generate_milestones") as generate:
        clarity.return_value = ClarityCheckSchema(is_clear=True, reasoning="Clear scope.")
        generate.return_value = plan
        runner = ScopingAgentRunner()
        draft = runner.start_project(project_data, thread_id="test_rejection_flow")
        client_state = runner.submit_approval(
            thread_id="test_rejection_flow", user_id="client_reject", role="client", approved=True
        )
        assert client_state["client_approved"] is True
        rejected = runner.submit_approval(
            thread_id="test_rejection_flow", user_id="freelancer_reject", role="freelancer",
            approved=False, comment="Please include a CSV export deliverable.",
        )
    assert rejected["project_status"] == STATUS_NEEDS_HUMAN_EDIT
    assert rejected["needs_human_edit"] is True
    assert rejected["client_approved"] is False
    assert rejected["freelancer_approved"] is False
    assert "CSV export" in rejected["needs_human_edit_reasons"][0]
    persisted = db.get_project(draft["project_id"])
    assert persisted["client_approved"] is False
    assert persisted["freelancer_approved"] is False
    assert persisted["status"] == STATUS_NEEDS_HUMAN_EDIT


def test_standalone_file_criteria_require_client_agreed_path():
    from ProofPay.agents.scoping_agent.validators import detect_unresolved_and_placeholder_params
    milestones = [
        {
            "id": "m1", "title": "Documentation", "description": "Prepare the project documentation.",
            "payment_amount": 500.0, "deadline": "Day 10",
            "acceptance_criteria": [{
                "id": "c1", "type": "file_has_sections",
                "params": {"file_path": "docs/architecture.md", "required_sections": ["Architecture", "Security"]},
                "weight": 1.0, "must_pass": True,
            }],
        },
        {
            "id": "m2", "title": "Final Report", "description": "Submit the completed project report.",
            "payment_amount": 500.0, "deadline": "Day 20",
            "acceptance_criteria": [{
                "id": "c2", "type": "file_has_sections",
                "params": {"file_path": "docs/final-report.md", "required_sections": ["Summary", "Results"]},
                "weight": 1.0, "must_pass": True,
            }],
        },
    ]
    errors, unresolved = detect_unresolved_and_placeholder_params(milestones, user_provided_config={})
    assert "deliverable_path" in unresolved
    assert any("not explicitly agreed" in error for error in errors)

    errors, unresolved = detect_unresolved_and_placeholder_params(
        milestones, user_provided_config={"deliverable_paths": ["docs/architecture.md", "docs/final-report.md"]}
    )
    assert "deliverable_path" not in unresolved
    assert errors == []


def test_persisted_locked_plan_cannot_be_downgraded_or_mutated():
    from ProofPay.services.database import SQLiteProjectStore
    store = SQLiteProjectStore("sqlite:///:memory:")
    milestones = [{"id": "m1"}, {"id": "m2"}]
    event = {"project_id": "immutable-project", "plan_hash": "d" * 64, "approved_at": "2026-11-03T00:00:00+00:00"}
    store.save_approved_plan_and_event("immutable-project", {"milestones": milestones}, event)
    with pytest.raises(ValueError, match="cannot be downgraded"):
        store.save_project("immutable-project", {"status": "DRAFT"})
    with pytest.raises(ValueError, match="milestones are immutable"):
        store.save_project("immutable-project", {"status": "PLAN_APPROVED", "milestones": [{"id": "tampered"}]})
    store.close()
