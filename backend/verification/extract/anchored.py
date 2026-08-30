"""Anchored extraction: find a label, read what follows it.

Reworked from engine-v3/prototypes/extraction_router.py.  The prototype's
anchoring technique is sound; its two-state Result model is not, and is not
carried over.  Here, a field that is not found yields None with an explicit
uncertainty reason -- it never yields a negative finding.  Absence of evidence
is not evidence of a wrong value.
"""

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from .. import privacy, states
from ..models import ExtractedField, Provenance

ANCHOR_WINDOW = 220

_DATE_FORMATS = (
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d",
    "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
)


def find_anchor_presence(text: str, anchors: List[str]
                         ) -> Tuple[Optional[str], Optional[Tuple[int, int]]]:
    """For fields whose value IS the anchor text, e.g. a named authority.

    Returns the matched anchor as it appears in the profile, not as it appears
    in the document, so the value is stable across capitalisation differences.
    """
    for anchor in anchors:
        m = re.search(re.escape(anchor), text, re.IGNORECASE)
        if m:
            return anchor, (m.start(), m.end())
    return None, None


def find_anchored(text: str, anchors: List[str], pattern: Optional[str]
                  ) -> Tuple[Optional[str], Optional[Tuple[int, int]]]:
    """Search for `pattern` in the window following any anchor.

    Deliberately does NOT fall back to a document-wide search: the prototype did,
    and a document-wide match for a generic pattern such as a date attributes a
    value to a label it was never near.
    """
    if not pattern or not anchors:
        return None, None
    compiled = re.compile(pattern, re.IGNORECASE)
    for anchor in anchors:
        for m in re.finditer(re.escape(anchor), text, re.IGNORECASE):
            window_start = m.end()
            window = text[window_start:window_start + ANCHOR_WINDOW]
            hit = compiled.search(window)
            if hit:
                value = hit.group(1) if hit.groups() else hit.group(0)
                span = (window_start + hit.start(), window_start + hit.end())
                return value.strip(), span
    return None, None


def normalize(value: Optional[str], normalizer: str) -> Tuple[Optional[Any], Optional[str]]:
    """Returns (normalized_value, uncertainty_reason)."""
    if value is None:
        return None, None
    if normalizer == "date":
        parsed = parse_date(value)
        if parsed is None:
            return None, "VALUE_FOUND_BUT_NOT_A_READABLE_DATE"
        return parsed.isoformat(), None
    if normalizer == "integer":
        digits = re.sub(r"[^0-9-]", "", value)
        if not digits or digits == "-":
            return None, "VALUE_FOUND_BUT_NOT_A_READABLE_NUMBER"
        try:
            return int(digits), None
        except ValueError:
            return None, "VALUE_FOUND_BUT_NOT_A_READABLE_NUMBER"
    if normalizer == "text":
        cleaned = re.sub(r"\s+", " ", value).strip(" :-\u2013\u2014")
        return (cleaned or None), (None if cleaned else "VALUE_FOUND_BUT_EMPTY")
    return value, None


def parse_date(value: str) -> Optional[date]:
    candidate = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
    return None


def page_for_offset(offsets: Dict[int, int], offset: int) -> Optional[int]:
    page = None
    for page_number in sorted(offsets):
        if offsets[page_number] <= offset:
            page = page_number
        else:
            break
    return page


def extract_field(spec: Dict[str, Any], text: str, offsets: Dict[int, int],
                  profile_id: str, profile_version: str) -> ExtractedField:
    field_id = spec["field_id"]
    anchors = spec.get("anchors") or []
    pattern = spec.get("pattern")
    normalizer = spec.get("normalizer", "none")

    if pattern:
        raw, span = find_anchored(text, anchors, pattern)
    else:
        # No pattern means the anchor text itself is the value.
        raw, span = find_anchor_presence(text, anchors)
    normalized, uncertainty = normalize(raw, normalizer)

    if raw is None:
        # Not found.  UNKNOWN, never a mismatch.
        uncertainty = "FIELD_NOT_FOUND_IN_DOCUMENT"
        confidence = 0.0
    elif normalized is None:
        confidence = 0.3
    else:
        confidence = 0.8

    return ExtractedField(
        field_id=field_id,
        label=spec.get("label") or field_id.replace("_", " ").capitalize(),
        raw_value=raw,
        normalized_value=normalized,
        confidence=confidence,
        field_source=spec["field_source"],
        sensitivity=spec.get("sensitivity", privacy.NON_SENSITIVE),
        uncertainty_reason=uncertainty,
        provenance=Provenance(
            method=states.METHOD_ANCHORED_REGEX,
            page=page_for_offset(offsets, span[0]) if span else None,
            char_span=span,
            profile_id=profile_id,
            profile_version=profile_version,
        ),
    )
