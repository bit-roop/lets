"""M5 orchestration.

Pipeline: guard -> inventory -> native text -> classify -> match -> fields ->
checks -> disposition -> persist.

Three invariants this file must not break:

1. M5 is *given* M4's decision and reads it. It never computes one. There is no
   call here to any M4 service function, because those functions re-run the
   engine internally.
2. UNKNOWN applicability stays unresolved. It never becomes NOT_APPLICABLE.
3. Nothing here writes to an M4 object. DocumentSubmission is read only.
"""

import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from . import capabilities, m4_context, m4_gateway, privacy, states
from .checks.runner import run_checks
from .classify import deterministic as classifier
from .extract import anchored
from .extract.text import extract_pdf_text
from .ingest import guard
from .ingest.pdf import PdfStructureError, inventory
from .m4_context import M4Context, M4ContextError
from .models import (AuthenticityResult, ClassificationDetail, ConfidenceBreakdown,
                     ExtractedField, Finding, HumanReviewTicket, Provenance,
                     VerificationRecord, assert_authenticity_writable)
from .profiles.registry import get_profile_registry
from .store import get_record_store, retention_window


class AnalysisError(ValueError):
    """A caller-correctable problem: unknown submission, malformed M4 result."""


def analyze(submission_id: str, m4_result: Dict[str, Any],
            as_of: Optional[date] = None) -> Dict[str, Any]:
    """Examine one submitted document against an already-established M4 result.

    `m4_result` is the payload from POST /api/documents/requirements. M5 reads
    the applicability M4 already decided; it does not derive one.
    """
    try:
        context = M4Context(m4_result)
    except M4ContextError as exc:
        raise AnalysisError(str(exc)) from exc

    submission = m4_gateway.submission(submission_id)
    if submission is None:
        raise AnalysisError(f"unknown submission_id: {submission_id!r}")

    # Read-only snapshot of everything M5 needs from M4.
    document_id = submission.document_id
    application_id = submission.application_id
    sha256 = submission.sha256
    declared_mime = submission.mime_type
    storage_key = submission.storage_key

    profile = get_profile_registry().get(document_id)
    caps = capabilities.detect()
    created_at, expires_at = retention_window()

    applicability, observations = context.observe_document(document_id)

    record = VerificationRecord(
        record_id=str(uuid.uuid4()),
        submission_id=submission_id,
        application_id=application_id,
        document_id=document_id,
        submission_sha256=sha256,
        m4_observations=observations,
        m4_applicability_observed=applicability,
        requirement_match=states.INDETERMINATE,
        ingestion=states.NOT_ANALYZED,
        extraction=states.NOT_ATTEMPTED,
        classification=states.INSUFFICIENT_EVIDENCE,
        classification_detail=ClassificationDetail(None, None, None, None),
        internal_consistency=states.INDETERMINATE,
        cross_consistency=states.NO_COMPARANDA,
        authenticity=_authenticity_for(profile),
        confidence=ConfidenceBreakdown(),
        disposition=states.NOT_ANALYZED,
        disposition_reason=None,
        created_at=created_at,
        expires_at=expires_at,
        profile_id=profile.profile_id if profile else None,
        profile_version=profile.version if profile else None,
        capabilities_at_analysis=caps,
    )

    # --- Disposition row 1: no profile --------------------------------------
    if profile is None:
        record.disposition_reason = states.REASON_NO_PROFILE
        return _persist(record)

    # --- Disposition rows 2 and 3: what M4 already decided -------------------
    forced_match = m4_context.requirement_match_for(applicability)
    if forced_match is not None:
        # FALSE / UNSUPPORTED -> NOT_APPLICABLE. UNKNOWN -> INDETERMINATE.
        # Different claims; never merged.
        record.requirement_match = forced_match
        record.disposition = states.NOT_ANALYZED
        record.disposition_reason = m4_context.disposition_reason_for(applicability)
        return _persist(record)

    # --- Disposition row 4: media guard -------------------------------------
    spec = m4_gateway.spec(document_id)
    try:
        path = guard.resolve_storage_path(storage_key, m4_gateway.submission_storage_root())
    except (ValueError, FileNotFoundError) as exc:
        record.ingestion = states.INGEST_FAILED
        record.disposition = states.REJECTED_STRUCTURAL
        record.disposition_reason = "STORED_FILE_UNAVAILABLE"
        record.findings.append(_system_finding(
            "M5-STORAGE", "The stored copy of this upload could not be opened."))
        return _persist(record)

    verdict = guard.check(path, declared_mime, spec.accepted_formats)
    if not verdict.accepted:
        record.ingestion = states.MEDIA_REJECTED
        record.disposition = states.REJECTED_STRUCTURAL
        record.disposition_reason = "MEDIA_REJECTED"
        for reason in verdict.reasons:
            record.findings.append(_system_finding("M5-MEDIA", reason))
        return _persist(record)

    record.ingestion = states.INGESTED
    for note in verdict.notes:
        record.findings.append(_informational_finding("M5-MEDIA-NOTE", note))

    if verdict.detected_mime != "application/pdf":
        # Slice 1 reads PDFs only. An accepted image is not a failure of the
        # document; it is a capability this build does not have.
        record.extraction = states.NOT_ATTEMPTED
        record.disposition = states.HUMAN_REVIEW_REQUIRED
        record.disposition_reason = "CAPABILITY_NOT_AVAILABLE"
        record.human_review = HumanReviewTicket(
            ticket_id=str(uuid.uuid4()),
            triggers=[states.TRIGGER_INSUFFICIENT_EVIDENCE],
            reasons=["This build can only read PDF documents. The uploaded image "
                     "has not been examined and needs manual checking."])
        return _persist(record)

    try:
        pdf_info = inventory(path)
    except PdfStructureError:
        record.ingestion = states.INGEST_FAILED
        record.disposition = states.REJECTED_STRUCTURAL
        record.disposition_reason = "PDF_STRUCTURE_UNREADABLE"
        record.findings.append(_system_finding(
            "M5-PDF", "The PDF structure could not be read."))
        return _persist(record)

    max_pages = int(profile.thresholds.get("max_pages", guard.MAX_PAGES))
    if pdf_info.page_count > max_pages:
        record.ingestion = states.MEDIA_REJECTED
        record.disposition = states.REJECTED_STRUCTURAL
        record.disposition_reason = "MEDIA_REJECTED"
        record.findings.append(_system_finding(
            "M5-MEDIA",
            f"The document has {pdf_info.page_count} pages, above the "
            f"{max_pages}-page limit."))
        return _persist(record)

    # --- Extraction ---------------------------------------------------------
    min_chars = int(profile.thresholds.get("min_text_chars", 40))
    extraction = extract_pdf_text(path, min_text_chars=min_chars)
    record.extraction = extraction.state

    # Row 5: extractor failure is a SYSTEM fault, retryable, not a mismatch.
    if extraction.state == states.FAILED:
        record.disposition = states.HUMAN_REVIEW_REQUIRED
        record.disposition_reason = "SYSTEM_EXTRACTION_FAILURE"
        record.human_review = HumanReviewTicket(
            ticket_id=str(uuid.uuid4()),
            triggers=[states.TRIGGER_SYSTEM_EXTRACTION_FAILURE],
            reasons=["The document could not be processed because of a problem in "
                     "this system, not a problem with the document. It can be "
                     "retried."])
        record.findings.append(_system_finding("M5-EXTRACT", "Text extraction failed."))
        return _persist(record)

    # Row 6: nothing readable came out. The document was not checked; it did
    # not fail a check. Never a mismatch.
    if extraction.state == states.UNREADABLE:
        record.disposition = states.HUMAN_REVIEW_REQUIRED
        record.disposition_reason = "DOCUMENT_UNREADABLE"
        record.classification = states.INSUFFICIENT_EVIDENCE
        record.human_review = HumanReviewTicket(
            ticket_id=str(uuid.uuid4()),
            triggers=[states.TRIGGER_DOCUMENT_UNREADABLE],
            reasons=["No readable text could be found in this document. It may be a "
                     "scan. This build does not read scanned documents, so it needs "
                     "to be checked by a person."])
        record.findings.append(Finding(
            check_id="M5-EXTRACT-UNREADABLE", outcome=states.OUTCOME_UNREADABLE,
            severity=states.INFORMATIONAL,
            message="No readable text layer was found in this document.",
            provenance=Provenance(method=states.METHOD_PDF_TEXT_LAYER)))
        return _persist(record)

    text = extraction.full_text
    offsets = extraction.page_offsets()

    # --- Classification (content only; the filename is never passed in) ------
    outcome = classifier.classify(text, profile, get_profile_registry().all())
    record.classification = outcome.state
    record.classification_detail = ClassificationDetail(
        label=outcome.best.document_id if outcome.best else None,
        score=round(outcome.best.score, 3) if outcome.best else None,
        runner_up=outcome.runner_up.document_id if outcome.runner_up else None,
        runner_up_score=round(outcome.runner_up.score, 3) if outcome.runner_up else None,
        matched_anchors=outcome.best.matched if outcome.best else [],
    )
    match_state, _ = classifier.requirement_match_for(outcome)
    record.requirement_match = match_state
    identity_matched = outcome.state == states.MATCHES_EXPECTED

    # --- Fields -------------------------------------------------------------
    fields: List[ExtractedField] = []
    for field_spec in profile.fields:
        if field_spec["field_id"] == "document_identity_text":
            fields.append(_identity_field(profile, outcome, field_spec))
            continue
        fields.append(anchored.extract_field(
            field_spec, text, offsets, profile.profile_id, profile.version))
    record.fields = fields
    by_id = {f.field_id: f for f in fields}

    # --- Deterministic checks ----------------------------------------------
    record.findings.extend(run_checks(profile, by_id, identity_matched, as_of))
    record.internal_consistency = _internal_consistency(record.findings)
    record.confidence = _confidence(profile, fields, outcome)

    # --- Disposition rows 7-10 ---------------------------------------------
    _derive_disposition(record, profile)
    return _persist(record)


