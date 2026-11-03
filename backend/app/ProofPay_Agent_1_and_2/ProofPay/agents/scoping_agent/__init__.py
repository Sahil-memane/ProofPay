"""Scoping Agent package for ProofPay."""

from ProofPay.agents.scoping_agent.state import ScopingState

__all__ = ["ScopingState", "create_scoping_graph", "ScopingAgentRunner"]


def __getattr__(name: str):
    if name in ("create_scoping_graph", "ScopingAgentRunner"):
        from ProofPay.agents.scoping_agent.graph import create_scoping_graph, ScopingAgentRunner
        globals()["create_scoping_graph"] = create_scoping_graph
        globals()["ScopingAgentRunner"] = ScopingAgentRunner
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
