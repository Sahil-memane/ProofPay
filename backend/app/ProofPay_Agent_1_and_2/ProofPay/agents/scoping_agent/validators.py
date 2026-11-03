"""Deterministic policy validators for ProofPay Scoping Agent.

Mandatory Design Principle:
"The LLM proposes, the policy engine decides, code executes."

No LLM output bypasses these Python validation checks.
All rules specified in Section 4 are strictly enforced.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ProofPay.agents.scoping_agent.criteria_library import (
    ALLOWED_CRITERIA_TYPES,
    is_hard_criterion,
    is_valid_criterion_type,
    validate_criterion_parameters,
)

# Configurable Policy Defaults
DEFAULT_SUPPORTED_CURRENCIES = {"USD", "EUR", "GBP", "CAD", "AUD"}
DEFAULT_MIN_PROJECT_BUDGET = float(os.getenv("MIN_PROJECT_BUDGET", "50.0"))
DEFAULT_MAX_PROJECT_BUDGET = float(os.getenv("MAX_PROJECT_BUDGET", "50000.0"))
DEFAULT_MIN_MILESTONE_AMOUNT = float(os.getenv("MIN_MILESTONE_AMOUNT", "20.0"))
DEFAULT_MAX_RELEASE_PERCENTAGE = float(os.getenv("MAX_RELEASE_PERCENTAGE", "0.80"))

DEFAULT_MIN_MILESTONES = int(os.getenv("MIN_MILESTONES", "2"))
DEFAULT_MAX_MILESTONES = int(os.getenv("MAX_MILESTONES", "6"))
DEFAULT_MIN_HARD_CRITERIA_RATIO = float(os.getenv("MIN_HARD_CRITERIA_RATIO", "0.70"))

MIN_DESCRIPTION_LENGTH = 15
MAX_DESCRIPTION_LENGTH = 15000


def get_supported_currencies() -> set[str]:
    raw = os.getenv("SUPPORTED_CURRENCIES", "")
    if raw:
        return {c.strip().upper() for c in raw.split(",") if c.strip()}
    return DEFAULT_SUPPORTED_CURRENCIES


# -----------------------------------------------------------------------------
# Input Validation (Section 4)
# -----------------------------------------------------------------------------

def parse_deadline_to_days(deadline_str: str) -> Optional[float]:
    """Parse various deadline formats into a numeric day offset from today.

    Supported formats:
    - '30 days', '2 weeks', '1 month'
    - '30d', '14'
    - ISO date: '2026-12-01', '2026-11-20'
    Returns number of days relative to now, or None if unparseable.
    """
    if not deadline_str or not isinstance(deadline_str, str):
        return None

    cleaned = deadline_str.strip().lower()

    # Match numeric days: "30 days", "30d", "14", "Day 15", "day 30"
    match_prefix_day = re.match(r"^day\s*(\d+(?:\.\d+)?)$", cleaned)
    if match_prefix_day:
        return float(match_prefix_day.group(1))

    match_days = re.match(r"^(\d+(?:\.\d+)?)\s*(?:days?|d)?$", cleaned)
    if match_days:
        return float(match_days.group(1))

    # Match weeks: "2 weeks", "2w"
    match_weeks = re.match(r"^(\d+(?:\.\d+)?)\s*(?:weeks?|w)$", cleaned)
    if match_weeks:
        return float(match_weeks.group(1)) * 7.0

    # Match months: "1 month", "2 months", "1m"
    match_months = re.match(r"^(\d+(?:\.\d+)?)\s*(?:months?|m)$", cleaned)
    if match_months:
        return float(match_months.group(1)) * 30.0

    # Match ISO date format: YYYY-MM-DD
    match_date = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", cleaned)
    if match_date:
        try:
            target_date = datetime.strptime(cleaned, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            # Use current UTC date
            now = datetime.now(timezone.utc)
            delta = (target_date - now).total_seconds() / 86400.0
            return delta
        except Exception:
            return None

    return None


def validate_project_input(
    project_description: str,
    total_budget: float,
    currency: str,
    deadline: str,
    min_budget: float = DEFAULT_MIN_PROJECT_BUDGET,
    max_budget: float = DEFAULT_MAX_PROJECT_BUDGET,
) -> Tuple[bool, List[str]]:
    """Validate project intake data before passing to LLM or graph processing.

    Returns:
        (is_valid, list_of_errors)
    """
    errors: List[str] = []

    # 1. Project description validation
    if not project_description or not isinstance(project_description, str):
        errors.append("Project description must not be empty.")
    else:
        stripped = project_description.strip()
        if len(stripped) == 0:
            errors.append("Project description must not be empty.")
        elif len(stripped) < MIN_DESCRIPTION_LENGTH:
            errors.append(
                f"Project description is too short ({len(stripped)} chars). Minimum required: {MIN_DESCRIPTION_LENGTH} chars."
            )
        elif len(stripped) > MAX_DESCRIPTION_LENGTH:
            errors.append(
                f"Project description exceeds maximum length ({len(stripped)} > {MAX_DESCRIPTION_LENGTH} chars)."
            )

    # 2. Currency validation
    supported_currencies = get_supported_currencies()
    if not currency or not isinstance(currency, str):
        errors.append("Currency must be specified.")
    elif currency.strip().upper() not in supported_currencies:
        errors.append(
            f"Unsupported currency '{currency}'. Supported currencies: {sorted(supported_currencies)}"
        )

    # 3. Budget validation
    if total_budget is None or not isinstance(total_budget, (int, float)):
        errors.append("Total budget must be a valid positive number.")
    else:
        if total_budget <= 0:
            errors.append(f"Total budget must be positive, got {total_budget}.")
        elif total_budget < min_budget:
            errors.append(
                f"Total budget {total_budget} is below the minimum allowed policy limit of {min_budget}."
            )
        elif total_budget > max_budget:
            errors.append(
                f"Total budget {total_budget} exceeds the maximum allowed policy limit of {max_budget}."
            )

    # 4. Deadline validation
    if not deadline or not isinstance(deadline, str) or not deadline.strip():
        errors.append("Project deadline must be specified.")
    else:
        days = parse_deadline_to_days(deadline)
        if days is None:
            errors.append(
                f"Invalid deadline format '{deadline}'. Expected formats: '30 days', '2 weeks', 'YYYY-MM-DD'."
            )
        elif days <= 0:
            errors.append(f"Project deadline must be in the future, got '{deadline}' ({days:.1f} days).")

    return (len(errors) == 0, errors)


# -----------------------------------------------------------------------------
# Milestone Plan Validation (Section 4)
# -----------------------------------------------------------------------------

KNOWN_PLACEHOLDER_DOMAINS = [
    "example.com",
    "example.org",
    "test.com",
    ".test",
    ".invalid",
    "shop.test",
    "localhost",
    "127.0.0.1",
    "staging.example.com",
    "prod.example.com",
]

KNOWN_PLACEHOLDER_REPOS = [
    "project-repo",
    "client-org/",
    "myorg/",
    "test/repo",
    "org/repo",
    "your-org/",
    "your-username/",
    "username/",
]

KNOWN_PLACEHOLDER_TEXTS = [
    "welcome to our store",
    "product catalog",
    "product title example",
    "your shopping cart",
    "secure checkout",
    "sample text",
]


def detect_unresolved_and_placeholder_params(
    milestones: List[Dict[str, Any]],
    user_provided_config: Optional[Dict[str, Any]] = None,
) -> Tuple[List[str], List[str]]:
    """Detect hallucinated infrastructure, generic placeholder values, and unverified parameters.

    Returns:
        (placeholder_errors, unresolved_parameter_keys)
    """
    errors: List[str] = []
    unresolved: set[str] = set()
    user_cfg = user_provided_config or {}

    configured_repo = (user_cfg.get("repository") or "").lower().strip()
    configured_urls = {
        u.lower().strip()
        for u in [
            user_cfg.get("staging_url"),
            user_cfg.get("production_url"),
            user_cfg.get("deployment_url"),
        ]
        if u
    }
    configured_provider = (user_cfg.get("payment_provider") or "").lower().strip()
    known_payment_providers = (
        "stripe", "paypal", "square", "adyen", "braintree",
        "razorpay", "authorize.net", "authorize net", "checkout.com",
        "worldpay", "payoneer", "mollie",
    )

    for idx, m in enumerate(milestones):
        m_title = str(m.get("title", f"Milestone {idx + 1}"))
        m_desc = str(m.get("description", ""))

        # Agent 1 must NOT ask the client to choose a payment provider merely
        # because the scope says "payment integration". However, if the LLM
        # silently injects a named provider into a milestone, that is an
        # unauthorized scope decision and must be flagged. A configured
        # provider is the only provider that may be named in the generated plan.
        milestone_text = f"{m_title} {m_desc}".lower()
        mentioned_providers = [
            provider for provider in known_payment_providers
            if re.search(r"(?<![a-z0-9])" + re.escape(provider.strip()) + r"(?![a-z0-9])", milestone_text)
        ]
        if mentioned_providers:
            allowed_provider = configured_provider.strip().lower()
            unauthorized = [provider for provider in mentioned_providers if provider.strip() != allowed_provider]
            if unauthorized:
                names = ", ".join(sorted(set(unauthorized)))
                errors.append(
                    f"Milestone {idx + 1} names payment provider(s) {names} without explicit client authorization. "
                    "Use provider-neutral wording such as 'payment gateway integration' or obtain explicit client configuration."
                )
                unresolved.add("payment_provider")

        criteria = m.get("acceptance_criteria", [])
        for c_idx, crit in enumerate(criteria):
            if not isinstance(crit, dict):
                continue
            params = crit.get("params", {})

            # B. URL checks
            if "url" in params:
                url_val = str(params["url"]).lower().strip()
                if "<unresolved" in url_val or any(d in url_val for d in KNOWN_PLACEHOLDER_DOMAINS):
                    errors.append(
                        f"Milestone {idx + 1} criterion {c_idx + 1} uses placeholder/hallucinated URL '{params['url']}'. "
                        "Real deployment target URL must be configured."
                    )
                    unresolved.add("deployment_url")
                elif not configured_urls:
                    errors.append(
                        f"Milestone {idx + 1} criterion {c_idx + 1} URL '{params['url']}' was not supplied "
                        "in client configuration. A model-generated URL cannot be treated as verified."
                    )
                    unresolved.add("deployment_url")
                elif not any(cfg_u in url_val for cfg_u in configured_urls):
                    errors.append(
                        f"Milestone {idx + 1} criterion {c_idx + 1} URL '{params['url']}' does not match client-configured URLs: {sorted(configured_urls)}"
                    )
                    unresolved.add("deployment_url")

            # C. Repository checks
            if "repo" in params:
                repo_val = str(params["repo"]).lower().strip()
                if "<unresolved" in repo_val or any(r in repo_val for r in KNOWN_PLACEHOLDER_REPOS):
                    errors.append(
                        f"Milestone {idx + 1} criterion {c_idx + 1} uses placeholder/hallucinated repository '{params['repo']}'. "
                        "Real repository must be configured."
                    )
                    unresolved.add("repository")
                elif not configured_repo:
                    errors.append(
                        f"Milestone {idx + 1} criterion {c_idx + 1} repository '{params['repo']}' was not supplied "
                        "by the client. A model-generated repository cannot be treated as verified."
                    )
                    unresolved.add("repository")
                elif configured_repo != repo_val:
                    errors.append(
                        f"Milestone {idx + 1} criterion {c_idx + 1} repository '{params['repo']}' does not match configured repo '{configured_repo}'."
                    )
                    unresolved.add("repository")

            # D. PR number checks
            if "pr_number" in params:
                pr_val = str(params["pr_number"]).lower().strip()
                configured_pr = str(user_cfg.get("pr_number") or "").strip().lower()
                if (
                    "<unresolved" in pr_val
                    or "repository" in unresolved
                    or not configured_repo
                    or not configured_pr
                    or configured_pr != pr_val
                ):
                    errors.append(
                        f"Milestone {idx + 1} criterion {c_idx + 1} specifies PR number '{params['pr_number']}', "
                        "but the exact PR number was not confirmed in client configuration."
                    )
                    unresolved.add("github_pr")

            # E. File/artifact paths must be concrete and client-provided when
            # used as standalone deliverable checks. A repository-relative path
            # remains valid for repo_file_exists only after the repository itself
            # has been explicitly configured.
            if "file_path" in params:
                file_path_raw = str(params["file_path"]).strip()
                file_path_val = file_path_raw.lower()
                placeholder_path_tokens = (
                    "<unresolved", "tbd", "todo", "placeholder", "your-file",
                    "your_deliverable", "unresolved_deliverable",
                )
                if not file_path_val or any(token in file_path_val for token in placeholder_path_tokens):
                    errors.append(
                        f"Milestone {idx + 1} criterion {c_idx + 1} uses unresolved file path "
                        f"'{params.get('file_path')}'. A concrete agreed deliverable path is required."
                    )
                    unresolved.add("deliverable_path")
                elif crit.get("type") in ("file_type_size", "file_has_sections"):
                    configured_paths = user_cfg.get("deliverable_paths") or []
                    configured_single = user_cfg.get("deliverable_path")
                    if configured_single:
                        configured_paths = list(configured_paths) + [configured_single]
                    normalized_paths = {str(item).strip().lower() for item in configured_paths if item}
                    if file_path_val not in normalized_paths:
                        errors.append(
                            f"Milestone {idx + 1} criterion {c_idx + 1} file path '{file_path_raw}' "
                            "was not explicitly agreed in client configuration. Use deliverable_check "
                            "when no concrete artifact path has been agreed."
                        )
                        unresolved.add("deliverable_path")

            # F. Expected text checks
            if "expected_text" in params:
                text_val = str(params["expected_text"]).lower().strip()
                if "<unresolved" in text_val or text_val in KNOWN_PLACEHOLDER_TEXTS:
                    errors.append(
                        f"Milestone {idx + 1} criterion {c_idx + 1} uses placeholder expected text '{params['expected_text']}'."
                    )
                    unresolved.add("expected_text")

    return errors, sorted(list(unresolved))


def validate_and_correct_milestone_plan(
    milestones: List[Dict[str, Any]],
    total_budget: float,
    project_deadline: str,
    min_milestones: int = DEFAULT_MIN_MILESTONES,
    max_milestones: int = DEFAULT_MAX_MILESTONES,
    min_milestone_amount: float = DEFAULT_MIN_MILESTONE_AMOUNT,
    max_release_percentage: float = DEFAULT_MAX_RELEASE_PERCENTAGE,
    min_hard_criteria_ratio: float = DEFAULT_MIN_HARD_CRITERIA_RATIO,
    user_provided_config: Optional[Dict[str, Any]] = None,
    enforce_provenance: bool = False,
) -> Tuple[bool, List[str], List[Dict[str, Any]], List[str]]:
    """Run all deterministic Python validators on the candidate milestone plan.

    If minor float variance exists (<= 0.05), it is adjusted on the final milestone.
    Returns:
        (is_valid, list_of_errors, corrected_milestones, unresolved_parameters)
    """
    errors: List[str] = []
    unresolved_params: List[str] = []

    if not isinstance(milestones, list):
        return False, ["Milestones must be provided as a list."], [], []

    # 1. Milestone count validation (between 2 and 6)
    count = len(milestones)
    if count < min_milestones or count > max_milestones:
        errors.append(
            f"Plan must contain between {min_milestones} and {max_milestones} milestones, but received {count}."
        )

    # Clone milestones for potential rounding adjustment
    corrected: List[Dict[str, Any]] = [dict(m) for m in milestones]

    # 2. Amounts check and rounding correction
    total_allocated = 0.0
    for idx, m in enumerate(corrected):
        amount = m.get("payment_amount")
        if amount is None or not isinstance(amount, (int, float)):
            errors.append(f"Milestone {idx + 1} ('{m.get('title', 'Unknown')}') missing valid payment_amount.")
            continue

        if amount < min_milestone_amount:
            errors.append(
                f"Milestone {idx + 1} amount {amount:.2f} is below minimum allowed milestone limit of {min_milestone_amount:.2f}."
            )

        max_allowed_for_milestone = total_budget * max_release_percentage
        if amount > max_allowed_for_milestone:
            errors.append(
                f"Milestone {idx + 1} amount {amount:.2f} exceeds maximum single release limit of "
                f"{max_release_percentage * 100:.0f}% of total budget ({max_allowed_for_milestone:.2f})."
            )

        total_allocated += float(amount)

    # Check sum against total budget with rounding adjustment
    if count > 0:
        budget_diff = round(total_budget - total_allocated, 4)
        if abs(budget_diff) > 0.001:
            if abs(budget_diff) <= 0.05:
                final_m = corrected[-1]
                old_amount = float(final_m.get("payment_amount", 0.0))
                new_amount = round(old_amount + budget_diff, 2)
                final_m["payment_amount"] = new_amount
            else:
                errors.append(
                    f"Sum of milestone amounts ({total_allocated:.2f}) does not equal total budget ({total_budget:.2f}). "
                    f"Difference: {budget_diff:.2f}."
                )

    # 3. Deadlines validation: ordered and within project deadline
    overall_deadline_days = parse_deadline_to_days(project_deadline)
    last_deadline_days = -1.0

    for idx, m in enumerate(corrected):
        m_title = m.get("title", f"Milestone {idx + 1}")
        m_deadline = m.get("deadline")
        if not m_deadline:
            errors.append(f"Milestone {idx + 1} ('{m_title}') is missing a deadline.")
            continue

        m_days = parse_deadline_to_days(str(m_deadline))
        if m_days is None:
            errors.append(f"Milestone {idx + 1} ('{m_title}') has unparseable deadline '{m_deadline}'.")
            continue

        if m_days <= 0:
            errors.append(f"Milestone {idx + 1} deadline '{m_deadline}' must be in the future.")

        if m_days < last_deadline_days - 0.001:
            errors.append(
                f"Milestone {idx + 1} deadline ('{m_deadline}' ~ {m_days:.1f} days) is earlier than "
                f"Milestone {idx} deadline (~ {last_deadline_days:.1f} days). Deadlines must be strictly ordered."
            )
        last_deadline_days = m_days

        if overall_deadline_days is not None and m_days > overall_deadline_days + 0.001:
            errors.append(
                f"Milestone {idx + 1} deadline ('{m_deadline}' ~ {m_days:.1f} days) exceeds "
                f"overall project deadline ('{project_deadline}' ~ {overall_deadline_days:.1f} days)."
            )

    # 4. Acceptance Criteria validation
    for idx, m in enumerate(corrected):
        m_title = m.get("title", f"Milestone {idx + 1}")
        criteria = m.get("acceptance_criteria", [])

        if not criteria or not isinstance(criteria, list):
            errors.append(f"Milestone {idx + 1} ('{m_title}') has no acceptance criteria.")
            continue

        hard_criteria_count = 0
        total_criterion_weight = 0.0
        hard_criterion_weight = 0.0

        for c_idx, crit in enumerate(criteria):
            if not isinstance(crit, dict):
                errors.append(f"Milestone {idx + 1} criterion {c_idx + 1} must be an object.")
                continue

            c_type = crit.get("type")
            c_weight = crit.get("weight", 0.0)
            c_params = crit.get("params", {})

            # A. Criteria library check
            if not c_type or not is_valid_criterion_type(c_type):
                errors.append(
                    f"Milestone {idx + 1} criterion {c_idx + 1} has invalid type '{c_type}'. "
                    f"Must belong to predefined library: {sorted(ALLOWED_CRITERIA_TYPES)}"
                )
                continue

            # B. Criterion parameter completeness
            valid_params, param_err = validate_criterion_parameters(c_type, c_params)
            if not valid_params:
                errors.append(f"Milestone {idx + 1} criterion {c_idx + 1} ({c_type}) parameter error: {param_err}")

            # C. Weight calculation
            try:
                c_weight_f = float(c_weight)
            except (ValueError, TypeError):
                c_weight_f = 0.0
                errors.append(f"Milestone {idx + 1} criterion {c_idx + 1} has invalid numeric weight '{c_weight}'.")

            total_criterion_weight += c_weight_f
            if is_hard_criterion(c_type):
                hard_criteria_count += 1
                hard_criterion_weight += c_weight_f

        # D. Every milestone must contain at least one hard criterion
        if hard_criteria_count == 0:
            errors.append(
                f"Milestone {idx + 1} ('{m_title}') does not contain any hard criteria. "
                "Every milestone must have at least one objective hard acceptance criterion."
            )

        # E. Hard criteria must carry at least 70% of total criterion weight
        if total_criterion_weight <= 0.0001:
            errors.append(f"Milestone {idx + 1} total criterion weight must be greater than 0.")
        else:
            hard_ratio = hard_criterion_weight / total_criterion_weight
            if hard_ratio < (min_hard_criteria_ratio - 0.001):
                errors.append(
                    f"Milestone {idx + 1} ('{m_title}') hard criteria weight ratio is {hard_ratio * 100:.1f}%, "
                    f"which is below the required {min_hard_criteria_ratio * 100:.0f}% minimum."
                )

    # 5. Information Provenance & Placeholder Detection
    placeholder_errs, unres_keys = detect_unresolved_and_placeholder_params(
        milestones=corrected,
        user_provided_config=user_provided_config,
    )
    unresolved_params.extend(unres_keys)

    if enforce_provenance:
        errors.extend(placeholder_errs)

    is_valid = len(errors) == 0
    return is_valid, errors, corrected, unresolved_params


# -----------------------------------------------------------------------------
# Deterministic Template Fallback (Section 6 & 9)
# -----------------------------------------------------------------------------

def generate_fallback_milestone_plan(
    total_budget: float,
    currency: str,
    deadline: str,
    project_description: str = "",
    user_provided_config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Generate a deterministic, human-review fallback using scope deliverables.

    This fallback never invents repository names, URLs, PR numbers, or file paths.
    It remains flagged for human review and is not automatically approvable.
    """
    days = parse_deadline_to_days(deadline) or 30.0
    half_1 = round(total_budget * 0.50, 2)
    half_2 = round(total_budget - half_1, 2)
    m1_days = max(1, int(days * 0.5))
    m2_days = max(2, int(days))

    description = (project_description or "").strip()
    scope_lines = [
        line.strip(" -\t0123456789.)")
        for line in description.splitlines()
        if line.strip() and len(line.strip()) > 3
    ]
    scope_items = [line for line in scope_lines if len(line) > 5][:8]
    if not scope_items:
        scope_items = ["The functional requirements explicitly listed in the project brief"]

    foundation_checks = [
        "Project structure and initial architecture are documented and match the agreed scope",
        "The development foundation can be reviewed and the agreed setup instructions are supplied",
    ]
    implementation_checks = [
        f"Delivered work covers the agreed requirement: {item[:180]}"
        for item in scope_items[:5]
    ]

    return [
        {
            "id": "m1",
            "title": "Milestone 1: Project Foundation and Architecture",
            "description": "Establish the agreed project structure, architecture, and initial foundation deliverables.",
            "payment_amount": half_1,
            "deadline": f"Day {m1_days}",
            "acceptance_criteria": [
                {
                    "id": "m1_c1",
                    "type": "deliverable_check",
                    "params": {
                        "deliverable": "Project architecture and initial foundation deliverables",
                        "acceptance_checks": foundation_checks,
                    },
                    "weight": 0.75,
                    "must_pass": True,
                },
                {
                    "id": "m1_c2",
                    "type": "manual_review",
                    "params": {
                        "checklist": [
                            "Client confirms the architecture matches the agreed project scope",
                            "Client confirms the initial foundation is understandable and reviewable",
                        ],
                        "reviewer_role": "client",
                    },
                    "weight": 0.25,
                    "must_pass": False,
                },
            ],
        },
        {
            "id": "m2",
            "title": "Milestone 2: Implementation and Final Deliverables",
            "description": "Complete the functional deliverables agreed in the project brief and submit them for acceptance.",
            "payment_amount": half_2,
            "deadline": f"Day {m2_days}",
            "acceptance_criteria": [
                {
                    "id": "m2_c1",
                    "type": "deliverable_check",
                    "params": {
                        "deliverable": "Completed project implementation and final agreed deliverables",
                        "acceptance_checks": implementation_checks,
                    },
                    "weight": 0.75,
                    "must_pass": True,
                },
                {
                    "id": "m2_c2",
                    "type": "manual_review",
                    "params": {
                        "checklist": [
                            "Client confirms all agreed deliverables have been submitted",
                            "Client confirms the final work meets the agreed acceptance checks",
                        ],
                        "reviewer_role": "client",
                    },
                    "weight": 0.25,
                    "must_pass": False,
                },
            ],
        },
    ]


# -----------------------------------------------------------------------------
# SHA-256 Plan Hashing (Section 3H & 8)
# -----------------------------------------------------------------------------

def compute_plan_hash(
    milestones: List[Dict[str, Any]],
    total_budget: float,
    currency: str,
    project_id: Optional[str] = None,
) -> str:
    """Generate deterministic SHA-256 hash of approved milestones, criteria, and amounts.

    Canonical JSON serialization ensures identical cryptographic signature across platforms.
    Raises ValueError if milestones list is empty or insufficient.
    """
    if not milestones or not isinstance(milestones, list) or len(milestones) < 2:
        raise ValueError(
            f"Cannot compute plan hash: Plan must contain at least 2 valid milestones, got {len(milestones) if isinstance(milestones, list) else type(milestones)}."
        )

    normalized: Dict[str, Any] = {
        "total_budget": float(total_budget),
        "currency": str(currency).upper(),
        "milestones": milestones,
    }
    if project_id:
        normalized["project_id"] = str(project_id)

    serialized = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
