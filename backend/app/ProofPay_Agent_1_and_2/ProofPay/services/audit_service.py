"""Persistent audit logging service for ProofPay."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging

from ProofPay.services.database import db

logger = logging.getLogger("ProofPay.Audit")


class AuditService:
    def record_event(
        self,
        project_id: str,
        event_type: str,
        actor: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_id": project_id,
            "event_type": event_type,
            "actor": actor,
            "details": details or {},
        }
        db.record_audit_event(entry)
        logger.info("[AUDIT] [%s] Project: %s Actor: %s", event_type, project_id, actor)
        return entry

    def get_events(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return db.get_audit_events(project_id=project_id)

    def clear(self) -> None:
        db.clear_audit_events()


audit_service = AuditService()
