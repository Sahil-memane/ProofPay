"""
AST test: enforce that answer_key is ONLY imported by
  - backend/app/simulator/
  - backend/app/reconciliation/metrics.py
  - backend/app/eval/

No other module (recovery, channels, api, agents, scheduler, etc.) may import it.
"""
from __future__ import annotations
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]   # d:/paypal

# Directories that must NEVER import the answer key
CHECK_DIRS = [
    "backend/app/recovery",
    "backend/app/channels",
    "backend/app/api",
    "backend/app/agents",
    "backend/app/scheduler",
    "backend/app/reconciliation",  # checked with metrics.py exemption
]


def _imports_answer_key(source: str) -> bool:
    """Return True if source code imports the answer_key module."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "answer_key" in alias.name:
                    return True
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "answer_key" in module:
                return True
    return False


def test_answer_key_not_imported_by_forbidden_modules():
    violations: list[str] = []
    for check_dir in CHECK_DIRS:
        search_path = REPO_ROOT / check_dir
        if not search_path.exists():
            continue
        py_files = list(search_path.rglob("*.py"))
        for py_file in py_files:
            rel = py_file.relative_to(REPO_ROOT).as_posix()
            # Exception explicitly allowed by spec: backend/app/reconciliation/metrics.py
            if rel == "backend/app/reconciliation/metrics.py":
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
            except Exception:
                continue
            if _imports_answer_key(source):
                violations.append(rel)

    assert not violations, (
        f"answer_key imported from forbidden modules:\n"
        + "\n".join(f"  {v}" for v in violations)
    )

