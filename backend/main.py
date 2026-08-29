import logging
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_registry
from backend.engine_adapter import (
    evaluate_facts,
    get_catalogue,
    get_persona,
    get_sources,
    get_verification_summary,
    list_personas,
)
from backend.schemas import EvaluateRequest, HealthResponse, PersonaInfo

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
