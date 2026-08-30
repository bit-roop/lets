"""M5 API contract."""

import json
import unittest
from unittest import mock

from backend.tests import m5_support as support
from backend.verification import states


class TestAnalyzeEndpoint(unittest.TestCase):

    def setUp(self):
        self.api = support.client(self)
        support.ensure_fixtures()
        support.isolated_store(self)
        self.m4 = support.m4_result(self.api, support.PERSONA_B)

    def test_unknown_submission_is_400(self):
        response = self.api.post("/api/verification/analyze", json={
            "submission_id": "does-not-exist", "m4_result": self.m4})
        self.assertEqual(response.status_code, 400)

    def test_missing_submission_id_is_422(self):
        self.assertEqual(
            self.api.post("/api/verification/analyze", json={}).status_code, 422)

    def test_missing_m4_result_is_422(self):
        """M5 has no fallback that would derive applicability itself."""
        self.assertEqual(
            self.api.post("/api/verification/analyze",
                          json={"submission_id": "x"}).status_code, 422)

    def test_server_errors_do_not_leak_exception_detail(self):
        """A failure must not hand the client a traceback, a path, or a value."""
        from backend.verification import api as verification_api
        submission_id = support.submit_upload(
            self.api, "leak-app", "S02-FORM-1", "synthetic_form_1.pdf")
        secret = "/secret/path/applicant-aadhaar-123412341234.pdf"
        with mock.patch("backend.verification.api.analyze",
                        side_effect=RuntimeError(secret)):
            response = self.api.post("/api/verification/analyze", json={
                "submission_id": submission_id, "m4_result": self.m4})
        self.assertEqual(response.status_code, 500)
        body = response.text
        self.assertNotIn(secret, body)
        self.assertNotIn("RuntimeError", body)
        self.assertNotIn("Traceback", body)
        self.assertEqual(response.json()["detail"], verification_api.GENERIC_ERROR)

    def test_record_shape(self):
        submission_id = support.submit_upload(
            self.api, "api-app", "S02-FORM-1", "synthetic_form_1.pdf")
        record = self.api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": self.m4}).json()

        for key in ("record_id", "submission_id", "document_id",
                    "m4_applicability_observed", "requirement_match", "ingestion",
                    "extraction", "classification", "internal_consistency",
                    "cross_consistency", "authenticity", "confidence",
                    "disposition", "fields", "findings", "m4_observations",
                    "capabilities_at_analysis"):
            self.assertIn(key, record)

        self.assertIn(record["disposition"], states.DISPOSITION)
        self.assertIn(record["ingestion"], states.INGESTION)
        self.assertIn(record["extraction"], states.EXTRACTION)
        self.assertIn(record["classification"], states.CLASSIFICATION)
        self.assertIn(record["requirement_match"], states.REQUIREMENT_MATCH)
        self.assertIn(record["authenticity"]["state"], states.AUTHENTICITY)

    def test_every_field_and_finding_carries_provenance(self):
        submission_id = support.submit_upload(
            self.api, "api-app2", "S02-FORM-1", "synthetic_form_1.pdf")
        record = self.api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": self.m4}).json()

        for field in record["fields"]:
            self.assertIn(field["field_source"], states.FIELD_SOURCES)
            self.assertTrue(field["provenance"]["method"])
            self.assertTrue(field["provenance"]["ruleset_version"])
            self.assertIsNone(field["provenance"]["model_id"],
                              "slice 1 uses no model; model_id must stay null")
        for finding in record["findings"]:
            self.assertIn(finding["outcome"], states.OUTCOMES)
            self.assertIn(finding["severity"], states.SEVERITIES)
            self.assertTrue(finding["provenance"]["method"])

    def test_m4_observation_is_carried_verbatim(self):
        submission_id = support.submit_upload(
            self.api, "api-app3", "S02-FORM-1", "synthetic_form_1.pdf")
        record = self.api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": self.m4}).json()

        observations = record["m4_observations"]
        self.assertTrue(observations)
        observation = observations[0]
        self.assertEqual(observation["requirement_id"], "S02-REQ-001")
        self.assertEqual(observation["approval_id"], "S-02")
        self.assertEqual(observation["source_authority"],
                         "Directorate of Industrial Safety and Health, Maharashtra")
        self.assertEqual(observation["source_checklist_item"], "Form No. 1")


