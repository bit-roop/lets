"""Durable storage abstraction for Application Cases and Tracking.

Provides a unified interface supporting:
1. Local development / unit-test execution via standard library SQLite.
2. Production / Cloud deployment via PostgreSQL / Neon when DATABASE_URL is configured.

Uses parameterized queries throughout. Strictly closes connections on completion.
"""

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ApplicationRecord

DEFAULT_DB_PATH = Path(".applications.db")

_SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS applications (
    application_id TEXT PRIMARY KEY,
    tracking_reference TEXT UNIQUE NOT NULL,
    entity_name TEXT NOT NULL,
    status TEXT NOT NULL,
    as_of TEXT NOT NULL,
    facts_json TEXT NOT NULL,
    approvals_json TEXT NOT NULL,
    submissions_json TEXT NOT NULL,
    verification_json TEXT NOT NULL,
    timeline_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_applications_tracking ON applications(tracking_reference);
CREATE INDEX IF NOT EXISTS idx_applications_created ON applications(created_at);

CREATE TABLE IF NOT EXISTS approval_lifecycle (
    application_id TEXT NOT NULL,
    approval_id TEXT NOT NULL,
    department TEXT NOT NULL,
    status TEXT NOT NULL,
    decision_note TEXT,
    decided_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (application_id, approval_id)
);
CREATE INDEX IF NOT EXISTS idx_approval_lifecycle_dept ON approval_lifecycle(department);

CREATE TABLE IF NOT EXISTS application_queries (
    query_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    approval_id TEXT NOT NULL,
    department TEXT NOT NULL,
    query_text TEXT NOT NULL,
    deadline TEXT NOT NULL,
    status TEXT NOT NULL,
    response_text TEXT,
    response_document_id TEXT,
    response_submission_id TEXT,
    responded_at TEXT,
    resolution_note TEXT,
    resolved_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_queries_application ON application_queries(application_id);
CREATE INDEX IF NOT EXISTS idx_queries_department ON application_queries(department);

CREATE TABLE IF NOT EXISTS application_events (
    event_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    approval_id TEXT,
    department TEXT,
    actor TEXT NOT NULL,
    event_type TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_application ON application_events(application_id);
"""

_SCHEMA_POSTGRES = """
CREATE TABLE IF NOT EXISTS applications (
    application_id VARCHAR(255) PRIMARY KEY,
    tracking_reference VARCHAR(255) UNIQUE NOT NULL,
    entity_name TEXT NOT NULL,
    status VARCHAR(50) NOT NULL,
    as_of VARCHAR(50) NOT NULL,
    facts_json TEXT NOT NULL,
    approvals_json TEXT NOT NULL,
    submissions_json TEXT NOT NULL,
    verification_json TEXT NOT NULL,
    timeline_json TEXT NOT NULL,
    created_at VARCHAR(100) NOT NULL,
    updated_at VARCHAR(100) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_applications_tracking ON applications(tracking_reference);
CREATE INDEX IF NOT EXISTS idx_applications_created ON applications(created_at);

CREATE TABLE IF NOT EXISTS approval_lifecycle (
    application_id VARCHAR(255) NOT NULL,
    approval_id VARCHAR(64) NOT NULL,
    department VARCHAR(64) NOT NULL,
    status VARCHAR(50) NOT NULL,
    decision_note TEXT,
    decided_at VARCHAR(100),
    created_at VARCHAR(100) NOT NULL,
    updated_at VARCHAR(100) NOT NULL,
    PRIMARY KEY (application_id, approval_id)
);
CREATE INDEX IF NOT EXISTS idx_approval_lifecycle_dept ON approval_lifecycle(department);

CREATE TABLE IF NOT EXISTS application_queries (
    query_id VARCHAR(255) PRIMARY KEY,
    application_id VARCHAR(255) NOT NULL,
    approval_id VARCHAR(64) NOT NULL,
    department VARCHAR(64) NOT NULL,
    query_text TEXT NOT NULL,
    deadline VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    response_text TEXT,
    response_document_id VARCHAR(255),
    response_submission_id VARCHAR(255),
    responded_at VARCHAR(100),
    resolution_note TEXT,
    resolved_at VARCHAR(100),
    created_at VARCHAR(100) NOT NULL,
    updated_at VARCHAR(100) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_queries_application ON application_queries(application_id);
CREATE INDEX IF NOT EXISTS idx_queries_department ON application_queries(department);

CREATE TABLE IF NOT EXISTS application_events (
    event_id VARCHAR(255) PRIMARY KEY,
    application_id VARCHAR(255) NOT NULL,
    approval_id VARCHAR(64),
    department VARCHAR(64),
    actor VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    detail TEXT,
    created_at VARCHAR(100) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_application ON application_events(application_id);
"""


class ApplicationStore:
    def __init__(self, path: Optional[Path] = None, database_url: Optional[str] = None):
        self.database_url = database_url if database_url is not None else os.getenv("DATABASE_URL")
        self.path = Path(path).resolve() if path else DEFAULT_DB_PATH.resolve()
        self._lock = threading.Lock()
        self.is_postgres = bool(self.database_url and (
            self.database_url.startswith("postgres://") or self.database_url.startswith("postgresql://")
        ))
        if not self.is_postgres:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connection(self):
        """Context manager guaranteeing connection closing across all OSes and databases."""
        if self.is_postgres:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(self.database_url)
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.path), timeout=30.0)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_db(self):
        if not self.is_postgres:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            if self.is_postgres:
                with conn.cursor() as cur:
                    cur.execute(_SCHEMA_POSTGRES)
            else:
                conn.executescript(_SCHEMA_SQLITE)

    def next_tracking_reference(self) -> str:
        """Generates sequential tracking references (e.g. MH-FOOD-2026-0001)."""
        with self._lock, self._connection() as conn:
            if self.is_postgres:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM applications")
                    total = cur.fetchone()[0]
                    return f"MH-FOOD-2026-{(total + 1):04d}"
            else:
                cursor = conn.execute("SELECT COUNT(*) AS total FROM applications")
                row = cursor.fetchone()
                count = (row["total"] if row else 0) + 1
                return f"MH-FOOD-2026-{count:04d}"

    def save(self, record: ApplicationRecord) -> None:
        params = (
            record.application_id,
            record.tracking_reference,
            record.entity_name,
            record.status,
            record.as_of,
            json.dumps(record.facts),
            json.dumps(record.approvals),
            json.dumps(record.submissions),
            json.dumps(record.verification_records),
            json.dumps(record.timeline),
            record.created_at,
            record.updated_at,
        )
        with self._lock, self._connection() as conn:
            if self.is_postgres:
                sql = """
                INSERT INTO applications (
                    application_id, tracking_reference, entity_name, status,
                    as_of, facts_json, approvals_json, submissions_json,
                    verification_json, timeline_json, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (application_id) DO UPDATE SET
                    tracking_reference = EXCLUDED.tracking_reference,
                    entity_name = EXCLUDED.entity_name,
                    status = EXCLUDED.status,
                    as_of = EXCLUDED.as_of,
                    facts_json = EXCLUDED.facts_json,
                    approvals_json = EXCLUDED.approvals_json,
                    submissions_json = EXCLUDED.submissions_json,
                    verification_json = EXCLUDED.verification_json,
                    timeline_json = EXCLUDED.timeline_json,
                    updated_at = EXCLUDED.updated_at
                """
                with conn.cursor() as cur:
                    cur.execute(sql, params)
            else:
                sql = """
                INSERT OR REPLACE INTO applications (
                    application_id, tracking_reference, entity_name, status,
                    as_of, facts_json, approvals_json, submissions_json,
                    verification_json, timeline_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                conn.execute(sql, params)

    def get(self, application_id: str) -> Optional[ApplicationRecord]:
        with self._connection() as conn:
            if self.is_postgres:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("SELECT * FROM applications WHERE application_id = %s", (application_id,))
                    row = cur.fetchone()
                    if not row:
                        return None
                    return self._dict_row_to_record(row)
            else:
                cursor = conn.execute(
                    "SELECT * FROM applications WHERE application_id = ?",
                    (application_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return self._dict_row_to_record(row)

    def get_by_tracking_ref(self, tracking_ref: str) -> Optional[ApplicationRecord]:
        with self._connection() as conn:
            if self.is_postgres:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("SELECT * FROM applications WHERE tracking_reference = %s", (tracking_ref,))
                    row = cur.fetchone()
                    if not row:
                        return None
                    return self._dict_row_to_record(row)
            else:
                cursor = conn.execute(
                    "SELECT * FROM applications WHERE tracking_reference = ?",
                    (tracking_ref,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return self._dict_row_to_record(row)

    def all(self) -> List[ApplicationRecord]:
        with self._connection() as conn:
            if self.is_postgres:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("SELECT * FROM applications ORDER BY created_at DESC")
                    rows = cur.fetchall()
                    return [self._dict_row_to_record(r) for r in rows]
            else:
                cursor = conn.execute("SELECT * FROM applications ORDER BY created_at DESC")
                rows = cursor.fetchall()
                return [self._dict_row_to_record(r) for r in rows]

    # ------------------------------------------------------------------
    # Slice 4: department lifecycle persistence.
    #
    # These live on the same store and the same database as the Slice 3
    # application case on purpose. No second database abstraction is
    # introduced. Only lifecycle facts are written here: officer and applicant
    # text, states, and timestamps. Document binaries, raw document text, and
    # M5 extracted field values are never stored by any method below.
    # ------------------------------------------------------------------

    def _execute(self, sql: str, params: tuple = (), fetch: Optional[str] = None) -> Any:
        """Run one statement against either backend.

        ``sql`` is written with SQLite ``?`` placeholders and rewritten to
        ``%s`` for PostgreSQL, so every call site stays parameterised.
        """
        with self._lock, self._connection() as conn:
            if self.is_postgres:
                import psycopg2.extras
                statement = sql.replace("?", "%s")
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(statement, params)
                    if fetch == "one":
                        row = cur.fetchone()
                        return dict(row) if row is not None else None
                    if fetch == "all":
                        return [dict(r) for r in cur.fetchall()]
                    return None
            cursor = conn.execute(sql, params)
            if fetch == "one":
                row = cursor.fetchone()
                return dict(row) if row is not None else None
            if fetch == "all":
                return [dict(r) for r in cursor.fetchall()]
            return None

    def set_application_status(self, application_id: str, status: str, updated_at: str) -> None:
        self._execute(
            "UPDATE applications SET status = ?, updated_at = ? WHERE application_id = ?",
            (status, updated_at, application_id),
        )

    def upsert_approval_lifecycle(self, row: Dict[str, Any]) -> None:
        params = (
            row["application_id"], row["approval_id"], row["department"], row["status"],
            row.get("decision_note"), row.get("decided_at"),
            row["created_at"], row["updated_at"],
        )
        if self.is_postgres:
            sql = """
            INSERT INTO approval_lifecycle (
                application_id, approval_id, department, status,
                decision_note, decided_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (application_id, approval_id) DO UPDATE SET
                department = EXCLUDED.department,
                status = EXCLUDED.status,
                decision_note = EXCLUDED.decision_note,
                decided_at = EXCLUDED.decided_at,
                updated_at = EXCLUDED.updated_at
            """
        else:
            sql = """
            INSERT OR REPLACE INTO approval_lifecycle (
                application_id, approval_id, department, status,
                decision_note, decided_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
        self._execute(sql, params)

    def get_approval_lifecycle(self, application_id: str, approval_id: str) -> Optional[Dict[str, Any]]:
        return self._execute(
            "SELECT * FROM approval_lifecycle WHERE application_id = ? AND approval_id = ?",
            (application_id, approval_id),
            fetch="one",
        )

    def list_approval_lifecycle(self, application_id: str) -> List[Dict[str, Any]]:
        return self._execute(
            "SELECT * FROM approval_lifecycle WHERE application_id = ? ORDER BY approval_id",
            (application_id,),
            fetch="all",
        ) or []

    def save_query(self, row: Dict[str, Any]) -> None:
        params = (
            row["query_id"], row["application_id"], row["approval_id"], row["department"],
            row["query_text"], row["deadline"], row["status"],
            row.get("response_text"), row.get("response_document_id"), row.get("response_submission_id"),
            row.get("responded_at"), row.get("resolution_note"), row.get("resolved_at"),
            row["created_at"], row["updated_at"],
        )
        if self.is_postgres:
            sql = """
            INSERT INTO application_queries (
                query_id, application_id, approval_id, department, query_text, deadline, status,
                response_text, response_document_id, response_submission_id, responded_at,
                resolution_note, resolved_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (query_id) DO UPDATE SET
                status = EXCLUDED.status,
                query_text = EXCLUDED.query_text,
                deadline = EXCLUDED.deadline,
                response_text = EXCLUDED.response_text,
                response_document_id = EXCLUDED.response_document_id,
                response_submission_id = EXCLUDED.response_submission_id,
                responded_at = EXCLUDED.responded_at,
                resolution_note = EXCLUDED.resolution_note,
                resolved_at = EXCLUDED.resolved_at,
                updated_at = EXCLUDED.updated_at
            """
        else:
            sql = """
            INSERT OR REPLACE INTO application_queries (
                query_id, application_id, approval_id, department, query_text, deadline, status,
                response_text, response_document_id, response_submission_id, responded_at,
                resolution_note, resolved_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        self._execute(sql, params)

    def get_query(self, query_id: str) -> Optional[Dict[str, Any]]:
        return self._execute(
            "SELECT * FROM application_queries WHERE query_id = ?",
            (query_id,),
            fetch="one",
        )

    def list_queries(self, application_id: str) -> List[Dict[str, Any]]:
        return self._execute(
            "SELECT * FROM application_queries WHERE application_id = ? ORDER BY created_at",
            (application_id,),
            fetch="all",
        ) or []

    def append_event(self, row: Dict[str, Any]) -> None:
        self._execute(
            """
            INSERT INTO application_events (
                event_id, application_id, approval_id, department, actor, event_type, detail, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["event_id"], row["application_id"], row.get("approval_id"), row.get("department"),
                row["actor"], row["event_type"], row.get("detail"), row["created_at"],
            ),
        )

    def list_events(self, application_id: str) -> List[Dict[str, Any]]:
        return self._execute(
            "SELECT * FROM application_events WHERE application_id = ? ORDER BY created_at",
            (application_id,),
            fetch="all",
        ) or []

    def _dict_row_to_record(self, row: Any) -> ApplicationRecord:
        return ApplicationRecord(
            application_id=row["application_id"],
            tracking_reference=row["tracking_reference"],
            entity_name=row["entity_name"],
            status=row["status"],
            as_of=row["as_of"],
            facts=json.loads(row["facts_json"]),
            approvals=json.loads(row["approvals_json"]),
            submissions=json.loads(row["submissions_json"]),
            verification_records=json.loads(row["verification_json"]),
            timeline=json.loads(row["timeline_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


_store: Optional[ApplicationStore] = None


def get_application_store() -> ApplicationStore:
    global _store
    if _store is None:
        _store = ApplicationStore()
    return _store


def reset_application_store(path: Optional[Path] = None, database_url: Optional[str] = None):
    """Test hook for isolating or resetting store."""
    global _store
    if path is not None or database_url is not None:
        _store = ApplicationStore(path=path, database_url=database_url)
    else:
        _store = None