# ---------------------------------------------------------------------------
# Disposition
# ---------------------------------------------------------------------------

def _derive_disposition(record: VerificationRecord, profile) -> None:
    blocking_mismatch = [
        f for f in record.findings
        if f.severity == states.BLOCKING and f.outcome == states.OUTCOME_MISMATCH
    ]

    if record.requirement_match == states.MISMATCH or blocking_mismatch:
        record.disposition = states.NEEDS_APPLICANT_ACTION
        record.disposition_reason = "REQUIREMENT_MISMATCH"
        return

    triggers, reasons = [], []

    if profile.human_review.get("always"):
        triggers.append("INHERENTLY_VISUAL_JUDGEMENT")
        reasons.append(profile.human_review.get(
            "always_reason", "This evidence item always requires a person to review it."))

    if record.classification == states.INSUFFICIENT_EVIDENCE:
        triggers.append(states.TRIGGER_INSUFFICIENT_EVIDENCE)
        reasons.append("There was not enough evidence in the document to identify "
                       "what it is.")

    uncertain_grounded = [
        f.field_id for f in record.fields
        if f.field_source == states.PROFILE_GROUNDED and f.normalized_value is None
    ]
    if uncertain_grounded:
        triggers.append(states.TRIGGER_EXTRACTION_UNCERTAIN_ON_BLOCKING_FIELD)
        reasons.append("Some expected information could not be read reliably.")

    if triggers:
        record.disposition = states.HUMAN_REVIEW_REQUIRED
        record.disposition_reason = triggers[0]
        record.human_review = HumanReviewTicket(
            ticket_id=str(uuid.uuid4()), triggers=triggers, reasons=reasons,
            fields=uncertain_grounded,
            checklist=list(profile.human_review.get("checklist", [])))
        return

    record.disposition = states.ACCEPTED_FOR_REVIEW
    record.disposition_reason = None


