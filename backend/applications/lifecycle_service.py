"""Slice 4 service: prototype department review over a persisted case.

Everything in this module reads the application case that Slice 3 already
stored. Applicability came from engine-v3 (M2), sequencing from M3, document
requirements and readiness from M4, and document findings from M5. Slice 4
consumes those results and never re-derives them.

There are no imports of ``backend.engine_adapter``, ``backend.workflow``,
``backend.documents``, or ``backend.verification`` anywhere in this file, and
the Slice 4 test suite sabotages those functions to prove the lifecycle keeps
working without them.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from .lifecycle import (
    APPROVAL_GRANTED,
    APPROVAL_IN_SCRUTINY,
    APPROVAL_QUERY_PENDING,
    APPROVAL_REJECTED,
    APPROVAL_SUBMITTED,
    DEPARTMENT_LABELS,
    EVENT_APPROVAL_GRANTED,
    EVENT_APPROVAL_REJECTED,
    EVENT_QUERY_RAISED,
    EVENT_QUERY_RESOLVED,
    EVENT_QUERY_RESPONDED,
    EVENT_REVIEW_STARTED,
    PROTOTYPE_DEPARTMENTS,
    QUERY_OPEN,
    QUERY_RESOLVED,
    QUERY_RESPONDED,
    InvalidTransition,
    LifecycleForbidden,
    LifecycleNotFound,
    LifecycleValidation,
    assert_approval_transition,
    assert_query_transition,
    department_of_approval,
    derive_application_status,
    is_prototype_department,
    normalise_department,
    validate_deadline,
    validate_text,
)
from .models import (
    ApplicationLifecycleView,
    ApprovalLifecycleView,
    DepartmentCaseDetail,
    DepartmentCaseListResponse,
    DepartmentCaseSummary,
    DepartmentEvidenceItem,
    DepartmentInfo,
    LifecycleEventView,
    QueryView,
)
from .store import get_application_store


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_department(value: Optional[str]) -> str:
    department = normalise_department(value)
    if department not in PROTOTYPE_DEPARTMENTS:
        raise LifecycleValidation(
            f"'{value}' is not a simulated department. Supported: {', '.join(sorted(PROTOTYPE_DEPARTMENTS))}."
        )
    return department


def _load_case(application_id: str):
    record = get_application_store().get(application_id)
    if record is None:
        raise LifecycleNotFound(f"Application case '{application_id}' does not exist.")
    return record


def _approval_snapshot(record, approval_id: str) -> Mapping[str, Any]:
    for approval in record.approvals:
        if approval.get("approval_id") == approval_id:
            return approval
    raise LifecycleNotFound(
        f"Approval '{approval_id}' is not part of application '{record.application_id}'."
    )


def _ensure_lifecycle_row(record, approval_id: str) -> Dict[str, Any]:
    """Return the persisted lifecycle row, creating the SUBMITTED row on demand.

    A case filed before Slice 4, or one never yet opened by an officer, has no
    row. The default is SUBMITTED, which is where Slice 3 already placed it.
    """
    store = get_application_store()
    snapshot = _approval_snapshot(record, approval_id)
    department = department_of_approval(snapshot)
    if not is_prototype_department(department):
        raise LifecycleForbidden(
            f"Approval '{approval_id}' belongs to '{department}', which is not simulated in this prototype."
        )
    row = store.get_approval_lifecycle(record.application_id, approval_id)
    if row is None:
        now = _now()
        row = {
            "application_id": record.application_id,
            "approval_id": approval_id,
            "department": department,
            "status": APPROVAL_SUBMITTED,
            "decision_note": None,
            "decided_at": None,
            "created_at": now,
            "updated_at": now,
        }
        store.upsert_approval_lifecycle(row)
    return dict(row)


def _states_for(record, rows: List[Dict[str, Any]]) -> Dict[str, str]:
    """Status of every reviewable approval in the case.

    An approval no officer has opened has no persisted row yet. It still counts
    as outstanding, so it defaults to SUBMITTED rather than being omitted;
    otherwise a case could report GRANTED while another department had not even
    looked at it.
    """
    by_id = {r["approval_id"]: r["status"] for r in rows}
    states: Dict[str, str] = {}
    for snapshot in record.approvals:
        approval_id = snapshot.get("approval_id")
        if not approval_id or not is_prototype_department(snapshot.get("department")):
            continue
        states[approval_id] = by_id.get(approval_id, APPROVAL_SUBMITTED)
    return states


def _record_event(
    application_id: str,
    actor: str,
    event_type: str,
    detail: Optional[str] = None,
    approval_id: Optional[str] = None,
    department: Optional[str] = None,
) -> None:
    get_application_store().append_event({
        "event_id": f"EVT-{uuid.uuid4().hex[:12]}",
        "application_id": application_id,
        "approval_id": approval_id,
        "department": department,
        "actor": actor,
        "event_type": event_type,
        "detail": detail,
        "created_at": _now(),
    })


def _refresh_application_status(record) -> str:
    """Recompute and persist the aggregate application status.

    This aggregates persisted lifecycle rows only. It touches nothing that any
    upstream milestone produced.
    """
    store = get_application_store()
    rows = store.list_approval_lifecycle(record.application_id)
    queries = store.list_queries(record.application_id)
    status = derive_application_status(_states_for(record, rows), queries)
    store.set_application_status(record.application_id, status, _now())
    return status


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


def _query_view(row: Mapping[str, Any], approval_names: Mapping[str, str]) -> QueryView:
    return QueryView(
        query_id=row["query_id"],
        application_id=row["application_id"],
        approval_id=row["approval_id"],
        approval_name=approval_names.get(row["approval_id"]),
        department=row["department"],
        query_text=row["query_text"],
        deadline=row["deadline"],
        status=row["status"],
        response_text=row.get("response_text"),
        response_document_id=row.get("response_document_id"),
        response_submission_id=row.get("response_submission_id"),
        responded_at=row.get("responded_at"),
        resolution_note=row.get("resolution_note"),
        resolved_at=row.get("resolved_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _approval_views(record, rows: List[Dict[str, Any]]) -> List[ApprovalLifecycleView]:
    by_id = {r["approval_id"]: r for r in rows}
    views: List[ApprovalLifecycleView] = []
    for snapshot in record.approvals:
        approval_id = snapshot.get("approval_id")
        department = department_of_approval(snapshot)
        if not is_prototype_department(department):
            continue
        row = by_id.get(approval_id)
        views.append(ApprovalLifecycleView(
            approval_id=approval_id,
            name=snapshot.get("name"),
            department=department,
            status=row["status"] if row else APPROVAL_SUBMITTED,
            decision_note=row.get("decision_note") if row else None,
            decided_at=row.get("decided_at") if row else None,
            # Values below were established upstream and are echoed unchanged.
            readiness_status=snapshot.get("readiness_status"),
            sla_days=snapshot.get("sla_days"),
            statute=snapshot.get("statute"),
            updated_at=row.get("updated_at") if row else None,
        ))
    return views


def build_lifecycle_view(record) -> ApplicationLifecycleView:
    """Assemble the applicant-facing lifecycle block for a stored case."""
    store = get_application_store()
    rows = store.list_approval_lifecycle(record.application_id)
    approval_names = {
        a.get("approval_id"): a.get("name") for a in record.approvals if a.get("approval_id")
    }
    query_rows = store.list_queries(record.application_id)
    queries = [_query_view(q, approval_names) for q in query_rows]
    events = [
        LifecycleEventView(
            event_id=e["event_id"],
            approval_id=e.get("approval_id"),
            department=e.get("department"),
            actor=e["actor"],
            event_type=e["event_type"],
            detail=e.get("detail"),
            created_at=e["created_at"],
        )
        for e in store.list_events(record.application_id)
    ]
    approvals = _approval_views(record, rows)
    return ApplicationLifecycleView(
        application_status=derive_application_status(_states_for(record, rows), query_rows),
        reviewable_departments=sorted({a.department for a in approvals}),
        approvals=approvals,
        queries=queries,
        open_queries=[q for q in queries if q.status in (QUERY_OPEN, QUERY_RESPONDED)],
        events=events,
    )


def list_departments() -> List[DepartmentInfo]:
    return [
        DepartmentInfo(department=code, label=DEPARTMENT_LABELS[code])
        for code in sorted(PROTOTYPE_DEPARTMENTS)
    ]


def list_department_cases(department: str) -> DepartmentCaseListResponse:
    """List filed prototype cases that carry at least one approval for this department."""
    dept = _require_department(department)
    store = get_application_store()
    cases: List[DepartmentCaseSummary] = []

    for record in store.all():
        owned = [
            a for a in record.approvals
            if department_of_approval(a) == dept
        ]
        if not owned:
            continue
        rows = store.list_approval_lifecycle(record.application_id)

        approvals = [v for v in _approval_views(record, rows) if v.department == dept]
        queries = [q for q in store.list_queries(record.application_id) if q["department"] == dept]
        events = store.list_events(record.application_id)
        cases.append(DepartmentCaseSummary(
            application_id=record.application_id,
            tracking_reference=record.tracking_reference,
            entity_name=record.entity_name,
            application_status=derive_application_status(
                _states_for(record, rows), store.list_queries(record.application_id)
            ),
            department=dept,
            approvals=approvals,
            open_query_count=sum(1 for q in queries if q["status"] == QUERY_OPEN),
            responded_query_count=sum(1 for q in queries if q["status"] == QUERY_RESPONDED),
            submissions_count=len(record.submissions),
            last_activity_at=events[-1]["created_at"] if events else record.updated_at,
            created_at=record.created_at,
        ))


    return DepartmentCaseListResponse(
        department=dept,
        label=DEPARTMENT_LABELS[dept],
        cases=cases,
        total_count=len(cases),
    )


def _evidence_items(record) -> List[DepartmentEvidenceItem]:
    """Build the officer evidence list from stored references only.

    The stored case holds M4 submission references and M5 outcome labels. It
    holds no document bytes, no document text, and no extracted field values,
    so none can leak here. Filenames are withheld from the officer view as
    well: they are applicant-supplied free text and add nothing to a review
    that already identifies the checklist item.
    """
    verification_by_doc: Dict[str, Dict[str, Any]] = {}
    for entry in record.verification_records:
        document_id = entry.get("document_id")
        if document_id:
            verification_by_doc[document_id] = entry

    items: List[DepartmentEvidenceItem] = []
    for submission in record.submissions:
        document_id = submission.get("document_id")
        if not document_id:
            continue
        finding = verification_by_doc.get(document_id, {})
        items.append(DepartmentEvidenceItem(
            document_id=document_id,
            submission_reference=str(submission.get("submission_id") or "")[:12] or "unavailable",
            evidence_state=submission.get("state"),
            automated_check_outcome=finding.get("disposition"),
            automated_check_consistency=finding.get("internal_consistency"),
        ))
    return items


def get_department_case(department: str, application_id: str) -> DepartmentCaseDetail:
    dept = _require_department(department)
    record = _load_case(application_id)
    owned = [a for a in record.approvals if department_of_approval(a) == dept]
    if not owned:
        raise LifecycleForbidden(
            f"Application '{application_id}' carries no approval owned by {dept}."
        )
    store = get_application_store()
    rows = store.list_approval_lifecycle(record.application_id)
    approval_names = {
        a.get("approval_id"): a.get("name") for a in record.approvals if a.get("approval_id")
    }
    approvals = [v for v in _approval_views(record, rows) if v.department == dept]
    queries = [
        _query_view(q, approval_names)
        for q in store.list_queries(record.application_id)
        if q["department"] == dept
    ]
    events = [
        LifecycleEventView(
            event_id=e["event_id"],
            approval_id=e.get("approval_id"),
            department=e.get("department"),
            actor=e["actor"],
            event_type=e["event_type"],
            detail=e.get("detail"),
            created_at=e["created_at"],
        )
        for e in store.list_events(record.application_id)
    ]
    return DepartmentCaseDetail(
        application_id=record.application_id,
        tracking_reference=record.tracking_reference,
        entity_name=record.entity_name,
        application_status=derive_application_status(
            _states_for(record, rows), store.list_queries(record.application_id)
        ),
        department=dept,
        as_of=record.as_of,
        approvals=approvals,
        evidence=_evidence_items(record),
        queries=queries,
        # The M3 schedule snapshot the case was filed with, shown for timeline
        # context. It is not rebuilt and no SLA value is recomputed.
        timeline=record.timeline or {},
        events=events,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


# ---------------------------------------------------------------------------
# Officer actions
# ---------------------------------------------------------------------------


def _guard_department_owns(row: Mapping[str, Any], department: str) -> None:
    if normalise_department(row["department"]) != department:
        raise LifecycleForbidden(
            f"{department} cannot act on an approval owned by {row['department']}."
        )


def start_review(application_id: str, approval_id: str, department: str) -> ApprovalLifecycleView:
    dept = _require_department(department)
    record = _load_case(application_id)
    row = _ensure_lifecycle_row(record, approval_id)
    _guard_department_owns(row, dept)
    assert_approval_transition(row["status"], APPROVAL_IN_SCRUTINY)

    row["status"] = APPROVAL_IN_SCRUTINY
    row["updated_at"] = _now()
    get_application_store().upsert_approval_lifecycle(row)
    _record_event(
        application_id, actor="OFFICER", event_type=EVENT_REVIEW_STARTED,
        detail=f"Scrutiny opened for {approval_id} in simulation.",
        approval_id=approval_id, department=dept,
    )
    _refresh_application_status(record)
    return _single_approval_view(record, approval_id)


def raise_query(
    application_id: str,
    approval_id: str,
    department: str,
    query_text: str,
    deadline: str,
) -> QueryView:
    dept = _require_department(department)
    text = validate_text(query_text, "Query text")
    due = validate_deadline(deadline)
    record = _load_case(application_id)
    row = _ensure_lifecycle_row(record, approval_id)
    _guard_department_owns(row, dept)
    assert_approval_transition(row["status"], APPROVAL_QUERY_PENDING)

    store = get_application_store()
    now = _now()
    query_row = {
        "query_id": f"QRY-{uuid.uuid4().hex[:12]}",
        "application_id": application_id,
        "approval_id": approval_id,
        "department": dept,
        "query_text": text,
        "deadline": due,
        "status": QUERY_OPEN,
        "response_text": None,
        "response_document_id": None,
        "response_submission_id": None,
        "responded_at": None,
        "resolution_note": None,
        "resolved_at": None,
        "created_at": now,
        "updated_at": now,
    }
    store.save_query(query_row)

    row["status"] = APPROVAL_QUERY_PENDING
    row["updated_at"] = now
    store.upsert_approval_lifecycle(row)
    _record_event(
        application_id, actor="OFFICER", event_type=EVENT_QUERY_RAISED,
        detail=f"Query raised on {approval_id}; response due {due}.",
        approval_id=approval_id, department=dept,
    )
    _refresh_application_status(record)

    names = {a.get("approval_id"): a.get("name") for a in record.approvals}
    return _query_view(query_row, names)


def list_queries(application_id: str, department: Optional[str] = None) -> List[QueryView]:
    record = _load_case(application_id)
    names = {a.get("approval_id"): a.get("name") for a in record.approvals}
    rows = get_application_store().list_queries(application_id)
    if department:
        dept = _require_department(department)
        rows = [r for r in rows if r["department"] == dept]
    return [_query_view(r, names) for r in rows]


def get_query(application_id: str, query_id: str) -> QueryView:
    record = _load_case(application_id)
    row = get_application_store().get_query(query_id)
    if row is None or row["application_id"] != application_id:
        raise LifecycleNotFound(f"Query '{query_id}' does not exist for this application.")
    names = {a.get("approval_id"): a.get("name") for a in record.approvals}
    return _query_view(row, names)


def respond_to_query(
    application_id: str,
    query_id: str,
    response_text: str,
    response_document_id: Optional[str] = None,
    response_submission_id: Optional[str] = None,
) -> QueryView:
    """Applicant response.

    A replacement document is referenced, never processed. The applicant
    re-submits through the existing M4 submission endpoint if they need to; all
    that is recorded here is the reference to that existing submission.
    """
    text = validate_text(response_text, "Response text")
    record = _load_case(application_id)
    store = get_application_store()
    row = store.get_query(query_id)
    if row is None or row["application_id"] != application_id:
        raise LifecycleNotFound(f"Query '{query_id}' does not exist for this application.")
    assert_query_transition(row["status"], QUERY_RESPONDED)

    if response_submission_id is not None:
        known = {s.get("submission_id") for s in record.submissions}
        if response_submission_id not in known:
            raise LifecycleValidation(
                "The referenced replacement submission is not attached to this application case."
            )

    now = _now()
    row = dict(row)
    row.update({
        "status": QUERY_RESPONDED,
        "response_text": text,
        "response_document_id": response_document_id,
        "response_submission_id": response_submission_id,
        "responded_at": now,
        "updated_at": now,
    })
    store.save_query(row)
    _record_event(
        application_id, actor="APPLICANT", event_type=EVENT_QUERY_RESPONDED,
        detail=f"Applicant responded to the query on {row['approval_id']}.",
        approval_id=row["approval_id"], department=row["department"],
    )
    _refresh_application_status(record)

    names = {a.get("approval_id"): a.get("name") for a in record.approvals}
    return _query_view(row, names)


def resolve_query(
    application_id: str,
    query_id: str,
    department: str,
    resolution_note: Optional[str] = None,
) -> QueryView:
    """Officer accepts the response and returns the approval to scrutiny."""
    dept = _require_department(department)
    note = validate_text(resolution_note, "Resolution note", required=False)
    record = _load_case(application_id)
    store = get_application_store()
    row = store.get_query(query_id)
    if row is None or row["application_id"] != application_id:
        raise LifecycleNotFound(f"Query '{query_id}' does not exist for this application.")
    _guard_department_owns(row, dept)
    assert_query_transition(row["status"], QUERY_RESOLVED)

    now = _now()
    row = dict(row)
    row.update({
        "status": QUERY_RESOLVED,
        "resolution_note": note or None,
        "resolved_at": now,
        "updated_at": now,
    })
    store.save_query(row)

    approval_row = _ensure_lifecycle_row(record, row["approval_id"])
    if approval_row["status"] == APPROVAL_QUERY_PENDING:
        assert_approval_transition(approval_row["status"], APPROVAL_IN_SCRUTINY)
        approval_row["status"] = APPROVAL_IN_SCRUTINY
        approval_row["updated_at"] = now
        store.upsert_approval_lifecycle(approval_row)

    _record_event(
        application_id, actor="OFFICER", event_type=EVENT_QUERY_RESOLVED,
        detail=f"Response accepted; {row['approval_id']} returned to scrutiny.",
        approval_id=row["approval_id"], department=dept,
    )
    _refresh_application_status(record)

    names = {a.get("approval_id"): a.get("name") for a in record.approvals}
    return _query_view(row, names)


def _decide(
    application_id: str,
    approval_id: str,
    department: str,
    target_state: str,
    decision_note: Optional[str],
) -> ApprovalLifecycleView:
    dept = _require_department(department)
    note = validate_text(decision_note, "Decision note", required=False)
    record = _load_case(application_id)
    row = _ensure_lifecycle_row(record, approval_id)
    _guard_department_owns(row, dept)
    assert_approval_transition(row["status"], target_state)

    now = _now()
    row["status"] = target_state
    row["decision_note"] = note or None
    row["decided_at"] = now
    row["updated_at"] = now
    get_application_store().upsert_approval_lifecycle(row)

    event_type = EVENT_APPROVAL_GRANTED if target_state == APPROVAL_GRANTED else EVENT_APPROVAL_REJECTED
    verb = "granted" if target_state == APPROVAL_GRANTED else "rejected"
    _record_event(
        application_id, actor="OFFICER", event_type=event_type,
        detail=f"Prototype department decision: {approval_id} {verb} in simulation.",
        approval_id=approval_id, department=dept,
    )
    _refresh_application_status(record)
    return _single_approval_view(record, approval_id)


def grant_approval(application_id: str, approval_id: str, department: str, decision_note: Optional[str] = None):
    return _decide(application_id, approval_id, department, APPROVAL_GRANTED, decision_note)


def reject_approval(application_id: str, approval_id: str, department: str, decision_note: Optional[str] = None):
    return _decide(application_id, approval_id, department, APPROVAL_REJECTED, decision_note)


def _single_approval_view(record, approval_id: str) -> ApprovalLifecycleView:
    rows = get_application_store().list_approval_lifecycle(record.application_id)
    for view in _approval_views(record, rows):
        if view.approval_id == approval_id:
            return view
    raise LifecycleNotFound(f"Approval '{approval_id}' has no lifecycle state.")


