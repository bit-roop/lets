"""M5 API. Four endpoints, all additive under /api/verification.

Both analysis and the evidence overlay require the caller to supply an
already-established M4 result. That is deliberate: M5 must observe M4's
decision rather than trigger a fresh one. See backend/verification/m4_context.py.
"""

from datetime import date
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import capabilities
from .logging_safe import log_failure
from .profiles.registry import get_profile_registry
from .service import AnalysisError, analyze, evidence_overlay, records_for_application

router = APIRouter(prefix="/api/verification", tags=["Verification"])

#: Returned for any unexpected server-side failure. Exception detail, file
#: paths, document text and extracted values must never reach the client.
GENERIC_ERROR = ("The verification service could not complete this request. "
                 "Please try again, or contact support if this continues.")

M4_RESULT_FIELD = Field(
    ...,
    description=("The M4 requirements result to observe, exactly as returned by "
                 "POST /api/documents/requirements. M5 reads the applicability "
                 "M4 already established and does not evaluate it again."))


class AnalyzeRequest(BaseModel):
    submission_id: str = Field(..., description="An existing M4 submission_id.")
    m4_result: Dict[str, Any] = M4_RESULT_FIELD
    as_of: Optional[date] = None


class OverlayRequest(BaseModel):
    application_id: str
    m4_result: Dict[str, Any] = M4_RESULT_FIELD
    m4_readiness: Optional[Dict[str, Any]] = Field(
        default=None,
        description=("The M4 readiness result, as returned by "
                     "POST /api/documents/readiness. Echoed back verbatim; M5 "
                     "never recomputes or alters it."))


@router.post("/analyze", summary="Examine one submitted document")
def analyze_submission(payload: AnalyzeRequest):
    """Examines an already-submitted M4 document against an established M4 result.

    Never claims authenticity, never changes M4 readiness, and never alters
    which approvals or requirements apply.
    """
    try:
        return analyze(payload.submission_id, payload.m4_result, payload.as_of)
    except AnalysisError as exc:
        # Caller-correctable and safe to echo: it describes the request, not
        # the document or the server.
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        # Sanitised diagnostic only: no exception message, no traceback text.
        log_failure("analyze", exc, submission_id=payload.submission_id)
        raise HTTPException(status_code=500, detail=GENERIC_ERROR)


@router.get("/records", summary="Verification records for an application")
def get_records(application_id: str):
    try:
        return {"application_id": application_id,
                "records": records_for_application(application_id)}
    except Exception as exc:
        log_failure("records", exc, application_id=application_id)
        raise HTTPException(status_code=500, detail=GENERIC_ERROR)


@router.post("/evidence", summary="M4 readiness with a separate M5 evidence overlay")
def get_evidence_overlay(payload: OverlayRequest):
    try:
        return evidence_overlay(payload.application_id, payload.m4_result,
                                payload.m4_readiness)
    except AnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log_failure("evidence", exc, application_id=payload.application_id)
        raise HTTPException(status_code=500, detail=GENERIC_ERROR)


@router.get("/capabilities", summary="What this build can and cannot establish")
def get_capabilities():
    try:
        registry = get_profile_registry()
        return {
            "capabilities": capabilities.detect(),
            "authenticity": capabilities.authenticity_summary(),
            "profiles": [
                {
                    "profile_id": p.profile_id,
                    "version": p.version,
                    "document_id": p.document_id,
                    "display_name": p.display_name,
                    "applicant_summary": p.applicant_summary,
                    "authenticity_capability": p.authenticity["capability"],
                    "limitations": p.provenance.get("limitations", []),
                }
                for p in registry.all()
            ],
            "not_analyzed_document_ids": registry.unprofiled_upload_document_ids(),
            "not_analyzed_note": (
                "These evidence items are required by the regulatory checklist but "
                "this system has no verification profile for them. Their contents "
                "have not been examined."),
        }
    except Exception as exc:
        log_failure("capabilities", exc)
        raise HTTPException(status_code=500, detail=GENERIC_ERROR)
