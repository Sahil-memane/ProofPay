from typing import Any, Dict, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    SqliteSaver = None
import sqlite3
from ProofPay.agents.verification_agent.state import VerificationState
from ProofPay.agents.verification_agent.nodes import load_locked_plan, verify_evidence, explain_result, persist_verification
from ProofPay.services.database import get_database_path


def _load(state: VerificationState) -> Dict[str, Any]:
    return load_locked_plan(state)


def _route(state: VerificationState) -> str:
    return "error" if state.get("error") else "verify"


def _error(state: VerificationState) -> Dict[str, Any]:
    return {"decision": "BLOCKED", "explanation": state.get("error", "Verification blocked.")}


def create_verification_graph(checkpointer: Optional[Any] = None):
    builder = StateGraph(VerificationState)
    builder.add_node("load_locked_plan", _load)
    builder.add_node("verify_evidence", verify_evidence)
    builder.add_node("explain_result", explain_result)
    builder.add_node("persist_verification", persist_verification)
    builder.add_node("blocked", _error)
    builder.add_edge(START, "load_locked_plan")
    builder.add_conditional_edges("load_locked_plan", _route, {"error": "blocked", "verify": "verify_evidence"})
    builder.add_edge("verify_evidence", "explain_result")
    builder.add_edge("explain_result", "persist_verification")
    builder.add_edge("persist_verification", END)
    builder.add_edge("blocked", END)
    return builder.compile(checkpointer=checkpointer)


class VerificationAgentRunner:
    def __init__(self):
        self.connection = None
        if SqliteSaver is not None:
            self.connection = sqlite3.connect(get_database_path(), check_same_thread=False, timeout=30)
            self.checkpointer = SqliteSaver(self.connection)
            self.checkpointer.setup()
        else:
            self.checkpointer = MemorySaver()
        self.graph = create_verification_graph(self.checkpointer)

    def submit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        config = {"configurable": {"thread_id": payload["submission_id"]}}
        return self.graph.invoke(payload, config=config)


verification_runner = VerificationAgentRunner()
