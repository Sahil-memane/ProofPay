"""Real audit package — drop-in replacement for stubs/audit.py."""
from backend.app.audit.search import clear, get_events, search
from backend.app.audit.writer import log_event, write

__all__ = ["write", "log_event", "get_events", "search", "clear"]
