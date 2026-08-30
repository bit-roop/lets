"""M5 transport models.

None of these decide regulatory applicability.  M4Observation is a verbatim
copy of what M4 reported; it is never recomputed here.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from . import privacy, states

RULESET_VERSION = "m5-slice1-2026-08-30"


@dataclass(frozen=True)
class Provenance:
    method: str
    page: Optional[int] = None
    char_span: Optional[Tuple[int, int]] = None
    profile_id: Optional[str] = None
    profile_version: Optional[str] = None
    ruleset_version: str = RULESET_VERSION
    model_id: Optional[str] = None  # non-null only when method == "LLM"

    def as_dict(self):
        d = asdict(self)
        if self.char_span is not None:
            d["char_span"] = list(self.char_span)
        return d


@dataclass(frozen=True)
class ExtractedField:
    """One value read from a document.

    ``raw_value`` and ``normalized_value`` are *transient*. They exist so the
    deterministic checks can run against the real value, and they are excluded
    from ``as_dict``, which is the only path to the record store and to the API.
    What survives is ``display_value``: the value itself when the profile
    declares the field non-sensitive, and a masked form when it does not.
    """
    field_id: str
    #: Applicant-facing label from the profile. The UI shows this; it must never
    #: fall back to rendering the internal field_id.
    label: str
    raw_value: Optional[str]          # transient - never serialised
    normalized_value: Optional[Any]   # transient - never serialised
    confidence: float
    field_source: str
    provenance: Provenance
    sensitivity: str = privacy.NON_SENSITIVE
    uncertainty_reason: Optional[str] = None

    @property
    def display_value(self) -> Optional[str]:
        return privacy.safe_display(self.normalized_value, self.sensitivity)

    @property
    def value_present(self) -> bool:
        return self.normalized_value is not None

    @property
    def masked(self) -> bool:
        return privacy.is_redacted(self.sensitivity) and self.value_present

    def as_dict(self):
        """Serialisation deliberately omits raw_value and normalized_value."""
        return {
            "field_id": self.field_id,
            "label": self.label,
            "field_source": self.field_source,
            "sensitivity": self.sensitivity,
            "value_present": self.value_present,
            "display_value": self.display_value,
            "masked": self.masked,
            "confidence": self.confidence,
            "uncertainty_reason": self.uncertainty_reason,
            "provenance": self.provenance.as_dict(),
        }


@dataclass(frozen=True)
class Finding:
    check_id: str
    outcome: str
    severity: str
    message: str
    provenance: Provenance
    remedy: Optional[str] = None
    inputs: List[str] = field(default_factory=list)
    #: Already reduced by privacy.safe_display before construction. A finding
    #: must never carry an unreduced value into the store or the API.
    observed: Optional[str] = None
    expected: Optional[str] = None

    def as_dict(self):
        d = asdict(self)
        d["provenance"] = self.provenance.as_dict()
        return d


@dataclass(frozen=True)
class M4Observation:
    """Verbatim copy of M4/engine output.  Never recalculated by M5."""
    requirement_id: str
    approval_id: str
    document_id: str
    obligation: str
    blocking: bool
    m4_verification_status: str
    coverage_status: str
    engine_state: Optional[str]
    condition_state: Optional[str]
    condition_description: Optional[str]
    condition_trace: List[Any] = field(default_factory=list)
    source_authority: Optional[str] = None
    source_checklist_item: Optional[str] = None
    source_url: Optional[str] = None

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ConfidenceBreakdown:
    """No single multiplied score.  A scalar would look precise and mean nothing."""
    extraction_min: Optional[float] = None
    extraction_mean: Optional[float] = None
    classification_margin: Optional[float] = None
    grounded_field_coverage: Optional[float] = None

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class AuthenticityResult:
    state: str
    availability: str
    authoritative: bool = False
    provider_id: Optional[str] = None
    evidence: List[str] = field(default_factory=list)
    checked_at: Optional[str] = None
    explanation: str = ""

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class HumanReviewTicket:
    ticket_id: str
    triggers: List[str]
    reasons: List[str]
    fields: List[str] = field(default_factory=list)
    pages: List[int] = field(default_factory=list)
    disputed: List[Dict[str, Any]] = field(default_factory=list)
    checklist: List[str] = field(default_factory=list)
    status: str = "OPEN"

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ClassificationDetail:
    label: Optional[str]
    score: Optional[float]
    runner_up: Optional[str]
    runner_up_score: Optional[float]
    matched_anchors: List[str] = field(default_factory=list)

    def as_dict(self):
        return asdict(self)


@dataclass
class VerificationRecord:
    record_id: str
    submission_id: str
    application_id: str
    document_id: str
    submission_sha256: Optional[str]
    m4_observations: List[M4Observation]
    m4_applicability_observed: str
    requirement_match: str
    ingestion: str
    extraction: str
    classification: str
    classification_detail: ClassificationDetail
    internal_consistency: str
    cross_consistency: str
    authenticity: AuthenticityResult
    confidence: ConfidenceBreakdown
    disposition: str
    disposition_reason: Optional[str]
    created_at: str
    expires_at: str
    profile_id: Optional[str] = None
    profile_version: Optional[str] = None
    ruleset_version: str = RULESET_VERSION
    fields: List[ExtractedField] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    human_review: Optional[HumanReviewTicket] = None
    capabilities_at_analysis: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self):
        return {
            "record_id": self.record_id,
            "submission_id": self.submission_id,
            "application_id": self.application_id,
            "document_id": self.document_id,
            "submission_sha256": self.submission_sha256,
            "m4_observations": [o.as_dict() for o in self.m4_observations],
            "m4_applicability_observed": self.m4_applicability_observed,
            "requirement_match": self.requirement_match,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "ruleset_version": self.ruleset_version,
            "ingestion": self.ingestion,
            "extraction": self.extraction,
            "classification": self.classification,
            "classification_detail": self.classification_detail.as_dict(),
            "internal_consistency": self.internal_consistency,
            "cross_consistency": self.cross_consistency,
            "fields": [f.as_dict() for f in self.fields],
            "findings": [f.as_dict() for f in self.findings],
            "authenticity": self.authenticity.as_dict(),
            "confidence": self.confidence.as_dict(),
            "disposition": self.disposition,
            "disposition_reason": self.disposition_reason,
            "human_review": self.human_review.as_dict() if self.human_review else None,
            "capabilities_at_analysis": self.capabilities_at_analysis,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


def assert_authenticity_writable(result: AuthenticityResult) -> AuthenticityResult:
    """Guard: VERIFIED is reachable only through an authoritative gateway.

    Slice 1 ships no gateway, so VERIFIED is unreachable by construction.
    """
    if result.state == states.AUTH_VERIFIED and not result.authoritative:
        raise ValueError(
            "AUTHENTICITY_VERIFIED requires an authoritative gateway result; "
            "no such gateway exists in this build.")
    return result
