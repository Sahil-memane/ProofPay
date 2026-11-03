"""Predefined Criteria Library for ProofPay Scoping Agent.

Every milestone acceptance criterion must strictly map to one of these predefined types.
The LLM cannot invent new criterion types.

Criteria are categorized into:
- Hard criteria: Objective acceptance checks that can be evaluated against the submitted work.
  Infrastructure-backed checks are optional; deliverable_check records scope-based checks
  without requiring a repository, URL, or invented file path.
- Soft criteria: Supplementary human review checks (e.g., manual_review). Soft criteria do not
  count toward the 70% hard criteria weight threshold.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class CriterionTypeDefinition:
    type_name: str
    description: str
    is_hard: bool
    required_params: Set[str]
    example_params: Dict[str, Any] = field(default_factory=dict)


CRITERIA_REGISTRY: Dict[str, CriterionTypeDefinition] = {
    "url_returns_200": CriterionTypeDefinition(
        type_name="url_returns_200",
        description="Verify an HTTP GET request to the specified URL returns a 200 OK status code.",
        is_hard=True,
        required_params={"url"},
        example_params={"url": "https://staging.example.com/health"},
    ),
    "url_contains_text": CriterionTypeDefinition(
        type_name="url_contains_text",
        description="Verify the response body of a URL contains the expected text or heading.",
        is_hard=True,
        required_params={"url", "expected_text"},
        example_params={"url": "https://staging.example.com", "expected_text": "Welcome to ProofPay"},
    ),
    "github_pr_merged": CriterionTypeDefinition(
        type_name="github_pr_merged",
        description="Verify a designated GitHub Pull Request has been successfully merged into the target branch.",
        is_hard=True,
        required_params={"repo", "pr_number"},
        example_params={"repo": "client-org/web-app", "pr_number": 12},
    ),
    "github_checks_passing": CriterionTypeDefinition(
        type_name="github_checks_passing",
        description="Verify CI/CD status checks (e.g., GitHub Actions, linting, tests) pass on a branch or commit.",
        is_hard=True,
        required_params={"repo", "branch_or_commit"},
        example_params={"repo": "client-org/web-app", "branch_or_commit": "main"},
    ),
    "repo_file_exists": CriterionTypeDefinition(
        type_name="repo_file_exists",
        description="Verify that a specific file path exists in the repository.",
        is_hard=True,
        required_params={"repo", "file_path"},
        example_params={"repo": "client-org/web-app", "file_path": "README.md"},
    ),
    "file_type_size": CriterionTypeDefinition(
        type_name="file_type_size",
        description="Verify an artifact or file is of allowed extension(s) and does not exceed maximum KB size.",
        is_hard=True,
        required_params={"file_path", "max_size_kb", "allowed_extensions"},
        example_params={"file_path": "assets/bundle.zip", "max_size_kb": 50000, "allowed_extensions": [".zip", ".tar.gz"]},
    ),
    "file_has_sections": CriterionTypeDefinition(
        type_name="file_has_sections",
        description="Verify a document or configuration file contains all required section headings or keys.",
        is_hard=True,
        required_params={"file_path", "required_sections"},
        example_params={"file_path": "docs/architecture.md", "required_sections": ["Architecture", "Data Model", "Security"]},
    ),
    "deliverable_check": CriterionTypeDefinition(
        type_name="deliverable_check",
        description=(
            "Define an objective check for an agreed project deliverable. "
            "This records what must be submitted and which scope-based checks must pass; "
            "it does not require a GitHub repository, deployment URL, or invented file path. "
            "A later verification workflow evaluates the submitted artifact."
        ),
        is_hard=True,
        required_params={"deliverable", "acceptance_checks"},
        example_params={
            "deliverable": "Working product listing and shopping cart functionality",
            "acceptance_checks": [
                "Products are displayed with name, price, and image",
                "A user can add and remove products from the cart",
                "Cart total updates when quantities change",
            ],
        },
    ),
    "manual_review": CriterionTypeDefinition(
        type_name="manual_review",
        description="Soft criterion: Manual inspection or visual review performed by client/reviewer.",
        is_hard=False,
        required_params={"checklist", "reviewer_role"},
        example_params={"checklist": ["UI adheres to brand guidelines", "Typography looks crisp"], "reviewer_role": "client"},
    ),
}

ALLOWED_CRITERIA_TYPES: Set[str] = set(CRITERIA_REGISTRY.keys())
HARD_CRITERIA_TYPES: Set[str] = {k for k, v in CRITERIA_REGISTRY.items() if v.is_hard}
SOFT_CRITERIA_TYPES: Set[str] = {k for k, v in CRITERIA_REGISTRY.items() if not v.is_hard}


def is_valid_criterion_type(type_name: str) -> bool:
    """Return True if criterion type is in the predefined library."""
    return type_name in ALLOWED_CRITERIA_TYPES


def is_hard_criterion(type_name: str) -> bool:
    """Return True if the criterion is an objective hard acceptance check."""
    return type_name in HARD_CRITERIA_TYPES


def validate_criterion_parameters(type_name: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate whether all required parameters for a criterion type are present and non-empty."""
    if not is_valid_criterion_type(type_name):
        return False, f"Criterion type '{type_name}' is not in the predefined library. Allowed: {sorted(ALLOWED_CRITERIA_TYPES)}"

    definition = CRITERIA_REGISTRY[type_name]
    if not isinstance(params, dict):
        return False, f"Criterion '{type_name}' parameters must be a dictionary, got {type(params).__name__}"

    missing = definition.required_params - set(params.keys())
    if missing:
        return False, f"Criterion '{type_name}' is missing required parameters: {sorted(missing)}"

    # Ensure parameters are not empty/null
    for req in definition.required_params:
        val = params.get(req)
        if val is None or val == "" or (isinstance(val, (list, dict)) and len(val) == 0):
            return False, f"Criterion '{type_name}' parameter '{req}' cannot be null or empty."

    if type_name == "deliverable_check":
        deliverable = params.get("deliverable")
        checks = params.get("acceptance_checks")
        if not isinstance(deliverable, str) or len(deliverable.strip()) < 5:
            return False, "Criterion 'deliverable_check' requires a descriptive deliverable name."
        if not isinstance(checks, list) or not checks or any(not isinstance(item, str) or not item.strip() for item in checks):
            return False, "Criterion 'deliverable_check' acceptance_checks must be a non-empty list of clear strings."
        if any(token in deliverable.lower() for token in ("<unresolved", "tbd", "placeholder", "todo")):
            return False, "Criterion 'deliverable_check' contains an unresolved deliverable placeholder."

    return True, None


def get_criteria_prompt_documentation() -> str:
    """Generate a formatted documentation string to include in LLM prompts."""
    lines = [
        "Allowed Criteria Library (SELECT CRITERIA ONLY FROM THIS LIST; DO NOT INVENT NEW TYPES):",
        ""
    ]
    for name, c_def in sorted(CRITERIA_REGISTRY.items()):
        category = "HARD CRITERION (objective)" if c_def.is_hard else "SOFT CRITERION (manual/informational)"
        lines.append(f"- Type: `{name}` [{category}]")
        lines.append(f"  Description: {c_def.description}")
        lines.append(f"  Required params: {sorted(c_def.required_params)}")
        lines.append(f"  Example: {c_def.example_params}")
    return "\n".join(lines)

