"""Data models for persistent application cases and tracking (Slice 3).

Stores references and snapshots of established assessment, approval,
readiness, and verification results without recomputing upstream logic.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ApprovalSnapshot(BaseModel):
    approval_id: str
    name: Optional[str] = None
    department: Optional[str] = None
    statute: Optional[str] = None
    sla_days: Optional[int] = None
    readiness_status: Optional[str] = None
    engine_state: Optional[str] = "APPLICABLE"


class SubmissionSnapshot(BaseModel):
    document_id: str
    submission_id: str
    filename: Optional[str] = None
    item_kind: Optional[str] = "UPLOAD_DOCUMENT"
    state: Optional[str] = "PROVIDED_UNVALIDATED"


class VerificationSnapshot(BaseModel):
    document_id: str
    record_id: Optional[str] = None
    disposition: Optional[str] = None
    internal_consistency: Optional[str] = None
    confidence_overall: Optional[float] = None


class ApplicationCreateRequest(BaseModel):
    application_id: Optional[str] = Field(
        default=None,
        description="Optional client-provided ID (e.g. local-assessment-id). If omitted, a UUID will be generated."
    )
    entity_name: str = Field(..., description="Legal business name of the applicant unit.")
    facts: Dict[str, Any] = Field(..., description="Snapshot of declared applicant fact vector.")
    as_of: Optional[str] = Field(default=None, description="Evaluation date (ISO format YYYY-MM-DD).")
    approvals: List[ApprovalSnapshot] = Field(default_factory=list, description="Applicable statutory approvals.")
    submissions: List[SubmissionSnapshot] = Field(default_factory=list, description="M4 submission references.")
    verification_records: List[VerificationSnapshot] = Field(default_factory=list, description="M5 verification references.")
    workflow_snapshot: Optional[Dict[str, Any]] = Field(default=None, description="Established M3 workflow schedule snapshot.")


class ApplicationSummary(BaseModel):
    application_id: str
    tracking_reference: str
    entity_name: str
    status: str
    as_of: str
    approvals_count: int
    ready_count: int
    submissions_count: int
    created_at: str
    updated_at: str


class ApplicationRecord(BaseModel):
    application_id: str
    tracking_reference: str
    entity_name: str
    status: str
    as_of: str
    facts: Dict[str, Any]
    approvals: List[Dict[str, Any]]
    submissions: List[Dict[str, Any]]
    verification_records: List[Dict[str, Any]]
    timeline: Dict[str, Any]
    created_at: str
    updated_at: str


class ApplicationListResponse(BaseModel):
    applications: List[ApplicationSummary]
    total_count: int
