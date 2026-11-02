"""
Import Linter Verification Test (Step 13).

Enforces the core ProofPay architectural contract:
  "The agent proposes, the policy decides, code executes.
   Recovery code never imports PayPal or email code; it only builds Proposal objects."
Forbids app.recovery, app.agents, and app.reconciliation from importing:
  - backend.app.paypal
  - backend.app.channels
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FORBIDDEN_TARGETS = {"backend.app.paypal", "app.paypal", "paypal", "backend.app.channels", "app.channels", "channels"}
INSPECT_DIRS = [
    ROOT / "backend" / "app" / "recovery",
    ROOT / "backend" / "app" / "agents",
    ROOT / "backend" / "app" / "reconciliation",
]


def test_import_linter_architectural_boundaries():
    """Assert that recovery, agents, and reconciliation NEVER import paypal or channels."""
    violations: list[str] = []

    for d in INSPECT_DIRS:
        if not d.exists():
            continue
        for py_file in d.rglob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read(), filename=str(py_file))
                except Exception as e:
                    violations.append(f"Parse error in {py_file}: {e}")
                    continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for forbidden in FORBIDDEN_TARGETS:
                            if alias.name == forbidden or alias.name.startswith(forbidden + "."):
                                violations.append(f"{py_file.name}:{node.lineno} imports '{alias.name}'")

                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for forbidden in FORBIDDEN_TARGETS:
                        if mod == forbidden or mod.startswith(forbidden + "."):
                            violations.append(f"{py_file.name}:{node.lineno} imports from '{mod}'")

    assert not violations, (
        "Architectural contract violation: forbidden imports found in recovery/agents/reconciliation:\n"
        + "\n".join(violations)
    )

