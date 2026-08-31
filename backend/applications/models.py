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
    # Slice 4. Populated on read from the persisted lifecycle tables; never
    # written back into the stored case row, and never used to recompute any
    # upstream applicability, readiness, or verification result.
    lifecycle: Optional["ApplicationLifecycleView"] = None


class ApplicationListResponse(BaseModel):
    applications: List[ApplicationSummary]
    total_count: int


# ---------------------------------------------------------------------------
# Slice 4: prototype department lifecycle.
#
# Every state below is a simulation artefact. Nothing here records a real
# government filing, a real departmental decision, or any MAITRI interaction.
# ---------------------------------------------------------------------------


class ApprovalLifecycleView(BaseModel):
    approval_id: str
    name: Optional[str] = None
    department: str
    status: str
    decision_note: Optional[str] = None
    decided_at: Optional[str] = None
    # Established upstream values, echoed for presentation only.
    readiness_status: Optional[str] = None
    sla_days: Optional[int] = None
    statute: Optional[str] = None
    updated_at: Optional[str] = None


class QueryView(BaseModel):
    query_id: str
    application_id: str
    approval_id: str
    approval_name: Optional[str] = None
    department: str
    query_text: str
    deadline: str
    status: str
    response_text: Optional[str] = None
    response_document_id: Optional[str] = None
    response_submission_id: Optional[str] = None
    responded_at: Optional[str] = None
    resolution_note: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: str
    updated_at: str


class LifecycleEventView(BaseModel):
    event_id: str
    approval_id: Optional[str] = None
    department: Optional[str] = None
    actor: str
    event_type: str
    detail: Optional[str] = None
    created_at: str


class ApplicationLifecycleView(BaseModel):
    application_status: str
    reviewable_departments: List[str] = Field(default_factory=list)
    approvals: List[ApprovalLifecycleView] = Field(default_factory=list)
    queries: List[QueryView] = Field(default_factory=list)
    open_queries: List[QueryView] = Field(default_factory=list)
    events: List[LifecycleEventView] = Field(default_factory=list)
    simulation_notice: str = (
        "Department review, queries, and decisions in this prototype are a simulation. "
        "No application has been filed with any government department."
    )


class DepartmentInfo(BaseModel):
    department: str
    label: str


class DepartmentListResponse(BaseModel):
    departments: List[DepartmentInfo]


class DepartmentCaseSummary(BaseModel):
    """Officer-facing case row. Deliberately narrow.

    Applicant fact vectors, filenames, extracted document values, and raw
    document text are not carried by this model.
    """
    application_id: str
    tracking_reference: str
    entity_name: str
    application_status: str
    department: str
    approvals: List[ApprovalLifecycleView] = Field(default_factory=list)
    open_query_count: int = 0
    responded_query_count: int = 0
    submissions_count: int = 0
    last_activity_at: Optional[str] = None
    created_at: str


class DepartmentEvidenceItem(BaseModel):
    """A pointer to evidence, not the evidence itself.

    ``document_id`` identifies the checklist item and ``submission_reference``
    is an opaque handle. No extracted values, field contents, or document text
    are included.
    """
    document_id: str
    submission_reference: str
    evidence_state: Optional[str] = None
    automated_check_outcome: Optional[str] = None
    automated_check_consistency: Optional[str] = None


class DepartmentCaseDetail(BaseModel):
    application_id: str
    tracking_reference: str
    entity_name: str
    application_status: str
    department: str
    as_of: str
    approvals: List[ApprovalLifecycleView] = Field(default_factory=list)
    evidence: List[DepartmentEvidenceItem] = Field(default_factory=list)
    queries: List[QueryView] = Field(default_factory=list)
    timeline: Dict[str, Any] = Field(default_factory=dict)
    events: List[LifecycleEventView] = Field(default_factory=list)
    created_at: str
    updated_at: str
    evidence_notice: str = (
        "Automated checks indicate whether expected evidence is present and readable. "
        "They do not establish authenticity or government approval."
    )
    simulation_notice: str = (
        "This is a prototype department review simulation. No government decision is recorded here."
    )


class DepartmentCaseListResponse(BaseModel):
    department: str
    label: str
    cases: List[DepartmentCaseSummary] = Field(default_factory=list)
    total_count: int = 0
class StartReviewRequest(BaseModel):
    department: str = Field(..., description="Acting prototype department (DISH or FSSAI).")


class RaiseQueryRequest(BaseModel):
    approval_id: str
    department: str
    query_text: str
    deadline: str = Field(..., description="ISO date, YYYY-MM-DD.")


class RespondToQueryRequest(BaseModel):
    response_text: str
    response_document_id: Optional[str] = Field(
        default=None,
        description="Optional checklist item id for a replacement document already submitted through M4.",
    )
    response_submission_id: Optional[str] = Field(
        default=None,
        description="Optional existing M4 submission reference. No new document processing occurs.",
    )


class ResolveQueryRequest(BaseModel):
    department: str
    resolution_note: Optional[str] = None


class DecisionRequest(BaseModel):
    department: str
    decision_note: Optional[str] = None


class QueryListResponse(BaseModel):
    application_id: str
    queries: List[QueryView] = Field(default_factory=list)
    total_count: int = 0
