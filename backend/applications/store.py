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
