"""Deterministic checks.

Every check returns one of five outcomes.  The rule that governs all of them:

    a field that was not found yields UNKNOWN, never MISMATCH.

This is the document-layer restatement of the three-valued discipline in
engine-v3/engine/tri.py.  Collapsing "we did not find it" into "it is wrong"
would produce false rejections and is the failure mode this layer exists to
avoid.
"""

from datetime import date
from typing import Dict, List, Optional

from .. import privacy, states
from ..models import ExtractedField, Finding, Provenance


def run_checks(profile, fields: Dict[str, ExtractedField],
               identity_matched: bool, as_of: Optional[date] = None) -> List[Finding]:
    as_of = as_of or date.today()
    findings: List[Finding] = []
    provenance = Provenance(
        method=states.METHOD_DETERMINISTIC,
        profile_id=profile.profile_id,
        profile_version=profile.version,
    )

    for check in profile.checks:
        kind = check["kind"]
        if kind == "identity_anchor_present":
            findings.append(_identity(check, identity_matched, provenance))
        elif kind == "date_well_formed":
            findings.append(_date_well_formed(check, fields, provenance))
        elif kind == "date_not_future":
            findings.append(_date_not_future(check, fields, provenance, as_of))
        elif kind == "integer_non_negative":
            findings.append(_integer_non_negative(check, fields, provenance))

    return findings


def _input_field(check, fields) -> Optional[ExtractedField]:
    for field_id in check.get("inputs", []):
        if field_id == "__identity__":
            continue
        return fields.get(field_id)
    return None


def _identity(check, matched: bool, provenance) -> Finding:
    if matched:
        return Finding(
            check_id=check["check_id"], outcome=states.OUTCOME_MATCH,
            severity=check["severity"],
            message="The document contains the text expected for this evidence item.",
            provenance=provenance, inputs=["__identity__"])
    return Finding(
        check_id=check["check_id"], outcome=states.OUTCOME_MISMATCH,
        severity=check["severity"], message=check.get("message", ""),
        remedy=check.get("remedy"), provenance=provenance, inputs=["__identity__"])


def _date_well_formed(check, fields, provenance) -> Finding:
    field = _input_field(check, fields)
    if field is None or field.raw_value is None:
        return _unknown(check, provenance, "No date was found in this document.")
    if field.normalized_value is None:
        return Finding(
            check_id=check["check_id"], outcome=states.OUTCOME_MISMATCH,
            severity=check["severity"], message=check.get("message", ""),
            remedy=check.get("remedy"), provenance=provenance,
            inputs=[field.field_id], observed=field.display_value)
    return Finding(
        check_id=check["check_id"], outcome=states.OUTCOME_MATCH,
        severity=check["severity"], message="The date reads as a valid calendar date.",
        provenance=provenance, inputs=[field.field_id],
        observed=field.display_value)


def _date_not_future(check, fields, provenance, as_of: date) -> Finding:
    field = _input_field(check, fields)
    if field is None or field.normalized_value is None:
        return _unknown(check, provenance, "No readable date was available to check.")
    try:
        parsed = date.fromisoformat(str(field.normalized_value))
    except ValueError:
        return _unknown(check, provenance, "No readable date was available to check.")
    if parsed > as_of:
        return Finding(
            check_id=check["check_id"], outcome=states.OUTCOME_MISMATCH,
            severity=check["severity"], message=check.get("message", ""),
            remedy=check.get("remedy"), provenance=provenance,
            inputs=[field.field_id], observed=parsed.isoformat(),
            expected=f"on or before {as_of.isoformat()}")
    return Finding(
        check_id=check["check_id"], outcome=states.OUTCOME_MATCH,
        severity=check["severity"], message="The date is not in the future.",
        provenance=provenance, inputs=[field.field_id], observed=parsed.isoformat())


def _integer_non_negative(check, fields, provenance) -> Finding:
    field = _input_field(check, fields)
    if field is None or field.normalized_value is None:
        return _unknown(check, provenance, "No number was found to check.")
    try:
        value = int(field.normalized_value)
    except (TypeError, ValueError):
        return _unknown(check, provenance, "No number was found to check.")
    if value < 0:
        return Finding(
            check_id=check["check_id"], outcome=states.OUTCOME_MISMATCH,
            severity=check["severity"], message=check.get("message", ""),
            remedy=check.get("remedy"), provenance=provenance,
            inputs=[field.field_id], observed=str(value))
    return Finding(
        check_id=check["check_id"], outcome=states.OUTCOME_MATCH,
        severity=check["severity"], message="The number is a plausible whole number.",
        provenance=provenance, inputs=[field.field_id], observed=str(value))


def _unknown(check, provenance, message: str) -> Finding:
    """Absence of information.  Never BLOCKING, never a mismatch."""
    return Finding(
        check_id=check["check_id"], outcome=states.OUTCOME_UNKNOWN,
        severity=states.INFORMATIONAL, message=message,
        provenance=provenance, inputs=check.get("inputs", []))
