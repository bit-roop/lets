"""What M5 is allowed to keep, and what it must never write down.

The pipeline necessarily reads an applicant's document. These tests hold the
line between reading a value and retaining it: raw extracted text reaches the
checks and then stops, and neither the record store nor an API response nor a
log line may carry it onward.
"""

import json
import logging
import sqlite3
import unittest
from unittest import mock

from backend.tests import m5_support as support
from backend.verification import privacy, states
from backend.verification.api import GENERIC_ERROR
from backend.verification.logging_safe import log_failure

#: Values planted in the synthetic Form No. 1 fixture. Invented for testing.
FIXTURE_OCCUPIER_NAME = "Aarav Deshmukh"
FIXTURE_OCCUPIER_SURNAME = "Deshmukh"

#: Body text that appears in the fixture but is not an extraction target.
FIXTURE_BODY_TEXT = "Application for registration and grant of licence"


class TestMaskingPrimitives(unittest.TestCase):

    def test_name_masking_keeps_initials_only(self):
        self.assertEqual(privacy.mask_name("Aarav Deshmukh"), "A**** D*******")

    def test_identifier_masking_keeps_a_trailing_fragment(self):
        self.assertEqual(privacy.mask_identifier("ABCDE1234F"), "******234F")

    def test_aadhaar_like_value_is_never_returned_in_full(self):
        masked = privacy.mask_identifier("123412341234")
        self.assertNotIn("123412341234", masked)
        self.assertTrue(masked.startswith("*"))
        self.assertEqual(len(masked), 12)

    def test_short_identifier_is_fully_masked(self):
        self.assertEqual(privacy.mask_identifier("12"), "**")

    def test_non_sensitive_values_pass_through(self):
        self.assertEqual(privacy.safe_display("Form No. 1", privacy.NON_SENSITIVE),
                         "Form No. 1")
        self.assertEqual(privacy.safe_display(67, privacy.QUANTITY), "67")

    def test_absent_value_stays_absent(self):
        self.assertIsNone(privacy.safe_display(None, privacy.PERSONAL_NAME))


class TestRawValuesAreNotPersisted(unittest.TestCase):

    def setUp(self):
        self.api = support.client(self)
        support.ensure_fixtures()
        self.store = support.isolated_store(self)
        self.m4 = support.m4_result(self.api, support.PERSONA_B)
        submission_id = support.submit_upload(
            self.api, "priv-app", "S02-FORM-1", "synthetic_form_1.pdf")
        self.record = self.api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": self.m4}).json()

    def _stored_payload(self) -> str:
        with sqlite3.connect(str(self.store.path)) as conn:
            rows = conn.execute("SELECT payload FROM verification_records").fetchall()
        self.assertTrue(rows, "nothing was persisted")
        return "\n".join(row[0] for row in rows)

    def test_the_extraction_actually_happened(self):
        """Guard the premise: if extraction silently stopped working, the
        privacy assertions below would pass for the wrong reason."""
        by_id = {f["field_id"]: f for f in self.record["fields"]}
        self.assertTrue(by_id["occupier_name"]["value_present"])
        self.assertEqual(self.record["disposition"], states.ACCEPTED_FOR_REVIEW)

    def test_personal_name_is_not_in_the_database(self):
        payload = self._stored_payload()
        self.assertNotIn(FIXTURE_OCCUPIER_NAME, payload)
        self.assertNotIn(FIXTURE_OCCUPIER_SURNAME, payload)

    def test_personal_name_is_stored_masked_and_marked(self):
        by_id = {f["field_id"]: f for f in self.record["fields"]}
        occupier = by_id["occupier_name"]
        self.assertTrue(occupier["masked"])
        self.assertEqual(occupier["sensitivity"], privacy.PERSONAL_NAME)
        self.assertEqual(occupier["display_value"], "A**** D*******")

    def test_no_field_carries_a_raw_or_normalized_value_off_the_pipeline(self):
        for field in self.record["fields"]:
            self.assertNotIn("raw_value", field)
            self.assertNotIn("normalized_value", field)
        payload = json.loads(self._stored_payload())
        for field in payload["fields"]:
            self.assertNotIn("raw_value", field)
            self.assertNotIn("normalized_value", field)

    def test_document_body_text_is_not_persisted(self):
        """The full extracted text stays in memory for the duration of the run."""
        self.assertNotIn(FIXTURE_BODY_TEXT, self._stored_payload())

    def test_findings_do_not_carry_unreduced_values(self):
        for finding in self.record["findings"]:
            if finding["observed"]:
                self.assertNotIn(FIXTURE_OCCUPIER_NAME, finding["observed"])
                self.assertNotIn(FIXTURE_OCCUPIER_SURNAME, finding["observed"])

    def test_non_sensitive_metadata_survives(self):
        """Redaction must not be so blunt that verification stops being useful."""
        by_id = {f["field_id"]: f for f in self.record["fields"]}
        self.assertIn("Factory Form No. 1", by_id["document_identity_text"]["display_value"])
        self.assertEqual(by_id["issuing_context_text"]["display_value"],
                         "Directorate of Industrial Safety and Health")
        self.assertEqual(by_id["document_date"]["display_value"], "2026-05-12")
        self.assertEqual(by_id["max_workers"]["display_value"], "67")

    def test_api_records_endpoint_does_not_expose_the_raw_name(self):
        body = self.api.get("/api/verification/records",
                            params={"application_id": "priv-app"}).text
        self.assertNotIn(FIXTURE_OCCUPIER_NAME, body)
        self.assertNotIn(FIXTURE_OCCUPIER_SURNAME, body)
        self.assertIn("A**** D*******", body)

    def test_every_profile_field_declares_a_storage_rule(self):
        from backend.verification.profiles.registry import get_profile_registry
        for profile in get_profile_registry().all():
            for field in profile.fields:
                self.assertIn(field.get("sensitivity"), privacy.SENSITIVITIES,
                              f"{profile.profile_id}:{field['field_id']}")


