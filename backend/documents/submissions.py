"""M4 submission metadata and safe local quarantine storage."""

import hashlib
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from .models import DocumentSubmission

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_MIME_TYPES = frozenset({"application/pdf", "image/jpeg", "image/png"})
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(filename: str) -> str:
    name = Path(str(filename or "upload")).name
    name = _SAFE_NAME.sub("_", name).strip("._")
    return (name or "upload")[:160]


class SubmissionStore:
    def __init__(self):
        self.items: Dict[str, DocumentSubmission] = {}
        self.by_hash: Dict[tuple, str] = {}
        self.root = Path(tempfile.gettempdir()) / "regulatory-engine-m4-uploads"
        self.root.mkdir(parents=True, exist_ok=True)

    def submit_bytes(self, application_id: str, document_id: str, filename: str, content: bytes, mime_type: str, spec=None):
        if not application_id or not document_id:
            raise ValueError("application_id and document_id are required")
        if spec is not None and spec.item_kind != "UPLOAD_DOCUMENT":
            raise ValueError(f"document_id {document_id!r} is not an upload document")
        if len(content) > MAX_UPLOAD_BYTES:
            raise ValueError(f"upload exceeds maximum size of {MAX_UPLOAD_BYTES} bytes")
        if mime_type not in ALLOWED_MIME_TYPES:
            raise ValueError("unsupported MIME type")
        safe = safe_filename(filename)
        digest = hashlib.sha256(content).hexdigest()
        existing = self.by_hash.get((application_id, document_id, digest))
        if existing:
            return self.items[existing], True
        sid = str(uuid.uuid4())
        key = f"{sid}-{safe}"
        (self.root / key).write_bytes(content)
        item = DocumentSubmission(
            submission_id=sid, document_id=document_id, application_id=application_id,
            filename=safe, sha256=digest, size_bytes=len(content), mime_type=mime_type,
            uploaded_at=datetime.now(timezone.utc).isoformat(), state="PROVIDED_UNVALIDATED",
            storage_key=key,
        )
        self.items[sid] = item
        self.by_hash[(application_id, document_id, digest)] = sid
        return item, False

    def submit_structured(self, application_id: str, document_id: str, structured_data: dict, spec=None):
        if not application_id or not document_id:
            raise ValueError("application_id and document_id are required")
        if spec is not None and spec.item_kind == "UPLOAD_DOCUMENT":
            raise ValueError(f"document_id {document_id!r} requires a file upload")
        sid = str(uuid.uuid4())
        item = DocumentSubmission(
            submission_id=sid, document_id=document_id, application_id=application_id,
            uploaded_at=datetime.now(timezone.utc).isoformat(), state="PROVIDED_UNVALIDATED",
            structured_data=dict(structured_data or {}),
        )
        self.items[sid] = item
        return item, False

    def for_application(self, application_id: str):
        return [s for s in self.items.values() if s.application_id == application_id]


_store: Optional[SubmissionStore] = None


def get_submission_store():
    global _store
    if _store is None:
        _store = SubmissionStore()
    return _store
