"""Deterministic document classification from content.

The filename is never an input.  It is not passed to this module and there is
no parameter through which it could arrive.  A correctly named wrong document
must still fail; a misnamed correct document must still be able to match.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .. import states


@dataclass
class Candidate:
    document_id: str
    profile_id: str
    score: float
    matched: List[str] = field(default_factory=list)
    penalised: List[str] = field(default_factory=list)


@dataclass
class ClassificationOutcome:
    state: str
    best: Optional[Candidate]
    runner_up: Optional[Candidate]
    margin: Optional[float]
    candidates: List[Candidate] = field(default_factory=list)


def score_profile(text: str, profile) -> Candidate:
    haystack = _normalise(text)
    score, matched, penalised = 0.0, [], []

    for anchor in profile.anchors_required:
        if _normalise(anchor["text"]) in haystack:
            score += float(anchor["weight"])
            matched.append(anchor["text"])

    for anchor in profile.anchors_forbidden:
        if _normalise(anchor["text"]) in haystack:
            score -= float(anchor["weight"])
            penalised.append(anchor["text"])

    return Candidate(profile.document_id, profile.profile_id, score, matched, penalised)


def classify(text: str, expected_profile, all_profiles) -> ClassificationOutcome:
    """Classify extracted text against every known profile.

    `expected_profile` is the profile for the slot the applicant uploaded into.
    It gets no scoring advantage; it only decides how the result is labelled.
    """
    if not text or not text.strip():
        return ClassificationOutcome(states.INSUFFICIENT_EVIDENCE, None, None, None, [])

    candidates = sorted(
        (score_profile(text, p) for p in all_profiles),
        key=lambda c: c.score, reverse=True)

    if not candidates:
        return ClassificationOutcome(states.UNKNOWN_TYPE, None, None, None, [])

    best = candidates[0]
    runner_up = candidates[1] if len(candidates) > 1 else None
    margin = (best.score - runner_up.score) if runner_up else best.score

    thresholds = expected_profile.thresholds if expected_profile else {}
    min_score = float(thresholds.get("classification_min_score", 4.0))
    min_margin = float(thresholds.get("classification_min_margin", 1.5))

    if best.score < min_score:
        # Nothing scored well enough to name a type.
        return ClassificationOutcome(states.UNKNOWN_TYPE, best, runner_up, margin, candidates)

    if runner_up is not None and margin < min_margin:
        # Two candidates are too close to separate honestly.
        return ClassificationOutcome(
            states.INSUFFICIENT_EVIDENCE, best, runner_up, margin, candidates)

    if expected_profile is not None and best.document_id == expected_profile.document_id:
        return ClassificationOutcome(
            states.MATCHES_EXPECTED, best, runner_up, margin, candidates)

    return ClassificationOutcome(
        states.DIFFERENT_KNOWN_TYPE, best, runner_up, margin, candidates)


def requirement_match_for(outcome: ClassificationOutcome) -> Tuple[str, Optional[str]]:
    """Map a classification outcome onto requirement_match.

    INSUFFICIENT_EVIDENCE and UNKNOWN_TYPE do NOT produce MISMATCH: not being
    able to identify a document is not the same as identifying it as the wrong
    one.  Only a confident identification of a *different* known type does.
    """
    if outcome.state == states.MATCHES_EXPECTED:
        return states.MATCH, None
    if outcome.state == states.DIFFERENT_KNOWN_TYPE:
        return states.MISMATCH, outcome.best.document_id if outcome.best else None
    return states.INDETERMINATE, None


def _normalise(value: str) -> str:
    return " ".join(value.lower().replace("\u2013", "-").replace("\u2014", "-").split())
