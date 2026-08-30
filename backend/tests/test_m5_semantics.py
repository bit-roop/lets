"""The semantic invariants.

These are the rules that stop this layer from doing harm. Each one guards
against a specific failure: telling an applicant their document is wrong when
it was merely unreadable, blocking them over information that was never found,
or implying a document is genuine when nothing checked it.
"""

import unittest
from datetime import date

from backend.tests import m5_support as support
from backend.verification import states
from backend.verification.checks.runner import run_checks
from backend.verification.models import (AuthenticityResult, ExtractedField,
                                         Provenance, assert_authenticity_writable)
from backend.verification.profiles.registry import get_profile_registry


def _field(field_id, raw=None, normalized=None,
           source=states.RESEARCH_REQUIRED, reason=None):
    return ExtractedField(
        field_id=field_id, label=field_id.replace("_", " ").capitalize(),
        raw_value=raw, normalized_value=normalized,
        confidence=0.0 if raw is None else 0.8, field_source=source,
        uncertainty_reason=reason,
        provenance=Provenance(method=states.METHOD_ANCHORED_REGEX))


class TestMissingInformationIsUnknown(unittest.TestCase):
    """Test 13: absence of evidence is not evidence of a wrong value."""

    def setUp(self):
        self.profile = get_profile_registry().get("S02-FORM-1")

    def test_absent_field_yields_unknown_never_mismatch(self):
        fields = {"document_date": _field("document_date"),
                  "max_workers": _field("max_workers")}
        findings = run_checks(self.profile, fields, identity_matched=True)

        for finding in findings:
            if finding.check_id == "S02F1-IDENTITY":
                continue
            self.assertEqual(finding.outcome, states.OUTCOME_UNKNOWN, finding.check_id)
            self.assertNotEqual(finding.outcome, states.OUTCOME_MISMATCH)

    def test_unknown_findings_are_never_blocking(self):
        fields = {"document_date": _field("document_date")}
        findings = run_checks(self.profile, fields, identity_matched=True)
        for finding in findings:
            if finding.outcome == states.OUTCOME_UNKNOWN:
                self.assertNotEqual(finding.severity, states.BLOCKING,
                                    f"{finding.check_id} would block on absent data")

    def test_a_wrong_value_still_produces_a_mismatch(self):
        """The rule protects absent data, not incorrect data."""
        fields = {"document_date": _field(
            "document_date", raw="01/01/2099", normalized="2099-01-01")}
        findings = {f.check_id: f for f in run_checks(
            self.profile, fields, identity_matched=True, as_of=date(2026, 8, 30))}
        self.assertEqual(findings["S02F1-DATE-FUTURE"].outcome, states.OUTCOME_MISMATCH)


class TestUnreadableIsNotMismatch(unittest.TestCase):
    """Test 14: a document that could not be read has not failed a check."""

    def setUp(self):
        self.api = support.client(self)
        support.ensure_fixtures()
        support.isolated_store(self)
        self.m4 = support.m4_result(self.api, support.PERSONA_B)

    def test_blank_document_routes_to_human_review(self):
        submission_id = support.submit_upload(
            self.api, "sem-app", "S02-FORM-1", "synthetic_blank.pdf")
        record = self.api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": self.m4}).json()

        self.assertEqual(record["extraction"], states.UNREADABLE)
        self.assertEqual(record["disposition"], states.HUMAN_REVIEW_REQUIRED)
        self.assertNotEqual(record["disposition"], states.NEEDS_APPLICANT_ACTION)
        self.assertNotEqual(record["requirement_match"], states.MISMATCH)
        self.assertIn(states.TRIGGER_DOCUMENT_UNREADABLE,
                      record["human_review"]["triggers"])

    def test_unreadable_produces_no_blocking_mismatch(self):
        submission_id = support.submit_upload(
            self.api, "sem-app2", "S02-FORM-1", "synthetic_blank.pdf")
        record = self.api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": self.m4}).json()
        blocking = [f for f in record["findings"]
                    if f["severity"] == states.BLOCKING
                    and f["outcome"] == states.OUTCOME_MISMATCH]
        self.assertFalse(blocking)

    def test_unrecognised_document_is_actionable_but_not_misidentified(self):
        """An unrecognised file is actionable without being named as something else.

        Two distinct mechanisms are at work and they must not be conflated.
        `requirement_match` stays INDETERMINATE because we genuinely cannot say
        what this document is. The identity check nonetheless returns a grounded
        MISMATCH: the text expected on Form No. 1 is definitively absent from
        readable content, which is a real negative observation rather than an
        absence of evidence. So the applicant is told to check their upload --
        the right outcome -- while the record never claims to know what they
        actually sent.
        """
        submission_id = support.submit_upload(
            self.api, "sem-app3", "S02-FORM-1", "synthetic_unrelated.pdf")
        record = self.api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": self.m4}).json()

        self.assertEqual(record["classification"], states.UNKNOWN_TYPE)
        self.assertEqual(record["disposition"], states.NEEDS_APPLICANT_ACTION)

        # We do not know what it is, and the record must not pretend otherwise.
        self.assertEqual(record["requirement_match"], states.INDETERMINATE)
        self.assertNotEqual(record["requirement_match"], states.MISMATCH)
        self.assertIsNone(record["classification_detail"]["label"] if
                          record["classification_detail"]["score"] else None)