def _internal_consistency(findings: List[Finding]) -> str:
    relevant = [f for f in findings if f.outcome in
                (states.OUTCOME_MATCH, states.OUTCOME_MISMATCH)]
    if not relevant:
        return states.INDETERMINATE
    if any(f.outcome == states.OUTCOME_MISMATCH for f in relevant):
        return states.INCONSISTENT
    return states.CONSISTENT


def _confidence(profile, fields, outcome) -> ConfidenceBreakdown:
    confidences = [f.confidence for f in fields] or [0.0]
    grounded_ids = profile.grounded_field_ids()
    grounded_found = [f for f in fields
                      if f.field_id in grounded_ids and f.normalized_value is not None]
    coverage = (len(grounded_found) / len(grounded_ids)) if grounded_ids else None
    return ConfidenceBreakdown(
        extraction_min=round(min(confidences), 3),
        extraction_mean=round(sum(confidences) / len(confidences), 3),
        classification_margin=round(outcome.margin, 3) if outcome.margin is not None else None,
        grounded_field_coverage=round(coverage, 3) if coverage is not None else None,
    )


def _identity_field(profile, outcome, field_spec) -> ExtractedField:
    matched = outcome.best.matched if (outcome.best and
                                       outcome.best.document_id == profile.document_id) else []
    value = ", ".join(matched) if matched else None
    return ExtractedField(
        field_id="document_identity_text",
        label=field_spec.get("label", "Document title text found"),
        raw_value=value,
        normalized_value=value,
        confidence=0.9 if value else 0.0,
        field_source=states.PROFILE_GROUNDED,
        sensitivity=field_spec.get("sensitivity", privacy.NON_SENSITIVE),
        uncertainty_reason=None if value else "EXPECTED_IDENTITY_TEXT_NOT_FOUND",
        provenance=Provenance(
            method=states.METHOD_ANCHORED_REGEX,
            profile_id=profile.profile_id, profile_version=profile.version),
    )


