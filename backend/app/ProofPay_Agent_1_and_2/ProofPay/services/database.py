"""Persistent SQLite storage for ProofPay Agent 1.

The default database is created locally at ``data/proofpay.db``. A SQLite URL
can be supplied through DATABASE_URL, for example:
    DATABASE_URL=sqlite:///./data/proofpay.db

No external database account is required for local development. The storage
API is intentionally small so a PostgreSQL repository can replace it later.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_sqlite_path(database_url: Optional[str] = None) -> str:
    """Resolve a SQLite URL/path. Relative paths are anchored to the project root."""
    raw = (database_url or os.getenv("DATABASE_URL") or "sqlite:///./data/proofpay.db").strip()
    if raw in ("sqlite://", "sqlite:///:memory:", ":memory:"):
        return ":memory:"
    if raw.startswith("sqlite:////"):
        path = "/" + raw[len("sqlite:////"):]
    elif raw.startswith("sqlite:///"):
        path = raw[len("sqlite:///"):]
    elif raw.startswith("sqlite://"):
        path = raw[len("sqlite://"):]
    else:
        raise ValueError(
            "This build supports SQLite DATABASE_URL values only. "
            "Use sqlite:///./data/proofpay.db for local development."
        )
    path = unquote(path.split("?", 1)[0])
    if path == ":memory:":
        return path
    path_obj = Path(path)
    if not path_obj.is_absolute():
        project_root = Path(__file__).resolve().parents[1]
        path_obj = project_root / path_obj
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    return str(path_obj.resolve())


class SQLiteProjectStore:
    """SQLite-backed project, approval, audit and domain-event repository."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_path = _resolve_sqlite_path(database_url)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            self.database_path,
            check_same_thread=False,
            timeout=30,
            isolation_level=None,
        )
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA busy_timeout = 30000")
            if self.database_path != ":memory:":
                self._conn.execute("PRAGMA journal_mode = WAL")
            self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                status TEXT,
                plan_hash TEXT,
                locked_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS domain_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT NOT NULL,
                project_id TEXT,
                plan_hash TEXT,
                payload_json TEXT NOT NULL,
                emitted_at TEXT NOT NULL,
                UNIQUE(event_name, project_id, plan_hash)
            );
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                details_json TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_audit_project ON audit_events(project_id, id);
            CREATE INDEX IF NOT EXISTS idx_domain_project ON domain_events(project_id, id);
            CREATE TABLE IF NOT EXISTS verification_submissions (
                submission_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                milestone_id TEXT NOT NULL,
                freelancer_id TEXT NOT NULL,
                status TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_verification_project
                ON verification_submissions(project_id, milestone_id, created_at);
            """
        )

    @staticmethod
    def _json(data: Dict[str, Any]) -> str:
        return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)

    def save_project(self, project_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if not project_id:
            raise ValueError("project_id is required to save a project.")
        now = _utc_now()
        with self._lock:
            existing = self.get_project(project_id) or {}
            if existing.get("status") == "PLAN_APPROVED":
                requested_status = data.get("status") or data.get("project_status") or "PLAN_APPROVED"
                if requested_status != "PLAN_APPROVED":
                    raise ValueError("A locked plan cannot be downgraded or overwritten.")
                if data.get("plan_hash") and data.get("plan_hash") != existing.get("plan_hash"):
                    raise ValueError("A locked plan cannot be replaced with a different plan hash.")
                if data.get("milestones") is not None and data.get("milestones") != existing.get("milestones"):
                    raise ValueError("A locked plan's milestones are immutable.")
            record = {
                **existing,
                **data,
                "project_id": project_id,
                "created_at": existing.get("created_at", now),
                "updated_at": now,
            }
            self._conn.execute(
                """INSERT INTO projects(project_id, data_json, status, plan_hash, locked_at, created_at, updated_at)
                   VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(project_id) DO UPDATE SET
                     data_json=excluded.data_json, status=excluded.status,
                     plan_hash=excluded.plan_hash, locked_at=excluded.locked_at,
                     updated_at=excluded.updated_at""",
                (
                    project_id,
                    self._json(record),
                    record.get("status") or record.get("project_status"),
                    record.get("plan_hash"),
                    record.get("approved_at") or record.get("locked_at"),
                    record["created_at"],
                    record["updated_at"],
                ),
            )
            return record

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT data_json FROM projects WHERE project_id = ?", (project_id,)
            ).fetchone()
            return json.loads(row["data_json"]) if row else None

    def list_projects(self) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT data_json FROM projects ORDER BY created_at DESC"
            ).fetchall()
            return [json.loads(row["data_json"]) for row in rows]

    def record_event(self, event_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = _utc_now()
        project_id = payload.get("project_id")
        plan_hash = payload.get("plan_hash")
        with self._lock:
            cursor = self._conn.execute(
                """INSERT OR IGNORE INTO domain_events
                   (event_name, project_id, plan_hash, payload_json, emitted_at)
                   VALUES(?,?,?,?,?)""",
                (event_name, project_id, plan_hash, self._json(payload), now),
            )
            if cursor.rowcount == 0:
                row = self._conn.execute(
                    """SELECT event_name, payload_json, emitted_at FROM domain_events
                       WHERE event_name=? AND project_id IS ? AND plan_hash IS ?""",
                    (event_name, project_id, plan_hash),
                ).fetchone()
                return {
                    "event_name": row["event_name"],
                    "payload": json.loads(row["payload_json"]),
                    "emitted_at": row["emitted_at"],
                }
        return {"event_name": event_name, "payload": payload, "emitted_at": now}

    def get_emitted_events(self, event_name: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            if event_name:
                rows = self._conn.execute(
                    "SELECT event_name,payload_json,emitted_at FROM domain_events WHERE event_name=? ORDER BY id",
                    (event_name,),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT event_name,payload_json,emitted_at FROM domain_events ORDER BY id"
                ).fetchall()
            return [
                {"event_name": r["event_name"], "payload": json.loads(r["payload_json"]), "emitted_at": r["emitted_at"]}
                for r in rows
            ]

    def save_approved_plan_and_event(
        self,
        project_id: str,
        project_data: Dict[str, Any],
        event_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Atomically persist a locked plan and its plan.approved event."""
        if not project_id or not event_payload.get("plan_hash"):
            raise ValueError("A project ID and plan hash are required for approval persistence.")
        now = _utc_now()
        plan_hash = str(event_payload["plan_hash"])
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                existing_row = self._conn.execute(
                    "SELECT data_json FROM projects WHERE project_id=?", (project_id,)
                ).fetchone()
                existing = json.loads(existing_row["data_json"]) if existing_row else {}
                if existing.get("status") == "PLAN_APPROVED":
                    if existing.get("plan_hash") != plan_hash:
                        raise ValueError("This project already has a different locked milestone plan.")
                    if (project_data.get("milestones") is not None
                            and project_data.get("milestones") != existing.get("milestones")):
                        raise ValueError("A locked plan's milestones are immutable.")

                record = {
                    **existing,
                    **project_data,
                    "project_id": project_id,
                    "status": "PLAN_APPROVED",
                    "plan_hash": plan_hash,
                    "locked_at": event_payload.get("approved_at"),
                    "created_at": existing.get("created_at", now),
                    "updated_at": now,
                }
                self._conn.execute(
                    """INSERT INTO projects(project_id,data_json,status,plan_hash,locked_at,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?)
                       ON CONFLICT(project_id) DO UPDATE SET
                         data_json=excluded.data_json,status=excluded.status,
                         plan_hash=excluded.plan_hash,locked_at=excluded.locked_at,
                         updated_at=excluded.updated_at""",
                    (project_id, self._json(record), "PLAN_APPROVED", plan_hash,
                     record["locked_at"], record["created_at"], now),
                )
                self._conn.execute(
                    """INSERT OR IGNORE INTO domain_events
                       (event_name,project_id,plan_hash,payload_json,emitted_at)
                       VALUES(?,?,?,?,?)""",
                    ("plan.approved", project_id, plan_hash, self._json(event_payload), now),
                )
                self._conn.execute("COMMIT")
                return record
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def save_verification_submission(self, submission_id: str, project_id: str,
                                     milestone_id: str, freelancer_id: str,
                                     status: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a verification run independently of the immutable approved plan."""
        now = _utc_now()
        with self._lock:
            existing = self._conn.execute(
                "SELECT created_at FROM verification_submissions WHERE submission_id=?",
                (submission_id,),
            ).fetchone()
            created_at = existing["created_at"] if existing else now
            self._conn.execute(
                """INSERT INTO verification_submissions
                   (submission_id,project_id,milestone_id,freelancer_id,status,result_json,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?)
                   ON CONFLICT(submission_id) DO UPDATE SET
                     status=excluded.status,result_json=excluded.result_json,updated_at=excluded.updated_at""",
                (submission_id, project_id, milestone_id, freelancer_id, status,
                 self._json(result), created_at, now),
            )
        return {"submission_id": submission_id, "project_id": project_id,
                "milestone_id": milestone_id, "freelancer_id": freelancer_id,
                "status": status, "result": result,
                "created_at": created_at, "updated_at": now}

    def get_verification_submission(self, submission_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM verification_submissions WHERE submission_id=?", (submission_id,)
            ).fetchone()
        if not row:
            return None
        return {"submission_id": row["submission_id"], "project_id": row["project_id"],
                "milestone_id": row["milestone_id"], "freelancer_id": row["freelancer_id"],
                "status": row["status"], "result": json.loads(row["result_json"]),
                "created_at": row["created_at"], "updated_at": row["updated_at"]}

    def list_verification_submissions(self, project_id: str, milestone_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT submission_id FROM verification_submissions WHERE project_id=?"
        args: List[Any] = [project_id]
        if milestone_id:
            query += " AND milestone_id=?"
            args.append(milestone_id)
        query += " ORDER BY created_at DESC"
        with self._lock:
            rows = self._conn.execute(query, args).fetchall()
        return [self.get_verification_submission(row["submission_id"]) for row in rows]

    def record_audit_event(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._conn.execute(
                "INSERT INTO audit_events(project_id,event_type,actor,details_json,timestamp) VALUES(?,?,?,?,?)",
                (entry["project_id"], entry["event_type"], entry["actor"], self._json(entry.get("details") or {}), entry["timestamp"]),
            )
        return entry

    def get_audit_events(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            if project_id:
                rows = self._conn.execute(
                    "SELECT * FROM audit_events WHERE project_id=? ORDER BY id", (project_id,)
                ).fetchall()
            else:
                rows = self._conn.execute("SELECT * FROM audit_events ORDER BY id").fetchall()
            return [
                {"timestamp": r["timestamp"], "project_id": r["project_id"],
                 "event_type": r["event_type"], "actor": r["actor"],
                 "details": json.loads(r["details_json"])}
                for r in rows
            ]

    def clear_audit_events(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM audit_events")

    def clear(self) -> None:
        """Clear application/checkpoint data (tests only; never used in normal app flow)."""
        with self._lock:
            self._conn.execute("DELETE FROM domain_events")
            self._conn.execute("DELETE FROM audit_events")
            self._conn.execute("DELETE FROM projects")
            self._conn.execute("DELETE FROM verification_submissions")
            # LangGraph SqliteSaver creates these tables in this same DB file.
            # Clear checkpoint rows between tests while preserving its migrations table.
            existing_tables = {
                row["name"] for row in self._conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            for table in ("checkpoints", "writes", "blobs"):
                if table in existing_tables:
                    self._conn.execute(f"DELETE FROM {table}")

    def close(self) -> None:
        with self._lock:
            self._conn.close()


# Shared persistent store. Tests can use DATABASE_URL=sqlite:///:memory: to isolate it.
db = SQLiteProjectStore()


def get_database_path() -> str:
    """Return the resolved SQLite path for LangGraph checkpoint persistence."""
    return db.database_path
