"""Application Case Business Logic & Lifecycle Service (Slice 3).

Consumes already-established assessment and workflow snapshots.
Never recomputes upstream M1-M5 logic.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import (
    ApplicationCreateRequest,
    ApplicationRecord,
    ApplicationSummary,
)
from .store import get_application_store
from backend.documents.registry import get_document_registry

VALID_READINESS_STATUSES = frozenset({
    "READY", "INCOMPLETE", "INDETERMINATE", "UNSUPPORTED", "PENDING",
})


def _supported_approval_ids() -> frozenset[str]:
    """Return approval IDs from the existing M4 coverage registry.

    This is a read-only structural lookup; it does not evaluate facts or
    recompute applicability.
    """
    return frozenset(item.approval_id for item in get_document_registry().coverage())


def validate_application_request(request: ApplicationCreateRequest) -> None:
    """Validates that the application payload carries established upstream context.

    Prevents fabricated or empty payloads while trusting the established snapshot structure.
    Never invokes upstream engine, workflow, or M4/M5 recomputation.
    """
    if not request.entity_name or not request.entity_name.strip():
        raise ValueError("entity_name is required to create an application.")

    if not request.facts or not isinstance(request.facts, dict) or len(request.facts) == 0:
        raise ValueError("Application requires an established fact vector from the assessment.")

    if not request.approvals or len(request.approvals) == 0:
        raise ValueError("Application requires at least one established statutory approval.")

    for appr in request.approvals:
        aid = appr.approval_id if hasattr(appr, "approval_id") else appr.get("approval_id")
        if not aid or not str(aid).strip():
            raise ValueError("All approval snapshots must specify a non-empty approval_id.")
        aid_str = str(aid)
        if aid_str not in _supported_approval_ids():
            raise ValueError(f"Approval ID '{aid_str}' is not recognized in the prototype approval set.")

        r_status = appr.readiness_status if hasattr(appr, "readiness_status") else appr.get("readiness_status")
        if r_status is not None and r_status not in VALID_READINESS_STATUSES:
            raise ValueError(f"Invalid readiness status '{r_status}'. Must be one of: {sorted(VALID_READINESS_STATUSES)}.")

    if request.submissions:
        for sub in request.submissions:
            doc_id = sub.document_id if hasattr(sub, "document_id") else sub.get("document_id")
            sub_id = sub.submission_id if hasattr(sub, "submission_id") else sub.get("submission_id")
            if not doc_id or not sub_id:
                raise ValueError("All submission references must specify both document_id and submission_id.")

    if request.verification_records:
        for ver in request.verification_records:
            doc_id = ver.document_id if hasattr(ver, "document_id") else ver.get("document_id")
            if not doc_id:
                raise ValueError("All verification references must specify document_id.")

    if request.workflow_snapshot is not None and not isinstance(request.workflow_snapshot, dict):
        raise ValueError("workflow_snapshot must be a dictionary snapshot if provided.")


def _build_human_timeline(workflow_snapshot: Optional[Dict[str, Any]], approvals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Formats M3 schedule / graph data into a simplified, applicant-friendly 2-phase timeline.

    Phase 1: Immediate Clearances (Can Start Now — no admitted legal prerequisites).
    Phase 2: Sequential Clearances (After Preconditions — e.g. Factory Licence after Building Approval).
    """
    phase1_items: List[Dict[str, Any]] = []
    phase2_items: List[Dict[str, Any]] = []

    # Map approval metadata
    appr_map = {a.get("approval_id"): a for a in approvals}

    # Inspect workflow schedule nodes if provided
    schedule_nodes = {}
    if workflow_snapshot and isinstance(workflow_snapshot, dict):
        schedule = workflow_snapshot.get("schedule") or {}
        schedule_nodes = schedule.get("nodes") or {}

    for approval in approvals:
        aid = approval.get("approval_id")
        sn = schedule_nodes.get(aid, {})
        blocked_by = sn.get("blocked_by", [])
        depth = sn.get("depth", 0)

        item = {
            "approval_id": aid,
            "name": approval.get("name") or aid,
            "department": approval.get("department") or "State Authority",
            "sla_days": approval.get("sla_days"),
            "readiness_status": approval.get("readiness_status", "READY"),
            "blocked_by": blocked_by,
        }

        if blocked_by or depth > 0:
            item["precondition_note"] = f"Requires prior approval: {', '.join(blocked_by)}"
            phase2_items.append(item)
        else:
            item["precondition_note"] = "Can be filed immediately in parallel"
            phase1_items.append(item)

    return {
        "summary": "Parallel & Sequential Clearances Timeline",
        "total_approvals": len(approvals),
        "phase_1_immediate": {
            "phase_number": 1,
            "title": "Phase 1: Immediate Clearances (Can Start Now)",
            "description": "Statutory registrations and consents that can be initiated in parallel.",
            "count": len(phase1_items),
            "items": phase1_items,
        },
        "phase_2_sequential": {
            "phase_number": 2,
            "title": "Phase 2: Sequential Clearances (After Preconditions)",
            "description": "Operating licences gated by site plan or prior construction approvals.",
            "count": len(phase2_items),
            "items": phase2_items,
        },
    }


def create_application_case(request: ApplicationCreateRequest) -> ApplicationRecord:
    validate_application_request(request)
    store = get_application_store()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Determine or generate canonical application ID
    app_id = request.application_id or f"APP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

    # Check for existing application
    existing = store.get(app_id)
    tracking_ref = existing.tracking_reference if existing else store.next_tracking_reference()

    # Convert request models to dictionaries
    def _to_dict(obj):
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        return obj

    approvals_data = [_to_dict(a) for a in request.approvals]
    submissions_data = [_to_dict(s) for s in request.submissions]
    verification_data = [_to_dict(v) for v in request.verification_records]

    # Build human timeline from M3 snapshot
    timeline = _build_human_timeline(request.workflow_snapshot, approvals_data)

    as_of = request.as_of or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    record = ApplicationRecord(
        application_id=app_id,
        tracking_reference=tracking_ref,
        entity_name=request.entity_name,
        status="SUBMITTED",
        as_of=as_of,
        facts=request.facts,
        approvals=approvals_data,
        submissions=submissions_data,
        verification_records=verification_data,
        timeline=timeline,
        created_at=existing.created_at if existing else now_iso,
        updated_at=now_iso,
    )

    store.save(record)
    return record


def get_application_case(application_id: str) -> Optional[ApplicationRecord]:
    record = get_application_store().get(application_id)
    if record is None:
        return None
    # Slice 4: attach the persisted department lifecycle so the applicant
    # dashboard sees review progress and open queries in one read. This reads
    # lifecycle tables only; no upstream evaluation is triggered and nothing
    # the engine, M3, M4, or M5 established is altered.
    from .lifecycle_service import build_lifecycle_view

    record.lifecycle = build_lifecycle_view(record)
    return record


def list_application_cases() -> List[ApplicationSummary]:
    records = get_application_store().all()
    summaries = []
    for r in records:
        ready_count = sum(1 for a in r.approvals if a.get("readiness_status") == "READY")
        summaries.append(
            ApplicationSummary(
                application_id=r.application_id,
                tracking_reference=r.tracking_reference,
                entity_name=r.entity_name,
                status=r.status,
                as_of=r.as_of,
                approvals_count=len(r.approvals),
                ready_count=ready_count,
                submissions_count=len(r.submissions),
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )
    return summaries
