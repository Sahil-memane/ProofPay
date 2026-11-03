"""LangGraph Node implementations for ProofPay Scoping Agent.

Follows the mandatory design principle:
"The LLM proposes, the policy engine decides, code executes."
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from ProofPay.agents.scoping_agent.state import (
    ScopingState,
    STATUS_RECEIVED,
    STATUS_PRE_VALIDATED,
    STATUS_NEEDS_CLARIFICATION,
    STATUS_CLARIFICATION_REQUESTED,
    STATUS_DRAFT,
    STATUS_NEEDS_HUMAN_EDIT,
    STATUS_PENDING_APPROVAL,
    STATUS_PLAN_APPROVED,
    STATUS_ERROR,
)
from ProofPay.agents.scoping_agent.validators import (
    validate_project_input,
    validate_and_correct_milestone_plan,
    generate_fallback_milestone_plan,
    compute_plan_hash,
)
from ProofPay.services.llm_service import llm_service, LLMServiceError
from ProofPay.services.audit_service import audit_service
from ProofPay.services.database import db

# Maximum Gemini calls permitted per project workflow
MAX_LLM_CALLS_POLICY = 4


def _extract_config_from_answers(
    answers: Any,
    current_config: Dict[str, Any],
    unresolved_params: List[str],
    config_status: Dict[str, str],
) -> None:
    """Extract only values explicitly supplied in answers.

    Question text is deliberately excluded from provider detection because
    questions often contain examples such as "PayPal, Stripe, Square".
    """
    import re

    if isinstance(answers, dict):
        answer_values = [str(value).strip() for value in answers.values() if value is not None]
    elif isinstance(answers, str):
        answer_values = [answers.strip()]
    else:
        answer_values = []

    answer_text = " ".join(answer_values)
    lower_text = answer_text.lower()
    uncertain_answer = any(
        phrase in lower_text
        for phrase in ("not decided", "not sure", "undecided", "don't know", "do not know", "tbd")
    )

    def mark_resolved(key: str, value: Any) -> None:
        current_config[key] = value
        config_status[key] = "RESOLVED"
        while key in unresolved_params:
            unresolved_params.remove(key)

    # Payment provider: only an explicit answer value can authorize a provider.
    provider_aliases = {
        "stripe": "Stripe",
        "paypal": "PayPal",
        "square": "Square",
        "braintree": "Braintree",
        "authorize.net": "Authorize.Net",
    }
    for token, canonical in provider_aliases.items():
        if not uncertain_answer and re.search(
            rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", lower_text
        ):
            mark_resolved("payment_provider", canonical)
            break

    # Repository platform and concrete repository are separate facts.
    repo_platforms = {
        "github": "GitHub",
        "gitlab": "GitLab",
        "bitbucket": "Bitbucket",
    }
    for token, canonical in repo_platforms.items():
        if not uncertain_answer and re.search(rf"(?<![a-z0-9]){token}(?![a-z0-9])", lower_text):
            current_config["repository_provider"] = canonical
            config_status["repository_provider"] = "RESOLVED"
            break

    repo_match = re.search(
        r"(?:https?://)?(?:www\.)?(?:github\.com|gitlab\.com|bitbucket\.org)/"
        r"([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)",
        answer_text,
        re.IGNORECASE,
    )
    if not repo_match:
        repo_match = re.search(
            r"(?:repository|repo)\s*(?:url|:|=)?\s*([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)",
            answer_text,
            re.IGNORECASE,
        )
    if not repo_match and not uncertain_answer:
        if isinstance(answers, dict):
            for q, a in answers.items():
                if not a:
                    continue
                q_lower = str(q).lower()
                a_str = str(a).strip()
                if any(k in q_lower for k in ("repository", "repo", "github", "gitlab", "bitbucket")):
                    m = re.search(r"(?:https?://)?(?:www\.)?(?:github\.com|gitlab\.com|bitbucket\.org)/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)", a_str, re.IGNORECASE)
                    if not m:
                        m = re.search(r"([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)", a_str)
                    if m and not m.group(1).lower().startswith("http"):
                        repo_match = m
                        break
        if not repo_match:
            for val in answer_values:
                val_stripped = val.strip()
                m = re.match(r"^([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)$", val_stripped)
                if m and not val_stripped.lower().startswith("http"):
                    repo_match = m
                    break
    if repo_match:
        mark_resolved("repository", repo_match.group(1).rstrip(".,;:/"))
        if "repository_provider" not in current_config:
            current_config["repository_provider"] = "GitHub"

    # Hosting platform is not the same as a deployed URL.
    hosting_platforms = {
        "vercel": "Vercel",
        "render": "Render",
        "netlify": "Netlify",
        "railway": "Railway",
        "aws": "AWS",
        "azure": "Azure",
        "gcp": "Google Cloud",
        "google cloud": "Google Cloud",
        "fly.io": "Fly.io",
        "heroku": "Heroku",
    }
    for token, canonical in hosting_platforms.items():
        if not uncertain_answer and token in lower_text:
            current_config["deployment_platform"] = canonical
            config_status["deployment_platform"] = "RESOLVED"
            break

    url_matches = re.findall(r"https?://[^\s<>\"']+", answer_text, re.IGNORECASE)
    for candidate in url_matches:
        matched_url = candidate.rstrip(".,;)")
        lower_url = matched_url.lower()
        # A source-control URL identifies the repository, not the deployment target.
        if any(host in lower_url for host in ("github.com/", "gitlab.com/", "bitbucket.org/")):
            continue
        if not any(domain in lower_url for domain in ("example.com", "example.org", "localhost")):
            mark_resolved("deployment_url", matched_url)
            current_config["staging_url"] = matched_url
            break


# -----------------------------------------------------------------------------
# Node 1: receive_project
# -----------------------------------------------------------------------------
def receive_project(state: ScopingState) -> Dict[str, Any]:
    """Node 1: Ingest project submission, generate unique UUID project ID, and initialize tracking."""
    # If resuming an existing workflow (clarification, edit, approval), preserve state
    if state.get("milestones") or state.get("clarification_answers") or state.get("pending_edit"):
        return {}

    # Mandatory Rule: Generate unique UUID project ID (never client_id)
    project_id = state.get("project_id")
    if not project_id or project_id == state.get("client_id"):
        project_id = str(uuid.uuid4())

    user_provided_config: Dict[str, Any] = dict(state.get("user_provided_config") or {})
    unresolved_params: List[str] = list(state.get("unresolved_parameters") or [])
    config_status: Dict[str, str] = dict(state.get("configuration_status") or {})

    # Mark pre-configured user settings as resolved
    for k, v in user_provided_config.items():
        if v:
            config_status[k] = "RESOLVED"
            while k in unresolved_params:
                unresolved_params.remove(k)

    # Extract configuration explicitly present in the original client description.
    raw_description = state.get("project_description", "")
    _extract_config_from_answers(
        {"project_description": raw_description},
        user_provided_config,
        unresolved_params,
        config_status,
    )
    desc = raw_description.lower()

    # Provider selection is outside Agent 1 scoping. Keep an explicitly supplied
    # provider as optional context, but never block scope approval when absent.
    if user_provided_config.get("payment_provider"):
        config_status["payment_provider"] = "RESOLVED"
    else:
        while "payment_provider" in unresolved_params:
            unresolved_params.remove("payment_provider")
        config_status["payment_provider"] = "NOT_REQUIRED_FOR_SCOPING"

    # Repository and deployment URLs belong to a later verification stage.
    # They are not prerequisites for Agent 1 milestone scoping.
    for optional_key in ("repository", "deployment_url", "staging_url", "production_url"):
        if optional_key in unresolved_params:
            unresolved_params.remove(optional_key)
        if config_status.get(optional_key) == "UNRESOLVED":
            config_status[optional_key] = "NOT_REQUIRED_FOR_SCOPING"

    audit_service.record_event(
        project_id=project_id,
        event_type="PROJECT_RECEIVED",
        actor=state.get("client_id", "system"),
        details={
            "project_id": project_id,
            "budget": state.get("total_budget"),
            "currency": state.get("currency"),
            "deadline": state.get("deadline"),
            "unresolved_parameters": unresolved_params,
        },
    )

    return {
        "project_id": project_id,
        "user_provided_config": user_provided_config,
        "unresolved_parameters": unresolved_params,
        "configuration_status": config_status,
        "clarification_count": state.get("clarification_count", 0),
        "clarification_questions": state.get("clarification_questions", []),
        "validation_errors": [],
        "repair_attempt": state.get("repair_attempt", 0),
        "llm_call_count": state.get("llm_call_count", 0),
        "llm_calls_attempted": state.get("llm_calls_attempted", 0),
        "llm_calls_succeeded": state.get("llm_calls_succeeded", 0),
        "llm_calls_failed": state.get("llm_calls_failed", 0),
        "needs_human_edit": state.get("needs_human_edit", False),
        "needs_human_edit_reasons": state.get("needs_human_edit_reasons", []),
        "client_approved": False,
        "freelancer_approved": False,
        "client_approved_hash": None,
        "freelancer_approved_hash": None,
        "approval_update": None,
        "project_status": STATUS_RECEIVED,
        "plan_hash": None,
        "error_message": None,
    }


# -----------------------------------------------------------------------------
# Node 2: pre_validate
# -----------------------------------------------------------------------------
def pre_validate(state: ScopingState) -> Dict[str, Any]:
    """Node 2: Deterministic Python validation on project input parameters."""
    project_id = state.get("project_id", "unknown")
    desc = state.get("project_description", "")
    budget = state.get("total_budget", 0.0)
    currency = state.get("currency", "USD")
    deadline = state.get("deadline", "")

    is_valid, errors = validate_project_input(
        project_description=desc,
        total_budget=budget,
        currency=currency,
        deadline=deadline,
    )

    if not is_valid:
        audit_service.record_event(
            project_id=project_id,
            event_type="PRE_VALIDATION_FAILED",
            actor="policy_engine",
            details={"errors": errors},
        )
        return {
            "validation_errors": errors,
            "error_message": "; ".join(errors),
            "project_status": STATUS_ERROR,
        }

    audit_service.record_event(
        project_id=project_id,
        event_type="PRE_VALIDATION_PASSED",
        actor="policy_engine",
        details={"status": "OK"},
    )
    return {
        "validation_errors": [],
        "error_message": None,
        "project_status": STATUS_PRE_VALIDATED,
    }


# -----------------------------------------------------------------------------
# Node 3: check_clarity
# -----------------------------------------------------------------------------
def check_clarity(state: ScopingState) -> Dict[str, Any]:
    """Node 3: Check requirements clarity via LLM.

    If vague, generates up to 3 targeted clarification questions.
    Counts attempted, succeeded, and failed calls.
    """
    project_id = state.get("project_id", "unknown")
    desc = state.get("project_description", "")
    budget = state.get("total_budget", 0.0)
    currency = state.get("currency", "USD")
    deadline = state.get("deadline", "")

    # Check maximum-call policy
    attempted = state.get("llm_calls_attempted", 0)
    if attempted >= MAX_LLM_CALLS_POLICY:
        return {"clarification_questions": []}

    new_attempted = attempted + 1

    try:
        clarity_result = llm_service.check_clarity(
            project_description=desc,
            total_budget=budget,
            currency=currency,
            deadline=deadline,
        )
        new_succeeded = state.get("llm_calls_succeeded", 0) + 1

        # Payment provider selection is deliberately outside Agent 1 scoping.
        # It may be configured later, so neither deterministic policy nor Gemini
        # should ask for it before milestone definition.
        questions: List[str] = []
        topic_terms: Dict[str, tuple] = {}
        covered_topics: Set[str] = set()
        non_scoping_infrastructure_terms = (
            "repository", "repo", "github", "gitlab", "bitbucket", "deployment",
            "deploy", "public url", "url", "hosting", "pull request", "pr number",
        )
        raw_model_questions = list(clarity_result.clarification_questions or [])
        def is_payment_provider_question(question: str) -> bool:
            lowered = str(question).lower()
            if any(phrase in lowered for phrase in (
                "payment provider", "payment gateway", "gateway provider",
                "payment processor", "which provider", "which gateway",
                "which processor", "choose a provider", "select a provider",
                "provider do you prefer", "processor do you prefer",
            )):
                return True
            named_providers = ("stripe", "paypal", "square", "braintree", "authorize.net")
            selection_terms = ("prefer", "choose", "select", "use", "integrate")
            return (
                any(name in lowered for name in named_providers)
                and any(term in lowered for term in selection_terms)
                and any(term in lowered for term in ("payment", "checkout", "gateway", "processor"))
            )

        non_scoping_only_questions = bool(raw_model_questions) and all(
            any(term in str(question).lower() for term in non_scoping_infrastructure_terms)
            or is_payment_provider_question(str(question))
            for question in raw_model_questions
        )
        for model_question in raw_model_questions:
            lowered_question = model_question.lower()
            # Infrastructure identifiers are collected by a later verification
            # workflow, not by the milestone scoping agent.
            if any(term in lowered_question for term in non_scoping_infrastructure_terms):
                continue
            # Do not ask for provider selection during scoping, even if Gemini
            # proposes it as a clarification question.
            if is_payment_provider_question(model_question):
                continue
            model_topics = {
                key for key, terms in topic_terms.items()
                if any(term in lowered_question for term in terms)
            }
            # Keep model-generated questions unless a deterministic question
            # already covers the same topic. Questions outside the small topic
            # map (for example, "tech stack" or "features") must not be dropped.
            if (
                not (model_topics & covered_topics)
                and model_question not in questions
                and len(questions) < 3
            ):
                questions.append(model_question)
        if not clarity_result.is_clear and not questions and not non_scoping_only_questions:
            questions.append(
                "Please provide the missing concrete deliverables and acceptance details needed to scope this project."
            )

        if (clarity_result.is_clear or non_scoping_only_questions) and not questions:
            audit_service.record_event(
                project_id=project_id,
                event_type="CLARITY_CHECK_PASSED",
                actor="llm_service",
                details={"reasoning": clarity_result.reasoning, "llm_calls_attempted": new_attempted},
            )
            return {
                "clarification_questions": [],
                "llm_call_count": new_attempted,
                "llm_calls_attempted": new_attempted,
                "llm_calls_succeeded": new_succeeded,
            }
        else:
            audit_service.record_event(
                project_id=project_id,
                event_type="CLARITY_CHECK_VAGUE",
                actor="llm_service",
                details={
                    "reasoning": clarity_result.reasoning,
                    "questions": clarity_result.clarification_questions,
                    "llm_calls_attempted": new_attempted,
                },
            )
            return {
                "clarification_questions": questions,
                "llm_call_count": new_attempted,
                "llm_calls_attempted": new_attempted,
                "llm_calls_succeeded": new_succeeded,
            }

    except LLMServiceError as e:
        new_failed = state.get("llm_calls_failed", 0) + 1
        audit_service.record_event(
            project_id=project_id,
            event_type="CLARITY_CHECK_SKIPPED_LLM_ERROR",
            actor="llm_service",
            details={"error": str(e), "llm_calls_attempted": new_attempted},
        )
        return {
            "clarification_questions": [],
            "llm_call_count": new_attempted,
            "llm_calls_attempted": new_attempted,
            "llm_calls_failed": new_failed,
        }


# -----------------------------------------------------------------------------
# Node 4: generate_questions
# -----------------------------------------------------------------------------
def generate_questions(state: ScopingState) -> Dict[str, Any]:
    """Node 4: Transition state when clarification questions are generated."""
    project_id = state.get("project_id", "unknown")
    new_count = state.get("clarification_count", 0) + 1

    audit_service.record_event(
        project_id=project_id,
        event_type="CLARIFICATION_QUESTIONS_EMITTED",
        actor="system",
        details={
            "clarification_count": new_count,
            "questions": state.get("clarification_questions", []),
        },
    )

    return {
        "clarification_count": new_count,
        "project_status": STATUS_CLARIFICATION_REQUESTED,
    }


# -----------------------------------------------------------------------------
# Node: handle_vague_clarification
# -----------------------------------------------------------------------------
def handle_vague_clarification(state: ScopingState) -> Dict[str, Any]:
    """Node handling when input remains vague after 1 clarification round."""
    project_id = state.get("project_id", "unknown")
    audit_service.record_event(
        project_id=project_id,
        event_type="CLARIFICATION_EXHAUSTED",
        actor="policy_engine",
        details={"status": "NEEDS_HUMAN_CLARIFICATION"},
    )
    return {
        "project_status": STATUS_NEEDS_CLARIFICATION,
        "needs_human_edit": True,
        "needs_human_edit_reasons": ["Project scope remains too vague after the allowed clarification round."],
        "error_message": "Project scope remains too vague after clarification. Human input required.",
    }


# -----------------------------------------------------------------------------
# Node 5: update_project
# -----------------------------------------------------------------------------
def update_project(state: ScopingState) -> Dict[str, Any]:
    """Node 5: Ingest user answers to clarification questions and update project description."""
    project_id = state.get("project_id", "unknown")
    answers = state.get("clarification_answers") or {}

    appended_text = "\n\nClient Clarifications:\n"
    if isinstance(answers, dict):
        for q, a in answers.items():
            appended_text += f"- {q}: {a}\n"
    else:
        appended_text += str(answers) + "\n"

    updated_desc = state.get("project_description", "") + appended_text

    # Extract verified configuration from answers
    current_config = dict(state.get("user_provided_config") or {})
    unresolved_params = list(state.get("unresolved_parameters") or [])
    config_status = dict(state.get("configuration_status") or {})

    _extract_config_from_answers(answers, current_config, unresolved_params, config_status)

    audit_service.record_event(
        project_id=project_id,
        event_type="PROJECT_DESCRIPTION_UPDATED",
        actor=state.get("client_id", "user"),
        details={
            "appended_clarification_length": len(appended_text),
            "user_provided_config": current_config,
            "unresolved_parameters": unresolved_params,
        },
    )

    return {
        "project_description": updated_desc,
        "user_provided_config": current_config,
        "unresolved_parameters": unresolved_params,
        "configuration_status": config_status,
        "clarification_questions": [],
        "clarification_answers": None,
        "project_status": STATUS_PRE_VALIDATED,
    }


# -----------------------------------------------------------------------------
# Node 6: generate_milestones (LLM Call 1)
# -----------------------------------------------------------------------------
def generate_milestones(state: ScopingState) -> Dict[str, Any]:
    """Node 6: LLM Call 1 - Generate structured milestone roadmap."""
    project_id = state.get("project_id", "unknown")
    desc = state.get("project_description", "")
    budget = state.get("total_budget", 0.0)
    currency = state.get("currency", "USD")
    deadline = state.get("deadline", "")

    attempted = state.get("llm_calls_attempted", 0)
    if attempted >= MAX_LLM_CALLS_POLICY:
        return {
            "milestones": [],
            "validation_errors": ["Maximum LLM call policy reached."],
        }

    new_attempted = attempted + 1

    user_cfg = state.get("user_provided_config") or {}
    try:
        plan_schema = llm_service.generate_milestones(
            project_description=desc,
            total_budget=budget,
            currency=currency,
            deadline=deadline,
            user_provided_config=user_cfg,
        )
        new_succeeded = state.get("llm_calls_succeeded", 0) + 1
        milestones_list = [m.model_dump() for m in plan_schema.milestones]

        audit_service.record_event(
            project_id=project_id,
            event_type="MILESTONES_GENERATED_BY_LLM",
            actor="llm_service",
            details={"milestones_count": len(milestones_list), "llm_calls_attempted": new_attempted},
        )

        return {
            "milestones": milestones_list,
            "llm_call_count": new_attempted,
            "llm_calls_attempted": new_attempted,
            "llm_calls_succeeded": new_succeeded,
            "plan_source": "llm_generated",
            "validation_errors": [],
        }

    except LLMServiceError as e:
        new_failed = state.get("llm_calls_failed", 0) + 1
        audit_service.record_event(
            project_id=project_id,
            event_type="LLM_GENERATION_FAILED",
            actor="llm_service",
            details={"error": str(e), "llm_calls_attempted": new_attempted},
        )
        return {
            "milestones": [],
            "llm_call_count": new_attempted,
            "llm_calls_attempted": new_attempted,
            "llm_calls_failed": new_failed,
            "validation_errors": [f"LLM milestone generation failed: {str(e)}"],
        }


# -----------------------------------------------------------------------------
# Node 7: validate_plan
# -----------------------------------------------------------------------------
def validate_plan(state: ScopingState) -> Dict[str, Any]:
    """Node 7: Deterministic Python validation on candidate milestone plan."""
    project_id = state.get("project_id", "unknown")
    milestones = state.get("milestones", [])
    budget = state.get("total_budget", 0.0)
    deadline = state.get("deadline", "")
    user_cfg = state.get("user_provided_config") or {}

    if not milestones:
        return {
            "validation_errors": state.get("validation_errors") or ["No milestones generated to validate."]
        }

    is_valid, errors, corrected, unresolved_params = validate_and_correct_milestone_plan(
        milestones=milestones,
        total_budget=budget,
        project_deadline=deadline,
        user_provided_config=user_cfg,
        enforce_provenance=True,
    )

    # Retain unresolved keys that are truly unresolved in configuration or present in the current plan criteria
    project_config_keys = set()
    config_status = dict(state.get("configuration_status") or {})
    prior_unresolved = {
        key for key in (state.get("unresolved_parameters") or [])
        if key in project_config_keys and config_status.get(key) != "RESOLVED"
    }
    all_unresolved = sorted(list(prior_unresolved.union(unresolved_params)))
    for key in all_unresolved:
        if config_status.get(key) != "RESOLVED":
            config_status[key] = "UNRESOLVED"

    effective_errors = list(errors)
    for key in all_unresolved:
        message = f"Required project/criterion configuration '{key}' is unresolved."
        if message not in effective_errors:
            effective_errors.append(message)
    is_valid = is_valid and not all_unresolved

    if is_valid:
        audit_service.record_event(
            project_id=project_id,
            event_type="PLAN_VALIDATION_PASSED",
            actor="policy_engine",
            details={"milestones_count": len(corrected), "unresolved_parameters": all_unresolved},
        )
        return {
            "milestones": corrected,
            "unresolved_parameters": all_unresolved,
            "configuration_status": config_status,
            "validation_errors": [],
        }
    else:
        audit_service.record_event(
            project_id=project_id,
            event_type="PLAN_VALIDATION_FAILED",
            actor="policy_engine",
            details={"error_count": len(effective_errors), "errors": effective_errors, "unresolved_parameters": all_unresolved},
        )
        return {
            "milestones": corrected,
            "unresolved_parameters": all_unresolved,
            "configuration_status": config_status,
            "validation_errors": effective_errors,
        }


# -----------------------------------------------------------------------------
# Node 8: repair_plan (LLM Call 2)
# -----------------------------------------------------------------------------
def repair_plan(state: ScopingState) -> Dict[str, Any]:
    """Node 8: LLM Call 2 - Repair an invalid milestone plan using deterministic error feedback."""
    project_id = state.get("project_id", "unknown")
    desc = state.get("project_description", "")
    budget = state.get("total_budget", 0.0)
    currency = state.get("currency", "USD")
    deadline = state.get("deadline", "")
    current_m = state.get("milestones", [])
    errors = state.get("validation_errors", [])
    user_cfg = state.get("user_provided_config") or {}

    new_repair_attempt = state.get("repair_attempt", 0) + 1
    attempted = state.get("llm_calls_attempted", 0)

    if attempted >= MAX_LLM_CALLS_POLICY:
        return {
            "validation_errors": ["Maximum LLM call policy reached."],
            "repair_attempt": new_repair_attempt,
        }

    new_attempted = attempted + 1

    try:
        repaired_schema = llm_service.repair_milestones(
            project_description=desc,
            total_budget=budget,
            currency=currency,
            deadline=deadline,
            current_milestones=current_m,
            validation_errors=errors,
            user_provided_config=user_cfg,
        )
        new_succeeded = state.get("llm_calls_succeeded", 0) + 1
        repaired_list = [m.model_dump() for m in repaired_schema.milestones]

        is_valid, new_errors, corrected, unresolved_params = validate_and_correct_milestone_plan(
            milestones=repaired_list,
            total_budget=budget,
            project_deadline=deadline,
            user_provided_config=user_cfg,
            enforce_provenance=True,
        )

        project_config_keys = set()
        config_status = dict(state.get("configuration_status") or {})
        prior_unresolved = {
            key for key in (state.get("unresolved_parameters") or [])
            if key in project_config_keys and config_status.get(key) != "RESOLVED"
        }
        all_unresolved = sorted(list(prior_unresolved.union(unresolved_params)))

        effective_errors = list(new_errors)
        for key in all_unresolved:
            message = f"Required project/criterion configuration '{key}' is unresolved."
            if message not in effective_errors:
                effective_errors.append(message)
        is_valid = is_valid and not all_unresolved

        audit_service.record_event(
            project_id=project_id,
            event_type="PLAN_REPAIR_ATTEMPTED",
            actor="llm_service",
            details={
                "repair_attempt": new_repair_attempt,
                "repaired_valid": is_valid,
                "errors": effective_errors if not is_valid else [],
                "llm_calls_attempted": new_attempted,
            },
        )

        return {
            "milestones": corrected,
            "validation_errors": [] if is_valid else effective_errors,
            "unresolved_parameters": [] if is_valid else all_unresolved,
            "repair_attempt": new_repair_attempt,
            "llm_call_count": new_attempted,
            "llm_calls_attempted": new_attempted,
            "llm_calls_succeeded": new_succeeded,
            "plan_source": "llm_repaired",
        }

    except LLMServiceError as e:
        new_failed = state.get("llm_calls_failed", 0) + 1
        audit_service.record_event(
            project_id=project_id,
            event_type="PLAN_REPAIR_FAILED_LLM_ERROR",
            actor="llm_service",
            details={"error": str(e), "llm_calls_attempted": new_attempted},
        )
        return {
            "validation_errors": [f"LLM repair failed: {str(e)}"],
            "repair_attempt": new_repair_attempt,
            "llm_call_count": new_attempted,
            "llm_calls_attempted": new_attempted,
            "llm_calls_failed": new_failed,
        }


# -----------------------------------------------------------------------------
# Node 9: template_fallback
# -----------------------------------------------------------------------------
def template_fallback(state: ScopingState) -> Dict[str, Any]:
    """Node 9: Deterministic template fallback plan.

    Triggered when LLM generation or repair fails.
    Produces a valid, policy-compliant plan flagged for human review.
    """
    project_id = state.get("project_id", "unknown")
    budget = state.get("total_budget", 0.0)
    currency = state.get("currency", "USD")
    deadline = state.get("deadline", "30 days")
    desc = state.get("project_description", "")

    user_cfg = state.get("user_provided_config") or {}
    fallback_plan = generate_fallback_milestone_plan(
        total_budget=budget,
        currency=currency,
        deadline=deadline,
        project_description=desc,
        user_provided_config=user_cfg,
    )

    is_valid, fallback_errors, corrected, unresolved_from_plan = validate_and_correct_milestone_plan(
        milestones=fallback_plan,
        total_budget=budget,
        project_deadline=deadline,
        user_provided_config=state.get("user_provided_config") or {},
        enforce_provenance=True,
    )
    # Do not carry criterion-specific unresolved keys from the discarded LLM
    # plan into the fallback plan. Retain only unresolved project-level settings
    # and keys detected in the fallback criteria themselves.
    project_config_keys = set()
    config_status = state.get("configuration_status") or {}
    prior_project_unresolved = {
        key for key in (state.get("unresolved_parameters") or [])
        if key in project_config_keys and config_status.get(key) != "RESOLVED"
    }
    unresolved = sorted(prior_project_unresolved.union(unresolved_from_plan))
    blocking_reasons = list(fallback_errors)
    for key in unresolved:
        reason = f"Required project/criterion configuration '{key}' is unresolved."
        if reason not in blocking_reasons:
            blocking_reasons.append(reason)
    if not blocking_reasons:
        blocking_reasons.append("Fallback plan requires human review before it can be approved.")

    audit_service.record_event(
        project_id=project_id,
        event_type="TEMPLATE_FALLBACK_APPLIED",
        actor="policy_engine",
        details={
            "milestones_count": len(corrected),
            "validation_errors": blocking_reasons,
            "unresolved_parameters": unresolved,
        },
    )

    return {
        "milestones": corrected,
        "plan_source": "template_fallback",
        "needs_human_edit": True,
        "needs_human_edit_reasons": blocking_reasons,
        "unresolved_parameters": unresolved,
        "validation_errors": blocking_reasons,
        "client_approved": False,
        "freelancer_approved": False,
        "client_approved_hash": None,
        "freelancer_approved_hash": None,
        "plan_hash": None,
        "approved_at": None,
        "project_status": STATUS_NEEDS_HUMAN_EDIT,
    }


# -----------------------------------------------------------------------------
# Node 10: save_draft
# -----------------------------------------------------------------------------
def save_draft(state: ScopingState) -> Dict[str, Any]:
    """Node 10: Save valid milestone plan as DRAFT in storage."""
    project_id = state.get("project_id", "project")
    milestones = state.get("milestones", [])
    status = STATUS_NEEDS_HUMAN_EDIT if state.get("needs_human_edit") else STATUS_DRAFT

    db.save_project(
        project_id=project_id,
        data={
            "project_id": project_id,
            "project_description": state.get("project_description"),
            "client_id": state.get("client_id"),
            "freelancer_id": state.get("freelancer_id"),
            "total_budget": state.get("total_budget"),
            "currency": state.get("currency"),
            "deadline": state.get("deadline"),
            "milestones": milestones,
            "status": status,
            "plan_source": state.get("plan_source"),
            "user_provided_config": state.get("user_provided_config", {}),
            "client_approved": state.get("client_approved", False),
            "freelancer_approved": state.get("freelancer_approved", False),
            "client_approved_hash": state.get("client_approved_hash"),
            "freelancer_approved_hash": state.get("freelancer_approved_hash"),
            "needs_human_edit": state.get("needs_human_edit", False),
            "needs_human_edit_reasons": state.get("needs_human_edit_reasons", []),
            "validation_errors": state.get("validation_errors", []),
            "unresolved_parameters": state.get("unresolved_parameters", []),
            "configuration_status": state.get("configuration_status", {}),
        },
    )

    audit_service.record_event(
        project_id=project_id,
        event_type="DRAFT_SAVED",
        actor="system",
        details={"milestones_count": len(milestones), "status": status},
    )

    return {
        "project_status": status,
        "validation_errors": state.get("validation_errors", []),
    }


# -----------------------------------------------------------------------------
# Node 11: collect_approvals
# -----------------------------------------------------------------------------
def collect_approvals(state: ScopingState) -> Dict[str, Any]:
    """Node 11: Inspect approval states of client and freelancer."""
    project_id = state.get("project_id", "unknown")
    milestones = state.get("milestones", [])
    errors = state.get("validation_errors", [])
    unresolved = state.get("unresolved_parameters", [])
    client_appr = bool(state.get("client_approved", False))
    freelancer_appr = bool(state.get("freelancer_approved", False))
    c_hash = state.get("client_approved_hash")
    f_hash = state.get("freelancer_approved_hash")

    has_valid_plan = bool(
        milestones
        and len(milestones) >= 2
        and not errors
        and not unresolved
        and not state.get("needs_human_edit", False)
    )
    both_approved = bool(
        has_valid_plan
        and client_appr
        and freelancer_appr
        and c_hash
        and f_hash
        and c_hash == f_hash
    )

    approval_update = state.get("approval_update") or {}
    rejected = approval_update.get("approved") is False
    rejection_reasons = list(state.get("needs_human_edit_reasons") or [])
    if rejected:
        role_label = str(approval_update.get("role") or "Participant").title()
        comment = str(approval_update.get("comment") or "").strip()
        reason = f"{role_label} requested changes to the milestone plan."
        if comment:
            reason += f" Comment: {comment}"
        rejection_reasons = [reason]
        client_appr = False
        freelancer_appr = False
        c_hash = None
        f_hash = None
        new_status = STATUS_NEEDS_HUMAN_EDIT
    elif not has_valid_plan:
        if state.get("needs_human_edit"):
            new_status = STATUS_NEEDS_HUMAN_EDIT
        elif unresolved or errors:
            new_status = STATUS_NEEDS_HUMAN_EDIT
        elif state.get("clarification_questions"):
            new_status = STATUS_CLARIFICATION_REQUESTED
        else:
            new_status = state.get("project_status", STATUS_DRAFT)
    elif state.get("needs_human_edit"):
        new_status = STATUS_NEEDS_HUMAN_EDIT
    elif both_approved:
        new_status = STATUS_DRAFT
    else:
        new_status = STATUS_PENDING_APPROVAL

    db.save_project(
        project_id=project_id,
        data={
            "client_id": state.get("client_id"),
            "freelancer_id": state.get("freelancer_id"),
            "total_budget": state.get("total_budget"),
            "currency": state.get("currency"),
            "deadline": state.get("deadline"),
            "milestones": milestones,
            "status": new_status,
            "client_approved": client_appr,
            "freelancer_approved": freelancer_appr,
            "client_approved_hash": c_hash,
            "freelancer_approved_hash": f_hash,
            "plan_source": state.get("plan_source"),
            "needs_human_edit": bool(state.get("needs_human_edit", False) or rejected),
            "needs_human_edit_reasons": rejection_reasons,
        },
    )

    audit_service.record_event(
        project_id=project_id,
        event_type="APPROVAL_CHECKED",
        actor="system",
        details={
            "client_approved": client_appr,
            "freelancer_approved": freelancer_appr,
            "has_valid_plan": has_valid_plan,
            "unresolved_parameters": unresolved,
            "both_approved": both_approved,
            "rejected": rejected,
            "rejection_reasons": rejection_reasons,
            "client_approved_hash": c_hash,
            "freelancer_approved_hash": f_hash,
        },
    )

    return {
        "project_status": new_status,
        "approval_update": None,
        "client_approved": client_appr,
        "freelancer_approved": freelancer_appr,
        "client_approved_hash": c_hash,
        "freelancer_approved_hash": f_hash,
        "needs_human_edit": bool(state.get("needs_human_edit", False) or rejected),
        "needs_human_edit_reasons": rejection_reasons,
    }


# -----------------------------------------------------------------------------
# Node 12: validate_edit
# -----------------------------------------------------------------------------
def validate_edit(state: ScopingState) -> Dict[str, Any]:
    """Node 12: Deterministically validate human-submitted milestone plan edits.

    MANDATORY RULE: Never call the LLM on edits.
    If valid: replaces milestones and resets both approvals.
    If invalid: returns exact deterministic validation errors.
    """
    project_id = state.get("project_id", "unknown")
    pending = state.get("pending_edit")
    budget = state.get("total_budget", 0.0)
    deadline = state.get("deadline", "")
    user_cfg = state.get("user_provided_config") or {}

    if not pending or not isinstance(pending, list):
        return {
            "validation_errors": ["No pending edit provided for validation."]
        }

    is_valid, errors, corrected, unresolved_params = validate_and_correct_milestone_plan(
        milestones=pending,
        total_budget=budget,
        project_deadline=deadline,
        user_provided_config=user_cfg,
        enforce_provenance=True,
    )

    # Recompute plan-level unresolved values from the edited plan instead of
    # carrying stale placeholders forward. Preserve only unresolved project-level
    # configuration that the client has not actually supplied yet.
    config_status = dict(state.get("configuration_status") or {})
    project_config_keys = set()
    prior_unresolved = {
        key for key in (state.get("unresolved_parameters") or [])
        if key in project_config_keys and config_status.get(key) != "RESOLVED"
    }
    all_unresolved = sorted(prior_unresolved.union(unresolved_params))
    effective_errors = list(errors)
    for key in all_unresolved:
        reason = f"Required project/criterion configuration '{key}' is unresolved."
        if reason not in effective_errors:
            effective_errors.append(reason)
    is_valid = is_valid and not all_unresolved

    if is_valid:
        audit_service.record_event(
            project_id=project_id,
            event_type="PLAN_EDIT_ACCEPTED",
            actor="policy_engine",
            details={"milestones_count": len(corrected)},
        )
        return {
            "milestones": corrected,
            "pending_edit": None,
            "plan_source": "human_edited",
            "needs_human_edit": False,
            "needs_human_edit_reasons": [],
            "unresolved_parameters": [],
            "project_status": STATUS_DRAFT,
            "client_approved": False,
            "freelancer_approved": False,
            "client_approved_hash": None,
            "freelancer_approved_hash": None,
            "plan_hash": None,
            "approved_at": None,
            "approval_update": None,
            "validation_errors": [],
        }
    else:
        audit_service.record_event(
            project_id=project_id,
            event_type="PLAN_EDIT_REJECTED",
            actor="policy_engine",
            details={"errors": errors},
        )
        return {
            "validation_errors": effective_errors,
            "needs_human_edit": True,
            "needs_human_edit_reasons": effective_errors,
            "unresolved_parameters": all_unresolved,
            "project_status": STATUS_NEEDS_HUMAN_EDIT,
            "pending_edit": None,
        }


# -----------------------------------------------------------------------------
# Node 13: lock_plan
# -----------------------------------------------------------------------------
def lock_plan(state: ScopingState) -> Dict[str, Any]:
    """Node 13: Generate SHA-256 cryptographic hash and lock the plan.

    Enforces all safety invariants:
    - Milestones exist and >= 2
    - Deterministic validation passes
    - Zero unresolved mandatory parameters
    - Both authenticated parties approved the exact same plan hash
    """
    project_id = state.get("project_id", "unknown")
    milestones = state.get("milestones", [])
    budget = state.get("total_budget", 0.0)
    currency = state.get("currency", "USD")
    deadline = state.get("deadline", "")
    user_cfg = state.get("user_provided_config") or {}

    # 1. Lifecycle status guard (direct node invocation must not bypass workflow state).
    current_status = state.get("project_status")
    if current_status is not None and current_status not in (STATUS_DRAFT, STATUS_PENDING_APPROVAL):
        return {
            "project_status": current_status,
            "error_message": f"Cannot lock plan from lifecycle status '{current_status}'.",
        }

    # 2. Plan existence check
    if not milestones or len(milestones) < 2:
        return {
            "project_status": STATUS_ERROR,
            "error_message": "Cannot lock plan: Milestone plan is missing or contains fewer than 2 milestones.",
        }

    # 2. Human-edit and existing blocking validation checks
    if state.get("needs_human_edit") or state.get("validation_errors"):
        return {
            "project_status": STATUS_NEEDS_HUMAN_EDIT,
            "error_message": "Cannot lock plan: Human edits or blocking validation issues remain.",
        }

    # 3. Unresolved parameters check
    unresolved = state.get("unresolved_parameters", [])
    if unresolved:
        return {
            "project_status": STATUS_NEEDS_HUMAN_EDIT,
            "error_message": f"Cannot lock plan: Mandatory configuration parameters remain unresolved: {sorted(unresolved)}",
        }

    # 3. Deterministic policy validation check
    is_valid, errors, _, _ = validate_and_correct_milestone_plan(
        milestones=milestones,
        total_budget=budget,
        project_deadline=deadline,
        user_provided_config=user_cfg,
        enforce_provenance=True,
    )
    if not is_valid:
        return {
            "project_status": STATUS_ERROR,
            "validation_errors": errors,
            "error_message": f"Cannot lock plan: Deterministic validation failed with errors: {'; '.join(errors)}",
        }

    # 4. Both parties approval check
    client_appr = bool(state.get("client_approved", False))
    freelancer_appr = bool(state.get("freelancer_approved", False))
    if not (client_appr and freelancer_appr):
        return {
            "project_status": STATUS_PENDING_APPROVAL,
            "error_message": "Cannot lock plan: Both client and freelancer must independently approve.",
        }

    # 5. Same exact plan hash verification
    current_hash = compute_plan_hash(
        milestones=milestones,
        total_budget=budget,
        currency=currency,
        project_id=project_id,
    )
    c_hash = state.get("client_approved_hash")
    f_hash = state.get("freelancer_approved_hash")

    if c_hash != current_hash or f_hash != current_hash:
        return {
            "project_status": STATUS_PENDING_APPROVAL,
            "error_message": "Cannot lock plan: Client and freelancer have not approved the exact same milestone plan version.",
        }

    now_iso = datetime.now(timezone.utc).isoformat()

    event_payload = {
        "project_id": project_id,
        "client_id": state.get("client_id"),
        "freelancer_id": state.get("freelancer_id"),
        "plan_hash": current_hash,
        "total_budget": budget,
        "currency": currency,
        "deadline": deadline,
        "milestones_count": len(milestones),
        "approved_at": now_iso,
    }
    try:
        db.save_approved_plan_and_event(
            project_id=project_id,
            project_data={
                "project_description": state.get("project_description"),
                "client_id": state.get("client_id"),
                "freelancer_id": state.get("freelancer_id"),
                "total_budget": budget,
                "currency": currency,
                "deadline": deadline,
                "milestones": milestones,
                "plan_source": state.get("plan_source"),
                "client_approved": client_appr,
                "freelancer_approved": freelancer_appr,
                "client_approved_hash": c_hash,
                "freelancer_approved_hash": f_hash,
                "needs_human_edit": False,
                "approved_at": now_iso,
            },
            event_payload=event_payload,
        )
    except Exception as exc:
        return {
            "project_status": STATUS_ERROR,
            "error_message": f"Cannot lock plan: persistent database transaction failed: {exc}",
        }

    audit_service.record_event(
        project_id=project_id,
        event_type="PLAN_LOCKED",
        actor="system",
        details={"plan_hash": current_hash, "approved_at": now_iso, "project_id": project_id},
    )

    return {
        "plan_hash": current_hash,
        "project_status": STATUS_PLAN_APPROVED,
        "approved_at": now_iso,
    }


# -----------------------------------------------------------------------------
# Node 14: emit_approved_event
# -----------------------------------------------------------------------------
def emit_approved_event(state: ScopingState) -> Dict[str, Any]:
    """Confirm the plan and plan.approved event were durably persisted by lock_plan."""
    project_id = state.get("project_id", "project")
    plan_hash = state.get("plan_hash")
    if state.get("project_status") != STATUS_PLAN_APPROVED or not plan_hash or not state.get("approved_at"):
        return {
            "project_status": state.get("project_status", STATUS_ERROR),
            "error_message": "Approved event blocked: plan locking did not complete successfully.",
        }

    persisted = db.get_project(project_id)
    matching_events = [
        event for event in db.get_emitted_events("plan.approved")
        if event.get("payload", {}).get("project_id") == project_id
        and event.get("payload", {}).get("plan_hash") == plan_hash
    ]
    if (not persisted or persisted.get("status") != STATUS_PLAN_APPROVED
            or persisted.get("plan_hash") != plan_hash or not matching_events):
        return {
            "project_status": STATUS_ERROR,
            "error_message": "Approved event blocked: locked plan and domain event were not durably persisted.",
        }

    audit_service.record_event(
        project_id=project_id,
        event_type="PLAN_APPROVED_EVENT_CONFIRMED",
        actor="system",
        details=matching_events[0]["payload"],
    )
    return {"project_status": STATUS_PLAN_APPROVED}


# -----------------------------------------------------------------------------
# Node 15: return_error
# -----------------------------------------------------------------------------
def return_error(state: ScopingState) -> Dict[str, Any]:
    """Node 15: Handle fatal workflow error and finalize state."""
    project_id = state.get("project_id", "unknown")
    errors = state.get("validation_errors", [])
    msg = state.get("error_message") or "; ".join(errors) or "Unknown scoping agent error"

    audit_service.record_event(
        project_id=project_id,
        event_type="WORKFLOW_ERROR",
        actor="system",
        details={"error_message": msg},
    )

    return {
        "project_status": STATUS_ERROR,
        "error_message": msg,
    }
