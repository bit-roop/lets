"""Milestone 4 regulatory evidence and document-readiness subsystem."""

from .models import (
    DocumentSpec, DocumentRequirement, DocumentSubmission, Readiness,
    SourceRef, Coverage, ReuseLink,
)
from .registry import DocumentRegistry, get_document_registry

__all__ = [
    "DocumentSpec", "DocumentRequirement", "DocumentSubmission", "Readiness",
    "SourceRef", "Coverage", "ReuseLink", "DocumentRegistry",
    "get_document_registry",
]