class TestWrongDocumentIsActionable(unittest.TestCase):
    """The counterpart: a confidently identified wrong document IS actionable."""

    def test_form_b_in_the_form_1_slot(self):
        api = support.client(self)
        support.ensure_fixtures()
        support.isolated_store(self)
        self.m4 = support.m4_result(api, support.PERSONA_B)
        submission_id = support.submit_upload(
            api, "sem-app4", "S02-FORM-1", "synthetic_form_b.pdf")
        record = api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": self.m4}).json()

        self.assertEqual(record["requirement_match"], states.MISMATCH)
        self.assertEqual(record["disposition"], states.NEEDS_APPLICANT_ACTION)
        self.assertEqual(record["classification_detail"]["label"], "F02-FORM-B")


class TestAuthenticityCannotBeFaked(unittest.TestCase):
    """Tests 11 and 12: VERIFIED is unreachable without an authoritative gateway."""

    def test_verified_requires_an_authoritative_result(self):
        with self.assertRaises(ValueError):
            assert_authenticity_writable(AuthenticityResult(
                state=states.AUTH_VERIFIED, availability="AVAILABLE",
                authoritative=False, provider_id="MOCK"))

    def test_a_mock_gateway_cannot_produce_verified(self):
        """A mock is non-authoritative by definition, so the guard refuses it."""
        with self.assertRaises(ValueError):
            assert_authenticity_writable(AuthenticityResult(
                state=states.AUTH_VERIFIED, availability="AVAILABLE",
                authoritative=False, provider_id="MOCK",
                evidence=["mock gateway said the document is genuine"]))

    def test_an_llm_style_assertion_cannot_produce_verified(self):
        """Test 11: model output has no route to a favourable terminal state."""
        with self.assertRaises(ValueError):
            assert_authenticity_writable(AuthenticityResult(
                state=states.AUTH_VERIFIED, availability="NOT_AVAILABLE",
                authoritative=False, provider_id=None,
                evidence=["a model judged this document to look genuine"]))

    def test_no_profile_can_declare_verified_or_supported(self):
        self.assertNotIn(states.AUTH_VERIFIED, states.DECLARABLE_AUTHENTICITY)
        self.assertNotIn(states.AUTH_SUPPORTED, states.DECLARABLE_AUTHENTICITY)

    def test_applicant_authored_is_distinct_from_no_mechanism(self):
        """'Nothing to check against' is not 'we could not check'."""
        self.assertNotEqual(states.AUTH_NOT_APPLICABLE_APPLICANT_AUTHORED,
                            states.AUTH_NO_MECHANISM_AVAILABLE)

    def test_slice1_records_never_claim_authenticity(self):
        api = support.client(self)
        support.ensure_fixtures()
        support.isolated_store(self)
        self.m4 = support.m4_result(api, support.PERSONA_B)
        submission_id = support.submit_upload(
            api, "sem-app5", "S02-FORM-1", "synthetic_form_1.pdf")
        record = api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": self.m4}).json()

        self.assertEqual(record["authenticity"]["state"],
                         states.AUTH_NOT_APPLICABLE_APPLICANT_AUTHORED)
        self.assertFalse(record["authenticity"]["authoritative"])
        self.assertEqual(record["disposition"], states.ACCEPTED_FOR_REVIEW,
                         "acceptance for review must not depend on authenticity")


class TestNoProfileMeansNotAnalyzed(unittest.TestCase):
    """An evidence item M5 was never taught to read is not thereby acceptable."""

    def test_unprofiled_document_is_not_analyzed(self):
        api = support.client(self)
        support.ensure_fixtures()
        support.isolated_store(self)
        self.m4 = support.m4_result(api, support.PERSONA_B)
        submission_id = support.submit_upload(
            api, "sem-app6", "S02-PREMISES-PROOF", "synthetic_form_1.pdf")
        record = api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": self.m4}).json()

        self.assertEqual(record["disposition"], states.NOT_ANALYZED)
        self.assertEqual(record["disposition_reason"], states.REASON_NO_PROFILE)
        self.assertNotEqual(record["disposition"], states.ACCEPTED_FOR_REVIEW)


class TestConfidenceIsNotASingleScore(unittest.TestCase):

    def test_confidence_is_a_breakdown(self):
        api = support.client(self)
        support.ensure_fixtures()
        support.isolated_store(self)
        self.m4 = support.m4_result(api, support.PERSONA_B)
        submission_id = support.submit_upload(
            api, "sem-app7", "S02-FORM-1", "synthetic_form_1.pdf")
        record = api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": self.m4}).json()

        confidence = record["confidence"]
        self.assertEqual(
            sorted(confidence),
            ["classification_margin", "extraction_mean", "extraction_min",
             "grounded_field_coverage"])
        self.assertNotIn("score", confidence)
        self.assertNotIn("overall", confidence)


class TestFileReuseIsDetectable(unittest.TestCase):
    """Test 12 of the plan's list: identity keyed on the hash, not M4's tuple."""

    def test_same_file_in_two_slots_is_visible(self):
        api = support.client(self)
        support.ensure_fixtures()
        store = support.isolated_store(self)
        m4 = support.m4_result(api, support.PERSONA_B)

        first = support.submit_upload(
            api, "reuse-app", "S02-FORM-1", "synthetic_form_1.pdf")
        second = support.submit_upload(
            api, "reuse-app", "F02-FORM-B", "synthetic_form_1.pdf")
        for submission_id in (first, second):
            api.post("/api/verification/analyze", json={
                "submission_id": submission_id, "m4_result": m4})

        record = store.latest_for_submission(first)
        sightings = store.sightings_for_hash(record["submission_sha256"])
        self.assertEqual(len(sightings), 2)
        self.assertEqual({s["document_id"] for s in sightings},
                         {"S02-FORM-1", "F02-FORM-B"})


if __name__ == "__main__":
    unittest.main()
