"""Focused tests for Gemini response parsing, milestone generation, and repair flow.

Includes:
1. Unit and integration tests with mocked LLM responses (deterministic, offline).
2. Live Gemini API execution test (enabled when GOOGLE_API_KEY is present).
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

from ProofPay.agents.scoping_agent.schemas import (
    ClarityCheckSchema,
    MilestonePlanSchema,
    MilestoneSchema,
    CriterionSchema,
)
from ProofPay.agents.scoping_agent.state import (
    STATUS_DRAFT,
    STATUS_PENDING_APPROVAL,
    STATUS_NEEDS_HUMAN_EDIT,
)
from ProofPay.agents.scoping_agent.validators import (
    validate_and_correct_milestone_plan,
)
from ProofPay.agents.scoping_agent.graph import ScopingAgentRunner
from ProofPay.agents.scoping_agent.nodes import _extract_config_from_answers
from ProofPay.agents.scoping_agent.prompts import (
    format_verified_config_documentation,
    GENERATE_MILESTONES_PROMPT,
    REPAIR_PLAN_PROMPT,
)
from ProofPay.services.llm_service import llm_service, LLMServiceError
from ProofPay.services.database import db
from ProofPay.services.audit_service import audit_service


@pytest.fixture(autouse=True)
def reset_services():
    """Reset database and audit service between tests."""
    db.clear()
    audit_service.clear()


# -----------------------------------------------------------------------------
# MOCKED TESTS (Deterministic, Offline)
# -----------------------------------------------------------------------------

def test_mocked_gemini_response_parsing_to_schema():
    """Test that raw Gemini JSON response accurately parses into MilestonePlanSchema."""
    raw_gemini_json = {
        "milestones": [
            {
                "id": "m1",
                "title": "Backend Architecture & Database Setup",
                "description": "Initialize repository structure, Docker compose, and database migrations.",
                "payment_amount": 500.0,
                "deadline": "Day 15",
                "acceptance_criteria": [
                    {
                        "id": "c1",
                        "type": "repo_file_exists",
                        "params": {"repo": "acme/project", "file_path": "docker-compose.yml"},
                        "weight": 0.5,
                        "must_pass": True,
                    },
                    {
                        "id": "c2",
                        "type": "github_checks_passing",
                        "params": {"repo": "acme/project", "branch_or_commit": "main"},
                        "weight": 0.5,
                        "must_pass": True,
                    },
                ],
            },
            {
                "id": "m2",
                "title": "API Endpoints & Deployment",
                "description": "Deploy working endpoints to staging environment and verify health check.",
                "payment_amount": 500.0,
                "deadline": "Day 30",
                "acceptance_criteria": [
                    {
                        "id": "c3",
                        "type": "url_returns_200",
                        "params": {"url": "https://staging.project.dev/health"},
                        "weight": 0.75,
                        "must_pass": True,
                    },
                    {
                        "id": "c4",
                        "type": "manual_review",
                        "params": {"checklist": ["API auth works", "Documentation complete"], "reviewer_role": "client"},
                        "weight": 0.25,
                        "must_pass": False,
                    },
                ],
            },
        ],
        "summary": "2-stage delivery plan for backend and staging deployment.",
    }

    plan_schema = MilestonePlanSchema(**raw_gemini_json)
    assert len(plan_schema.milestones) == 2
    assert plan_schema.milestones[0].id == "m1"
    assert plan_schema.milestones[0].payment_amount == 500.0
    assert len(plan_schema.milestones[0].acceptance_criteria) == 2
    assert plan_schema.milestones[1].acceptance_criteria[0].type == "url_returns_200"


def test_mocked_gemini_generation_produces_genuine_gemini_plan():
    """Verify that a valid LLM-generated plan sets plan_source='llm_generated' and does not fall back."""
    project_payload = {
        "project_description": "Build an e-commerce platform with product catalog and payments",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_id": "client_test",
        "freelancer_id": "freelancer_test",
        "user_provided_config": {
            "payment_provider": "Stripe",
            "repository": "acme/ecommerce-app",
            "deployment_url": "https://staging.myproject.dev",
        },
    }

    mock_milestones = [
        {
            "id": "m1",
            "title": "Core Setup & Catalog",
            "description": "Setup project and implement catalog.",
            "payment_amount": 500.0,
            "deadline": "Day 15",
            "acceptance_criteria": [
                {
                    "id": "c1",
                    "type": "repo_file_exists",
                    "params": {"repo": "acme/ecommerce-app", "file_path": "README.md"},
                    "weight": 0.8,
                    "must_pass": True,
                },
                {
                    "id": "c2",
                    "type": "manual_review",
                    "params": {"checklist": ["Catalog displays"], "reviewer_role": "client"},
                    "weight": 0.2,
                    "must_pass": False,
                },
            ],
        },
        {
            "id": "m2",
            "title": "Payments & Deployment",
            "description": "Integrate Stripe and deploy to staging.",
            "payment_amount": 500.0,
            "deadline": "Day 30",
            "acceptance_criteria": [
                {
                    "id": "c3",
                    "type": "url_returns_200",
                    "params": {"url": "https://staging.myproject.dev"},
                    "weight": 0.75,
                    "must_pass": True,
                },
                {
                    "id": "c4",
                    "type": "manual_review",
                    "params": {"checklist": ["Payment verified"], "reviewer_role": "client"},
                    "weight": 0.25,
                    "must_pass": False,
                },
            ],
        },
    ]

    mock_plan = MilestonePlanSchema(
        milestones=[MilestoneSchema(**m) for m in mock_milestones],
        summary="Roadmap",
    )

    with patch.object(llm_service, "check_clarity") as mock_clarity, \
         patch.object(llm_service, "generate_milestones") as mock_gen:

        mock_clarity.return_value = ClarityCheckSchema(is_clear=True, reasoning="Requirements clear.")
        mock_gen.return_value = mock_plan

        runner = ScopingAgentRunner()
        state = runner.start_project(project_payload, thread_id="test_mock_gemini_gen")

        assert state["plan_source"] == "llm_generated"
        assert state["project_status"] in (STATUS_DRAFT, STATUS_PENDING_APPROVAL)
        assert len(state["milestones"]) == 2
        assert state["validation_errors"] == []
        assert state["unresolved_parameters"] == []
        assert not state["needs_human_edit"]


def test_mocked_gemini_repair_flow_recovers_to_gemini_repaired():
    """Verify that an initial invalid plan successfully repairs and sets plan_source='llm_repaired'."""
    project_payload = {
        "project_description": "Build an e-commerce platform with product catalog and payments",
        "total_budget": 1000.0,
        "currency": "USD",
        "deadline": "30 days",
        "client_id": "client_test",
        "freelancer_id": "freelancer_test",
        "user_provided_config": {
            "payment_provider": "Stripe",
            "repository": "acme/ecommerce-app",
            "deployment_url": "https://staging.myproject.dev",
        },
    }

    # Initial plan has budget sum error: 400 + 400 = 800 != 1000
    invalid_milestones = [
        {
            "id": "m1",
            "title": "Phase 1",
            "description": "Phase 1 setup",
            "payment_amount": 400.0,
            "deadline": "Day 15",
            "acceptance_criteria": [
                {
                    "id": "c1",
                    "type": "repo_file_exists",
                    "params": {"repo": "acme/ecommerce-app", "file_path": "README.md"},
                    "weight": 1.0,
                    "must_pass": True,
                }
            ],
        },
        {
            "id": "m2",
            "title": "Phase 2",
            "description": "Phase 2 launch",
            "payment_amount": 400.0,
            "deadline": "Day 30",
            "acceptance_criteria": [
                {
                    "id": "c2",
                    "type": "url_returns_200",
                    "params": {"url": "https://staging.myproject.dev"},
                    "weight": 1.0,
                    "must_pass": True,
                }
            ],
        },
    ]

    # Repaired plan fixes the budget sum: 500 + 500 = 1000
    repaired_milestones = [
        {
            "id": "m1",
            "title": "Phase 1",
            "description": "Phase 1 setup",
            "payment_amount": 500.0,
            "deadline": "Day 15",
            "acceptance_criteria": [
                {
                    "id": "c1",
                    "type": "repo_file_exists",
                    "params": {"repo": "acme/ecommerce-app", "file_path": "README.md"},
                    "weight": 1.0,
                    "must_pass": True,
                }
            ],
        },
        {
            "id": "m2",
            "title": "Phase 2",
            "description": "Phase 2 launch",
            "payment_amount": 500.0,
            "deadline": "Day 30",
            "acceptance_criteria": [
                {
                    "id": "c2",
                    "type": "url_returns_200",
                    "params": {"url": "https://staging.myproject.dev"},
                    "weight": 1.0,
                    "must_pass": True,
                }
            ],
        },
    ]

    with patch.object(llm_service, "check_clarity") as mock_clarity, \
         patch.object(llm_service, "generate_milestones") as mock_gen, \
         patch.object(llm_service, "repair_milestones") as mock_repair:

        mock_clarity.return_value = ClarityCheckSchema(is_clear=True, reasoning="Requirements clear.")
        mock_gen.return_value = MilestonePlanSchema(milestones=[MilestoneSchema(**m) for m in invalid_milestones])
        mock_repair.return_value = MilestonePlanSchema(milestones=[MilestoneSchema(**m) for m in repaired_milestones])

        runner = ScopingAgentRunner()
        state = runner.start_project(project_payload, thread_id="test_mock_gemini_repair")

        assert mock_repair.called
        assert state["repair_attempt"] == 1
        assert state["plan_source"] == "llm_repaired"
        assert state["project_status"] in (STATUS_DRAFT, STATUS_PENDING_APPROVAL)
        assert len(state["milestones"]) == 2
        assert state["validation_errors"] == []
        assert state["unresolved_parameters"] == []


def test_clarification_parser_extracts_owner_repo_format():
    """Verify that an answer with 'owner/repo' format is properly extracted into user_provided_config."""
    config = {}
    unresolved = ["repository"]
    config_status = {}

    _extract_config_from_answers(
        {"What is the GitHub repository path?": "acme-inc/storefront-web"},
        config,
        unresolved,
        config_status,
    )

    assert config.get("repository") == "acme-inc/storefront-web"
    assert config.get("repository_provider") == "GitHub"
    assert config_status.get("repository") == "RESOLVED"
    assert "repository" not in unresolved


def test_verified_config_documentation_formatting():
    """Verify verified client configuration documentation is properly generated for prompts."""
    config = {
        "payment_provider": "Stripe",
        "repository": "company/shop",
        "deployment_url": "https://shop.company.com",
    }
    doc = format_verified_config_documentation(config)
    assert "payment_provider: Stripe" in doc
    assert "repository: company/shop" in doc
    assert "deployment_url / staging_url: https://shop.company.com" in doc


# -----------------------------------------------------------------------------
# REAL GEMINI API TEST (Live Execution)
# -----------------------------------------------------------------------------

@pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY is not set.")
def test_real_gemini_milestone_generation_and_validation():
    """Live Gemini test: Verify actual Gemini model returns structured, policy-compliant milestones."""
    project_description = (
        "Build a modern SaaS marketing landing page with Hero, Features, Pricing, and Contact form sections."
    )
    total_budget = 600.0
    currency = "USD"
    deadline = "20 days"
    user_cfg = {
        "repository": "myteam/marketing-site",
        "deployment_url": "https://staging.marketingsite.dev",
    }

    # Call Gemini directly via LLMService
    plan_schema = llm_service.generate_milestones(
        project_description=project_description,
        total_budget=total_budget,
        currency=currency,
        deadline=deadline,
        user_provided_config=user_cfg,
    )

    assert isinstance(plan_schema, MilestonePlanSchema)
    assert 2 <= len(plan_schema.milestones) <= 6

    milestones_list = [m.model_dump() for m in plan_schema.milestones]

    # Validate against deterministic policy rules
    is_valid, errors, corrected, unresolved = validate_and_correct_milestone_plan(
        milestones=milestones_list,
        total_budget=total_budget,
        project_deadline=deadline,
        user_provided_config=user_cfg,
        enforce_provenance=True,
    )

    assert is_valid, f"Real Gemini milestones failed validation: {errors}"
    assert unresolved == [], f"Unresolved parameters found: {unresolved}"
    assert sum(m["payment_amount"] for m in corrected) == pytest.approx(total_budget, 0.01)
