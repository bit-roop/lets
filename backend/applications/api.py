"""FastAPI router for Application Case Management (Slice 3)."""

import logging
from fastapi import APIRouter, HTTPException, status

from .models import (
    ApplicationCreateRequest,
    ApplicationListResponse,
    ApplicationRecord,
)
from .service import (
    create_application_case,
    get_application_case,
    list_application_cases,
)

logger = logging.getLogger("regulatory-engine-applications")

router = APIRouter(prefix="/api/applications", tags=["Applications"])


@router.post(
    "",
    response_model=ApplicationRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Create or submit a persistent application case",
)
def create_application(payload: ApplicationCreateRequest):
    """
    Persists an application case from the established assessment and readiness context.
    Assigns a permanent tracking reference (e.g. MH-FOOD-2026-0001) and transitions
    status to SUBMITTED.
    """
    try:
        record = create_application_case(payload)
        return record
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Internal failure during application creation: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing the application case.",
        )


@router.get(
    "",
    response_model=ApplicationListResponse,
    summary="List all filed applications",
)
def list_applications():
    """Returns a list of all persistent applications filed in the system."""
    try:
        items = list_application_cases()
        return ApplicationListResponse(applications=items, total_count=len(items))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Internal failure listing applications: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while retrieving applications.",
        )


@router.get(
    "/{application_id}",
    response_model=ApplicationRecord,
    summary="Get an application by ID or tracking reference",
)
def get_application(application_id: str):
    """Retrieves full application case details including approvals, submissions, and timeline."""
    try:
        record = get_application_case(application_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application case '{application_id}' not found.",
            )
        return record
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Internal failure retrieving application '%s': %s", application_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while retrieving the application case.",
        )
