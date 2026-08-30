import logging
from typing import Any, Dict, List, Optional

import json
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_registry
from backend.engine_adapter import (
    evaluate_facts,
    build_workflow_for_facts,
    get_catalogue,
    get_persona,
    get_sources,
    get_verification_summary,
    list_personas,
)
from backend.schemas import (EvaluateRequest, EvaluateWithWorkflowResponse, HealthResponse,
                              PersonaInfo, WorkflowRequest, DocumentRequirementsRequest)
from backend.documents.registry import get_document_registry
from backend.documents.service import requirements_for_application, readiness_for_application
from backend.documents.submissions import get_submission_store
from backend.documents.validators import validate_structured_fields

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("regulatory-engine-api")

app = FastAPI(
    title="Regulatory Approval & Compliance Engine API",
    description="Stateless adapter for deterministic regulatory reasoning (engine-v3 baseline).",
    version="3.0.0",
)

# CORS Configuration for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check and engine verification status",
)
def health_check():
    """Returns engine health status, counts of loaded regulatory assets, and verification breakdown."""
    registry = get_registry()
    ver_summary = get_verification_summary()
    return HealthResponse(
        status="healthy",
        engine_version="3.0.0",
        requirements_count=len(registry.catalogue),
        rules_count=len(registry.rules),
        sources_count=len(registry.sources),
        verification_summary=ver_summary,
    )


@app.get(
    "/api/catalogue",
    tags=["Regulatory Data"],
    summary="Get requirement catalogue",
)
def get_requirements_catalogue():
    """Returns the full catalogue of approvals, registrations, licences, and compliance items."""
    return get_catalogue()


@app.get(
    "/api/sources",
    tags=["Regulatory Data"],
    summary="Get authoritative sources",
)
def get_regulatory_sources():
    """Returns all authoritative sources cited by the regulatory rules."""
    return get_sources()


@app.get(
    "/api/personas",
    response_model=List[PersonaInfo],
    tags=["Personas"],
    summary="List available demo personas",
)
def get_all_personas():
    """Lists all available test personas in the system."""
    return list_personas()


@app.get(
    "/api/personas/{persona_id}",
    tags=["Personas"],
    summary="Get persona fact vector",
)
def get_persona_by_id(persona_id: str):
    """Fetches a specific persona's fact vector by ID (e.g. 'persona_a', 'persona_b', 'persona_c')."""
    persona_data = get_persona(persona_id)
    if persona_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona '{persona_id}' not found.",
        )
    return persona_data


@app.post(
    "/api/evaluate",
    tags=["Regulatory Derivation"],
    summary="Evaluate facts against regulatory rules",
)
def evaluate_regulatory_facts(payload: EvaluateRequest):
    """
    Evaluates applicant facts against the versioned regulatory rule graph.
    Returns four-state requirement resolution (APPLICABLE, NOT_APPLICABLE, UNKNOWN, CONFLICT)
    and full statutory provenance for all derivations.
    """
    try:
        result = evaluate_facts(facts=payload.facts, as_of=payload.as_of)
        return result
    except Exception as e:
        logger.exception("Error during regulatory evaluation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Regulatory derivation failed: {str(e)}",
        )


@app.post("/api/workflow", tags=["Workflow"], summary="Build a deterministic approval workflow")
def build_regulatory_workflow(payload: WorkflowRequest):
    try:
        return build_workflow_for_facts(
            payload.facts,
            payload.as_of,
            payload.include_provisional,
            payload.include_candidate_edges,
        )["workflow"]
    except Exception as e:
        logger.exception("Error during workflow construction")
        raise HTTPException(status_code=500, detail=f"Workflow construction failed: {str(e)}")


@app.post(
    "/api/evaluate-with-workflow",
    response_model=EvaluateWithWorkflowResponse,
    tags=["Workflow"],
    summary="Evaluate facts and build a workflow",
)
def evaluate_with_workflow(payload: WorkflowRequest):
    try:
        return build_workflow_for_facts(
            payload.facts,
            payload.as_of,
            payload.include_provisional,
            payload.include_candidate_edges,
        )
    except Exception as e:
        logger.exception("Error during evaluation and workflow construction")
        raise HTTPException(status_code=500, detail=f"Workflow evaluation failed: {str(e)}")


@app.get("/api/documents/requirements", tags=["Documents"], summary="List M4 document/evidence requirements")
def get_document_requirements(approval_id: Optional[str] = None):
    """Static registry view. Conditions are exposed; applicability is not changed."""
    registry = get_document_registry()
    selected = [approval_id] if approval_id else None
    return {
        "coverage": [c.as_dict() for c in registry.coverage(selected)],
        "specs": [s.as_dict() for s in registry.specs()],
        "requirements": [r.as_dict() | {"source": r.source.as_dict()} for r in registry.requirements(selected)],
    }


@app.post("/api/documents/requirements", tags=["Documents"], summary="Evaluate M4 requirements for facts")
def evaluate_document_requirements(payload: DocumentRequirementsRequest):
    return requirements_for_application(payload.facts, payload.as_of, payload.approval_ids, payload.include_provisional, payload.workflow_aware)


@app.post("/api/documents/submit", tags=["Documents"], summary="Submit evidence metadata or an upload")
async def submit_document(request: Request):
    """Accept multipart upload or JSON structured/form input; never claims authenticity."""
    content_type = request.headers.get("content-type", "")
    store = get_submission_store()
    try:
        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            application_id = str(form.get("application_id") or "")
            document_id = str(form.get("document_id") or "")
            item_kind = form.get("item_kind")
            spec = get_document_registry().validate_submission(document_id, item_kind)
            upload = form.get("file")
            if upload is None or not hasattr(upload, "read"):
                raise ValueError("multipart submission requires file")
            content = await upload.read()
            item, duplicate = store.submit_bytes(application_id, document_id, upload.filename, content, upload.content_type or "", spec)
        else:
            body = await request.json()
            application_id = body.get("application_id")
            document_id = body.get("document_id")
            spec = get_document_registry().validate_submission(document_id, body.get("item_kind"))
            if not isinstance(body.get("structured_data", {}), dict):
                raise ValueError("structured_data must be an object")
            validation = validate_structured_fields(body.get("structured_data", {}))
            item, duplicate = store.submit_structured(application_id, document_id, validation["fields"], spec)
            item.validation = validation
        response = item.as_dict()
        response["duplicate"] = duplicate
        response["verification_note"] = "M4 records presence/metadata only; upload is not authenticity-verified."
        return response
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/api/documents/readiness", tags=["Documents"], summary="Get M4 document readiness")
def get_document_readiness(application_id: str, facts: Optional[str] = None, approval_id: Optional[str] = None, workflow_aware: bool = False):
    try:
        parsed = json.loads(facts) if facts else {}
        if not isinstance(parsed, dict):
            raise ValueError("facts must be a JSON object")
        return readiness_for_application(application_id, parsed, approval_ids=[approval_id] if approval_id else None, workflow_aware=workflow_aware)
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
