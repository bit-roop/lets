"""Durable VerificationRecord storage on SQLite (stdlib only).

What is deliberately NOT stored: document bytes, page images, raw extracted
text, and any unmasked sensitive identifier.  M5 references M4's stored file by
submission_id and sha256; it never makes a second permanent copy of an
applicant's document.

file_identity is keyed on sha256 alone, not on M4's
(application_id, document_id, sha256) dedup tuple.  Keying on M4's tuple would
make the same file submitted into two different evidence slots invisible as
reuse, which is precisely the case worth detecting.  No UNIQUE constraint:
multiple rows per hash IS the signal.
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import RETENTION_DAYS, STORE_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS verification_records (
    record_id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL,
    application_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    submission_sha256 TEXT,
    disposition TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_records_application ON verification_records(application_id);
CREATE INDEX IF NOT EXISTS idx_records_submission ON verification_records(submission_id);

CREATE TABLE IF NOT EXISTS file_identity (
    sha256 TEXT NOT NULL,
    submission_id TEXT NOT NULL,
    application_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    first_seen TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_file_identity_sha ON file_identity(sha256);
"""


class RecordStore:
    def __init__(self, path: Path = STORE_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
        self.sweep_expired()

    def _connect(self):
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, record) -> None:
        payload = record.as_dict()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO verification_records "
                "(record_id, submission_id, application_id, document_id, "
                " submission_sha256, disposition, created_at, expires_at, payload) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (record.record_id, record.submission_id, record.application_id,
                 record.document_id, record.submission_sha256, record.disposition,
                 record.created_at, record.expires_at, json.dumps(payload)))
            if record.submission_sha256:
                existing = conn.execute(
                    "SELECT 1 FROM file_identity WHERE sha256=? AND submission_id=?",
                    (record.submission_sha256, record.submission_id)).fetchone()
                if existing is None:
                    conn.execute(
                        "INSERT INTO file_identity "
                        "(sha256, submission_id, application_id, document_id, first_seen) "
                        "VALUES (?,?,?,?,?)",
                        (record.submission_sha256, record.submission_id,
                         record.application_id, record.document_id, record.created_at))

    def latest_for_submission(self, submission_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM verification_records WHERE submission_id=? "
                "ORDER BY created_at DESC LIMIT 1", (submission_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def for_application(self, application_id: str) -> List[Dict[str, Any]]:
        """Latest record per submission for one application."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload, submission_id, created_at FROM verification_records "
                "WHERE application_id=? ORDER BY created_at ASC", (application_id,)
            ).fetchall()
        latest: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            latest[row["submission_id"]] = json.loads(row["payload"])
        return [latest[k] for k in sorted(latest)]

    def sightings_for_hash(self, sha256: str) -> List[Dict[str, Any]]:
        """All slots this exact file has been seen in. Used from Phase E onward."""
        if not sha256:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT submission_id, application_id, document_id, first_seen "
                "FROM file_identity WHERE sha256=? ORDER BY first_seen ASC",
                (sha256,)).fetchall()
        return [dict(r) for r in rows]

    def sweep_expired(self) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM verification_records WHERE expires_at < ?", (now,))
            return cursor.rowcount or 0


def retention_window():
    created = datetime.now(timezone.utc)
    return created.isoformat(), (created + timedelta(days=RETENTION_DAYS)).isoformat()


_store: Optional[RecordStore] = None


def get_record_store() -> RecordStore:
    global _store
    if _store is None:
        _store = RecordStore()
    return _store


def reset_record_store(path: Optional[Path] = None):
    """Test hook only."""
    global _store
    _store = RecordStore(path) if path else None