def _authenticity_for(profile) -> AuthenticityResult:
    """Authenticity is never established in this build.

    'Not applicable' and 'no mechanism available' are different claims and are
    kept apart. Neither says the document is or is not genuine.
    """
    if profile is None:
        return AuthenticityResult(
            state=states.AUTH_NOT_ASSESSED, availability="NOT_ASSESSED",
            explanation="This evidence item was not examined by this system.")
    capability = profile.authenticity["capability"]
    return assert_authenticity_writable(AuthenticityResult(
        state=capability,
        availability="NOT_AVAILABLE",
        authoritative=False,
        provider_id=None,
        explanation=profile.authenticity["explanation"],
    ))


def _system_finding(check_id: str, message: str) -> Finding:
    """A system-side problem. The message is fixed text: exception detail is
    logged server-side, never placed in a record the applicant can read."""
    return Finding(
        check_id=check_id, outcome=states.OUTCOME_UNREADABLE,
        severity=states.INFORMATIONAL, message=message,
        provenance=Provenance(method=states.METHOD_DETERMINISTIC))


def _informational_finding(check_id: str, message: str) -> Finding:
    return Finding(
        check_id=check_id, outcome=states.OUTCOME_UNKNOWN,
        severity=states.INFORMATIONAL, message=message,
        provenance=Provenance(method=states.METHOD_DETERMINISTIC))


def _persist(record: VerificationRecord) -> Dict[str, Any]:
    get_record_store().save(record)
    return record.as_dict()


# ---------------------------------------------------------------------------
# Evidence overlay (Option A)
# ---------------------------------------------------------------------------