class TestProfileLoaderRequiresSensitivity(unittest.TestCase):

    def test_a_field_without_a_sensitivity_is_rejected(self):
        import json as _json
        from backend.verification import m4_gateway
        from backend.verification.profiles import loader

        raw = _json.loads(
            (loader.PROFILE_ROOT / "S02-FORM-1.v1.json").read_text(encoding="utf-8"))
        raw["fields"][0].pop("sensitivity")
        with self.assertRaises(loader.ProfileError) as ctx:
            loader.validate(raw, set(m4_gateway.document_ids()), m4_gateway.spec, set())
        self.assertIn("sensitivity", str(ctx.exception))


class TestSafeLogging(unittest.TestCase):
    """A log line is somewhere data comes to rest, so it gets the same rules."""

    SECRET_PATH = "/srv/uploads/applicant/aadhaar-123412341234.pdf"
    SECRET_PII = "Aarav Deshmukh"

    def _capture(self, exc, **kwargs):
        with self.assertLogs("m5-verification", level="DEBUG") as captured:
            log_failure("analyze", exc, **kwargs)
        return "\n".join(captured.output)

    def _raise_nested(self):
        try:
            raise ValueError(
                f"failed to parse {self.SECRET_PATH} for {self.SECRET_PII}\n"
                f'Traceback (most recent call last):\n  File "{self.SECRET_PATH}", '
                f'line 1, in <module>')
        except ValueError as exc:
            return exc

    def test_no_path_pii_or_traceback_text_reaches_the_log(self):
        output = self._capture(self._raise_nested(), submission_id="abc-123")
        self.assertNotIn(self.SECRET_PATH, output)
        self.assertNotIn(self.SECRET_PII, output)
        self.assertNotIn("Traceback", output)
        self.assertNotIn("failed to parse", output)

    def test_useful_diagnostics_survive(self):
        output = self._capture(self._raise_nested(), submission_id="abc-123",
                               application_id="app-1")
        self.assertIn("ValueError", output)
        self.assertIn("abc-123", output)
        self.assertIn("app-1", output)
        self.assertIn("stage=analyze", output)
        self.assertIn("test_m5_privacy.py:", output,
                      "the innermost frame should be a basename and line number")

    def test_an_unloggable_identifier_is_dropped_not_logged(self):
        output = self._capture(self._raise_nested(),
                               submission_id="id with spaces and /paths")
        self.assertNotIn("/paths", output)
        self.assertIn("<unloggable>", output)

    def test_logging_never_raises(self):
        class Awkward(Exception):
            def __str__(self):
                raise RuntimeError("uncooperative exception")
        try:
            raise Awkward()
        except Awkward as exc:
            self._capture(exc, submission_id="ok-1")


class TestApiErrorsDoNotLeak(unittest.TestCase):

    SECRET_PATH = "/srv/secret/applicant-aadhaar-123412341234.pdf"
    SECRET_PII = "Aarav Deshmukh"

    def test_client_gets_only_the_generic_message_and_the_log_stays_clean(self):
        api = support.client(self)
        support.ensure_fixtures()
        support.isolated_store(self)
        m4 = support.m4_result(api, support.PERSONA_B)
        submission_id = support.submit_upload(
            api, "leak-app", "S02-FORM-1", "synthetic_form_1.pdf")

        boom = RuntimeError(
            f'{self.SECRET_PATH} {self.SECRET_PII}\nTraceback (most recent call '
            f'last):\n  File "{self.SECRET_PATH}", line 9, in parse')

        with mock.patch("backend.verification.api.analyze", side_effect=boom):
            with self.assertLogs("m5-verification", level="DEBUG") as captured:
                response = api.post("/api/verification/analyze", json={
                    "submission_id": submission_id, "m4_result": m4})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], GENERIC_ERROR)
        for forbidden in (self.SECRET_PATH, self.SECRET_PII, "Traceback", "RuntimeError("):
            self.assertNotIn(forbidden, response.text)

        logged = "\n".join(captured.output)
        self.assertNotIn(self.SECRET_PATH, logged)
        self.assertNotIn(self.SECRET_PII, logged)
        self.assertNotIn("Traceback", logged)
        self.assertIn("RuntimeError", logged)
        self.assertIn(submission_id, logged)


if __name__ == "__main__":
    unittest.main()
