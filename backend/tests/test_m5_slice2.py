"""Focused Slice 2 tests for grounded evidence findings and applicant actions."""

import unittest

from backend.verification import states
from backend.verification.models import ExtractedField, Provenance
from backend.verification.profiles.registry import get_profile_registry
from backend.verification.service import _grounded_field_findings


def _field(field_id, label, value):
    return ExtractedField(
        field_id=field_id,
        label=label,
        raw_value=value,
        normalized_value=value,
        confidence=0.8 if value else 0.0,
        field_source=states.PROFILE_GROUNDED,
        provenance=Provenance(
            method=states.METHOD_ANCHORED_REGEX,
            profile_id="PROF-S02-FORM-1",
            profile_version="1.0.0"),
    )


class TestGroundedEvidenceFindings(unittest.TestCase):
    def setUp(self):
        self.profile = get_profile_registry().get("S02-FORM-1")

    def test_present_grounded_field_is_explicit_and_traceable(self):
        findings = _grounded_field_findings(
            self.profile,
            [_field("issuing_context_text", "Authority named in the document", "DISH")],
        )
        finding = next(f for f in findings if f.inputs == ["issuing_context_text"])
        self.assertEqual(finding.outcome, states.OUTCOME_MATCH)
        self.assertEqual(finding.severity, states.INFORMATIONAL)
        self.assertEqual(finding.provenance.profile_id, self.profile.profile_id)
        self.assertEqual(finding.observed, "DISH")

    def test_missing_grounded_field_is_unknown_and_actionable(self):
        findings = _grounded_field_findings(
            self.profile,
            [_field("issuing_context_text", "Authority named in the document", None)],
        )
        finding = next(f for f in findings if f.inputs == ["issuing_context_text"])
        self.assertEqual(finding.outcome, states.OUTCOME_UNKNOWN)
        self.assertNotEqual(finding.outcome, states.OUTCOME_MISMATCH)
        self.assertEqual(finding.severity, states.INFORMATIONAL)
        self.assertTrue(finding.remedy)

    def test_research_required_field_never_creates_grounded_finding(self):
        field = _field("document_date", "Date printed on the form", None)
        field = ExtractedField(
            field_id=field.field_id, label=field.label, raw_value=None,
            normalized_value=None, confidence=0.0,
            field_source=states.RESEARCH_REQUIRED,
            provenance=field.provenance,
        )
        findings = _grounded_field_findings(self.profile, [field])
        self.assertEqual(findings, [])

if __name__ == "__main__":
    unittest.main()
