from datetime import date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    """Request payload for regulatory rule derivation and requirement resolution."""
    facts: Dict[str, Any] = Field(
        ...,
        description="Key-value dictionary of applicant facts. Missing facts or null values evaluate as UNKNOWN.",
    )
    as_of: Optional[date] = Field(
        None,
        description="Temporal evaluation date in ISO format (YYYY-MM-DD). Defaults to current date.",
    )


class HealthResponse(BaseModel):
    status: str
    engine_version: str
    requirements_count: int
    rules_count: int
    sources_count: int
    verification_summary: Dict[str, int]


class PersonaInfo(BaseModel):
    id: str
    name: str
