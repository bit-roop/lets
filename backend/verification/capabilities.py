"""Capability reporting.

This module exists so the system can never claim a capability the environment
does not have.  Everything absent in slice 1 is reported absent, by name, with
the reason -- rather than being silently unavailable or, worse, faked.
"""

from typing import Any, Dict

from . import states


def _importable(module_name: str) -> bool:
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def detect() -> Dict[str, Any]:
    return {
        "native_pdf_text": _importable("pdfplumber"),
        "pdf_structure": _importable("pypdf"),
        "ocr": False,
        "ocr_reason": "OCR is not part of this build. No OCR engine is installed.",
        "image_documents": False,
        "image_documents_reason": (
            "Image ingestion is not part of this build; only PDF text extraction "
            "is implemented."),
        "qr_decoding": False,
        "qr_reason": "QR decoding is not part of this build.",
        "pdf_signature_validation": False,
        "pdf_signature_reason": (
            "Signature validation is not part of this build. Where a PDF contains "
            "signature objects their presence may be recorded, but presence is not "
            "validation and establishes nothing about authenticity."),
        "llm": False,
        "llm_reason": "No language model is used in this build.",
        "cross_document_checks": False,
        "cross_document_reason": (
            "Comparison between documents is not part of this build."),
        "authoritative_gateways": {},
        "authoritative_gateway_note": (
            "No authoritative verification gateway is configured or available. "
            "Authenticity cannot be established for any document in this build, "
            "and the VERIFIED state is therefore unreachable."),
        "verified_state_reachable": False,
    }


def authenticity_summary() -> Dict[str, str]:
    return {
        "states_in_use": ", ".join(sorted({
            states.AUTH_NOT_APPLICABLE_APPLICANT_AUTHORED,
            states.AUTH_NO_MECHANISM_AVAILABLE,
        })),
        "note": (
            "'Not applicable' means the document is completed by the applicant and "
            "has no issuer to check against. 'No mechanism available' means the "
            "document has an issuer but no verification service is available to "
            "this system. Neither means the document is authentic, and neither "
            "means it is not."),
    }