class TestRecordsEndpoint(unittest.TestCase):

    def test_records_are_scoped_to_the_application(self):
        api = support.client(self)
        support.ensure_fixtures()
        support.isolated_store(self)

        m4 = support.m4_result(api, support.PERSONA_B)
        submission_id = support.submit_upload(
            api, "rec-app", "S02-FORM-1", "synthetic_form_1.pdf")
        api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": m4})

        mine = api.get("/api/verification/records",
                       params={"application_id": "rec-app"}).json()
        self.assertEqual(len(mine["records"]), 1)

        other = api.get("/api/verification/records",
                        params={"application_id": "someone-else"}).json()
        self.assertEqual(other["records"], [])


class TestReadinessOverlay(unittest.TestCase):

    def setUp(self):
        self.api = support.client(self)
        support.ensure_fixtures()
        support.isolated_store(self)

    def test_malformed_m4_result_is_400(self):
        response = self.api.post("/api/verification/evidence", json={
            "application_id": "x", "m4_result": {"not": "an m4 result"}})
        self.assertEqual(response.status_code, 400)

    def test_counters_are_internally_consistent(self):
        m4 = support.m4_result(self.api, support.PERSONA_B)
        for document_id, fixture in (("S02-FORM-1", "synthetic_form_1.pdf"),
                                     ("F02-FORM-B", "synthetic_form_b.pdf")):
            submission_id = support.submit_upload(
                self.api, "ov-app", document_id, fixture)
            self.api.post("/api/verification/analyze", json={
                "submission_id": submission_id, "m4_result": m4})

        overlay = self.api.post("/api/verification/evidence", json={
            "application_id": "ov-app", "m4_result": m4,
            "m4_readiness": support.m4_readiness(
                self.api, "ov-app", support.PERSONA_B)}).json()
        counters = overlay["m5_evidence"]["counters"]

        self.assertEqual(counters["m5_supported_applicable_count"], 2)
        self.assertEqual(counters["m5_analyzed_count"], 2)
        self.assertEqual(counters["m5_accepted_for_review_count"], 2)
        self.assertEqual(counters["m5_authenticity_established_count"], 0,
                         "no authenticity mechanism exists in this build")

        dispositions = sum(counters[k] for k in (
            "m5_accepted_for_review_count", "m5_needs_action_count",
            "m5_human_review_count", "m5_rejected_structural_count",
            "m5_not_analyzed_count"))
        self.assertEqual(dispositions, counters["m5_supported_applicable_count"])

        denominator_entries = [e for e in overlay["m5_evidence"]["per_requirement"]
                               if e["in_m5_denominator"]]
        self.assertEqual(len(denominator_entries),
                         counters["m5_supported_applicable_count"])

    def test_denominator_definition_is_published(self):
        overlay = self.api.post("/api/verification/evidence", json={
            "application_id": "ov-app2",
            "m4_result": support.m4_result(self.api, support.PERSONA_B)}).json()
        definition = overlay["m5_evidence"]["denominator_definition"].lower()
        self.assertIn("not treated as inapplicable", definition)


class TestCapabilitiesEndpoint(unittest.TestCase):

    def test_capabilities_report_what_is_absent(self):
        api = support.client(self)
        payload = api.get("/api/verification/capabilities").json()
        capabilities = payload["capabilities"]

        self.assertTrue(capabilities["native_pdf_text"])
        for absent in ("ocr", "llm", "qr_decoding", "pdf_signature_validation",
                       "cross_document_checks", "verified_state_reachable"):
            self.assertFalse(capabilities[absent],
                             f"{absent} is claimed but not implemented in slice 1")

        self.assertEqual(capabilities["authoritative_gateways"], {})
        self.assertEqual(len(payload["profiles"]), 2)
        self.assertEqual(len(payload["not_analyzed_document_ids"]), 34)

    def test_every_profile_publishes_its_limitations(self):
        api = support.client(self)
        for profile in api.get("/api/verification/capabilities").json()["profiles"]:
            self.assertTrue(profile["limitations"])


if __name__ == "__main__":
    unittest.main()
