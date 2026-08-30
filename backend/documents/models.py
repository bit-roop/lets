"""Typed transport models for M4.  They do not decide applicability."""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

VERIFICATION_STATES = frozenset({"VERIFIED", "VERIFIED_SCOPE_UNCLEAR", "SECONDARY", "UNSUPPORTED"})
READINESS_STATES = frozenset({"READY", "INCOMPLETE", "INDETERMINATE", "UNSUPPORTED"})
SUBMISSION_STATES = frozenset({"NOT_PROVIDED", "PROVIDED_UNVALIDATED", "VALID", "INVALID", "NEEDS_REVIEW", "REUSED_FROM"})
ITEM_KINDS = frozenset({"UPLOAD_DOCUMENT", "FORM_INPUT", "FEE", "INSPECTION_EVENT", "DECLARATION"})
OBLIGATIONS = frozenset({"MANDATORY", "CONDITIONAL", "SUPPORTING"})


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    authority: str
    title: str
    url: Optional[str]
    checklist_item: Optional[str]
    verification_status: str
    last_verified: Optional[str]
    currentness: str = "CURRENTNESS_REQUIRES_RECHECK"
    section: Optional[str] = None
    notes: Optional[str] = None

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class DocumentSpec:
    document_id: str
    name: str
    item_kind: str
    description: str
    accepted_formats: List[str] = field(default_factory=list)
    reusable: bool = False
    validator: Optional[str] = None
    provenance: Optional[SourceRef] = None

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class DocumentRequirement:
    requirement_id: str
    approval_id: str
    document_id: str
    obligation: str
    condition: Optional[Dict[str, Any]]
    condition_description: Optional[str]
    blocking: bool
    verification_status: str
    source: SourceRef
    notes: Optional[str] = None

    def as_dict(self):
        return asdict(self)


@dataclass
class DocumentSubmission:
    submission_id: str
    document_id: str
    application_id: str
    filename: Optional[str] = None
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_at: Optional[str] = None
    state: str = "NOT_PROVIDED"
    structured_data: Dict[str, Any] = field(default_factory=dict)
    storage_key: Optional[str] = None
    validation: Optional[Dict[str, Any]] = None
    reused_from: Optional[str] = None

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Coverage:
    approval_id: str
    status: str
    reason: str
    requirement_count: int
    source_ids: List[str] = field(default_factory=list)

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Readiness:
    approval_id: str
    status: str
    mandatory_total: int
    mandatory_satisfied: int
    missing_requirement_ids: List[str] = field(default_factory=list)
    indeterminate_requirement_ids: List[str] = field(default_factory=list)
    unsupported_requirement_ids: List[str] = field(default_factory=list)
    supporting_missing_requirement_ids: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ReuseLink:
    submission_id: str
    requirement_id: str
    document_id: str
    basis: str
    status: str

    def as_dict(self):
        return asdict(self)
