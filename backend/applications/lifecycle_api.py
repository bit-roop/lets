"""FastAPI routers for the Slice 4 prototype department lifecycle.

Two routers are exposed:

  * ``department_router`` — the officer-facing portal (``/api/departments``)
  * ``lifecycle_router``  — actions on a filed case (``/api/applications/...``)

All handlers map lifecycle failures onto stable HTTP codes and never return an
internal exception message to a client.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from . import lifecycle_service as svc
from .lifecycle import (
    InvalidTransition,
    LifecycleError,
    LifecycleForbidden,
    LifecycleNotFound,
    LifecycleValidation,
)
from .models import (
    ApprovalLifecycleView,
    DecisionRequest,
    DepartmentCaseDetail,
    DepartmentCaseListResponse,
    DepartmentListResponse,
    QueryListResponse,
    QueryView,
    RaiseQueryRequest,
    ResolveQueryRequest,
    RespondToQueryRequest,
    StartReviewRequest,
)

logger = logging.getLogger("regulatory-engine-lifecycle")

department_router = APIRouter(prefix="/api/departments", tags=["Department Review (Prototype Simulation)"])
lifecycle_router = APIRouter(prefix="/api/applications", tags=["Application Lifecycle (Prototype Simulation)"])

_GENERIC_ERROR = "An internal error occurred while processing the department lifecycle request."


def _http_error(exc: LifecycleError) -> HTTPException:
    """Map a lifecycle failure onto an HTTP status without leaking internals.

    The messages raised by the lifecycle layer are written for a client to
    read: they name states and identifiers, never file paths, SQL, or
    tracebacks.
    """
    if isinstance(exc, LifecycleNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, LifecycleForbidden):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, InvalidTransition):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


def _guard(operation: str, fn, *args, **kwargs):
    """Run a service call, translating known failures and hiding unknown ones."""
    try:
        return fn(*args, **kwargs)
    except LifecycleError as exc:
        raise _http_error(exc)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - deliberate catch-all boundary
        logger.error("Internal failure during %s: %s", operation, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_GENERIC_ERROR,
        )


# ---------------------------------------------------------------------------
# Department portal
# ---------------------------------------------------------------------------


@department_router.get("", response_model=DepartmentListResponse, summary="List simulated departments")
def get_departments():
    return DepartmentListResponse(departments=_guard("department listing", svc.list_departments))


@department_router.get(
    "/{department}/applications",
    response_model=DepartmentCaseListResponse,
    summary="List filed prototype cases for a department",
)
def get_department_applications(department: str):
    return _guard("department case listing", svc.list_department_cases, department)


@department_router.get(
    "/{department}/applications/{application_id}",
    response_model=DepartmentCaseDetail,
    summary="Officer view of a single prototype case",
)
def get_department_application(department: str, application_id: str):
    return _guard("department case retrieval", svc.get_department_case, department, application_id)


# ---------------------------------------------------------------------------
# Officer actions on approvals
# ---------------------------------------------------------------------------


@lifecycle_router.post(
    "/{application_id}/approvals/{approval_id}/start-review",
    response_model=ApprovalLifecycleView,
    summary="Move an approval into scrutiny (prototype simulation)",
)
def start_review(application_id: str, approval_id: str, payload: StartReviewRequest):
    return _guard("start review", svc.start_review, application_id, approval_id, payload.department)


@lifecycle_router.post(
    "/{application_id}/approvals/{approval_id}/grant",
    response_model=ApprovalLifecycleView,
    summary="Record a prototype department decision to grant",
)
def grant_approval(application_id: str, approval_id: str, payload: DecisionRequest):
    """Granted in simulation. This is not a government approval of any kind."""
    return _guard(
        "grant approval", svc.grant_approval,
        application_id, approval_id, payload.department, payload.decision_note,
    )


@lifecycle_router.post(
    "/{application_id}/approvals/{approval_id}/reject",
    response_model=ApprovalLifecycleView,
    summary="Record a prototype department decision to reject",
)
def reject_approval(application_id: str, approval_id: str, payload: DecisionRequest):
    return _guard(
        "reject approval", svc.reject_approval,
        application_id, approval_id, payload.department, payload.decision_note,
    )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


@lifecycle_router.post(
    "/{application_id}/queries",
    response_model=QueryView,
    status_code=status.HTTP_201_CREATED,
    summary="Raise a departmental query against an approval",
)
def create_query(application_id: str, payload: RaiseQueryRequest):
    return _guard(
        "query creation", svc.raise_query,
        application_id, payload.approval_id, payload.department, payload.query_text, payload.deadline,
    )


@lifecycle_router.get(
    "/{application_id}/queries",
    response_model=QueryListResponse,
    summary="List queries on an application",
)
def get_queries(application_id: str, department: Optional[str] = None):
    items = _guard("query listing", svc.list_queries, application_id, department)
    return QueryListResponse(application_id=application_id, queries=items, total_count=len(items))


@lifecycle_router.get(
    "/{application_id}/queries/{query_id}",
    response_model=QueryView,
    summary="Get a single query",
)
def get_single_query(application_id: str, query_id: str):
    return _guard("query retrieval", svc.get_query, application_id, query_id)


@lifecycle_router.post(
    "/{application_id}/queries/{query_id}/respond",
    response_model=QueryView,
    summary="Applicant response to an open query",
)
def respond_to_query(application_id: str, query_id: str, payload: RespondToQueryRequest):
    return _guard(
        "query response", svc.respond_to_query,
        application_id, query_id, payload.response_text,
        payload.response_document_id, payload.response_submission_id,
    )


@lifecycle_router.post(
    "/{application_id}/queries/{query_id}/resolve",
    response_model=QueryView,
    summary="Officer accepts a response and resumes scrutiny",
)
def resolve_query(application_id: str, query_id: str, payload: ResolveQueryRequest):
    return _guard(
        "query resolution", svc.resolve_query,
        application_id, query_id, payload.department, payload.resolution_note,
    )


