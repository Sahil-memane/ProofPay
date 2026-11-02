# TEMP: replaced by llm/
"""Stub LLM client — returns canned responses, tracks call count per case."""
from __future__ import annotations
from typing import Any

_call_counts: dict[str, int] = {}
MAX_LLM_CALLS_PER_CASE = 2


def complete(case_id: str, prompt: str, **kwargs: Any) -> str:
    """Return a deterministic stub response; enforces per-case call limit."""
    count = _call_counts.get(case_id, 0)
    if count >= MAX_LLM_CALLS_PER_CASE:
        raise RuntimeError(
            f"LLM call limit ({MAX_LLM_CALLS_PER_CASE}) exceeded for case {case_id}"
        )
    _call_counts[case_id] = count + 1
    return f"[stub-llm] response #{count + 1} for {case_id}"


def get_call_count(case_id: str) -> int:
    return _call_counts.get(case_id, 0)


def reset() -> None:
    _call_counts.clear()