def evidence_overlay(application_id: str, m4_result: Dict[str, Any],
                     m4_readiness: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """M4's own readiness, passed through untouched, plus a separate M5 layer.

    Both M4 payloads are supplied by the caller, which already holds them. M5
    echoes the readiness verbatim rather than recomputing it -- so "unchanged by
    M5" is true by construction, not merely by intent.
    """
    try:
        context = M4Context(m4_result)
    except M4ContextError as exc:
        raise AnalysisError(str(exc)) from exc

    registry = get_profile_registry()
    records = {r["document_id"]: r for r in
               get_record_store().for_application(application_id)}

    counters = {
        "m5_supported_applicable_count": 0,
        "m5_analyzed_count": 0,
        "m5_accepted_for_review_count": 0,
        "m5_needs_action_count": 0,
        "m5_human_review_count": 0,
        "m5_rejected_structural_count": 0,
        "m5_not_analyzed_count": 0,
        "m5_no_profile_count": 0,
        "m5_applicability_unresolved_count": 0,
        "m5_not_applicable_count": 0,
        "m5_non_upload_excluded_count": 0,
        "m5_unsupported_excluded_count": 0,
        "m5_authenticity_established_count": 0,
    }
    per_requirement: List[Dict[str, Any]] = []

    for approval in context.approvals():
        for row in approval["requirements"]:
            document_id = row["document_id"]
            spec = m4_gateway.spec(document_id)
            observed = m4_context.observed_state_for_row(row)
            record = records.get(document_id)

            entry = {
                "requirement_id": row.get("requirement_id"),
                "approval_id": approval["approval_id"],
                "document_id": document_id,
                "document_name": spec.name,
                "m4_applicability_observed": observed,
                "in_m5_denominator": False,
                "requirement_match": record.get("requirement_match") if record else None,
                "disposition": record.get("disposition") if record else None,
                "authenticity_state": (record or {}).get("authenticity", {}).get("state"),
                "has_profile": registry.get(document_id) is not None,
            }

            # Exclusions, each counted separately so nothing is silently dropped.
            if observed == states.UNSUPPORTED_APPROVAL:
                counters["m5_unsupported_excluded_count"] += 1
                per_requirement.append(entry)
                continue
            if spec.item_kind != "UPLOAD_DOCUMENT":
                counters["m5_non_upload_excluded_count"] += 1
                per_requirement.append(entry)
                continue
            if observed == states.NOT_APPLICABLE_CONDITION_FALSE:
                counters["m5_not_applicable_count"] += 1
                per_requirement.append(entry)
                continue
            if observed in (states.UNRESOLVED_CONDITION_UNKNOWN,
                            states.UNRESOLVED_ENGINE_STATE):
                # Unresolved is NOT inapplicable. Counted on its own line.
                counters["m5_applicability_unresolved_count"] += 1
                per_requirement.append(entry)
                continue
            if not entry["has_profile"]:
                counters["m5_no_profile_count"] += 1
                per_requirement.append(entry)
                continue

            counters["m5_supported_applicable_count"] += 1
            entry["in_m5_denominator"] = True

            if record is None:
                counters["m5_not_analyzed_count"] += 1
            else:
                counters["m5_analyzed_count"] += 1
                key = {
                    states.ACCEPTED_FOR_REVIEW: "m5_accepted_for_review_count",
                    states.NEEDS_APPLICANT_ACTION: "m5_needs_action_count",
                    states.HUMAN_REVIEW_REQUIRED: "m5_human_review_count",
                    states.REJECTED_STRUCTURAL: "m5_rejected_structural_count",
                    states.NOT_ANALYZED: "m5_not_analyzed_count",
                }.get(record["disposition"])
                if key:
                    counters[key] += 1
                if record.get("authenticity", {}).get("state") == states.AUTH_VERIFIED:
                    counters["m5_authenticity_established_count"] += 1

            per_requirement.append(entry)

    return {
        "application_id": application_id,
        # Echoed verbatim from the caller. M5 does not compute readiness.
        "m4_readiness": m4_readiness,
        "m5_evidence": {
            "note": (
                "M5 is an evidence-verification overlay. M5 does not determine "
                "whether an approval applies, whether an M4 requirement is "
                "satisfied, or whether an approval is ready to submit. The M4 "
                "readiness above is supplied by M4 and is unchanged by M5. "
                "'Accepted for review' does not mean the requirement is satisfied "
                "or that the document is authentic."),
            "denominator_definition": (
                "Counted only where: the approval is supported by M4, the engine "
                "state M4 reported is APPLICABLE, the evidence item is a document "
                "upload, the requirement is not unsupported, the condition_state "
                "M4 reported is strictly TRUE, and M5 has a verification profile. "
                "Requirements whose applicability M4 reports as unknown are counted "
                "separately and are NOT treated as inapplicable."),
            "counters": counters,
            "per_requirement": per_requirement,
            "capabilities": capabilities.detect(),
        },
    }


def records_for_application(application_id: str) -> List[Dict[str, Any]]:
    return get_record_store().for_application(application_id)
