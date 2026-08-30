"""Ingestion, extraction and classification.

Covers the guard, native text extraction, and content-based classification,
including the two filename-independence cases that decide whether this layer is
actually reading documents or just reading their names.
"""

import unittest
from pathlib import Path

from backend.tests import m5_support as support
from backend.verification import states
from backend.verification.classify import deterministic as classifier
from backend.verification.extract import anchored
from backend.verification.extract.text import extract_pdf_text
from backend.verification.ingest import guard
from backend.verification.ingest.pdf import PdfStructureError, inventory
from backend.verification.profiles.registry import get_profile_registry

FIXTURES = support.FIXTURE_DIR
PDF_ONLY = ["application/pdf"]


def setUpModule():
    support.ensure_fixtures()


class TestMediaGuard(unittest.TestCase):

    def _check(self, name, declared="application/pdf", formats=PDF_ONLY):
        return guard.check(FIXTURES / name, declared, formats)

    def test_valid_pdf_accepted(self):
        result = self._check("synthetic_form_1.pdf")
        self.assertTrue(result.accepted, result.reasons)
        self.assertEqual(result.detected_mime, "application/pdf")

    def test_mime_spoofing_rejected(self):
        """Declared PDF, contents plain text."""
        result = self._check("synthetic_not_a_pdf.pdf")
        self.assertFalse(result.accepted)

    def test_declared_type_must_match_contents(self):
        result = self._check("synthetic_form_1.pdf", declared="image/png")
        self.assertFalse(result.accepted)

    def test_format_not_accepted_by_the_requirement(self):
        result = self._check("synthetic_form_1.pdf", formats=["image/png"])
        self.assertFalse(result.accepted)

    def test_encrypted_pdf_rejected(self):
        result = self._check("synthetic_encrypted.pdf")
        self.assertFalse(result.accepted)
        self.assertTrue(any("encrypted" in r.lower() for r in result.reasons))

    def test_active_content_rejected(self):
        result = self._check("synthetic_active_content.pdf")
        self.assertFalse(result.accepted)
        self.assertTrue(any("active content" in r.lower() for r in result.reasons))

    def test_empty_file_rejected(self):
        empty = FIXTURES / "synthetic_empty.pdf"
        empty.write_bytes(b"")
        self.addCleanup(empty.unlink)
        self.assertFalse(self._check("synthetic_empty.pdf").accepted)

    def test_save_generations_are_a_note_not_a_verdict(self):
        """A re-saved document is not thereby suspicious."""
        source = (FIXTURES / "synthetic_form_1.pdf").read_bytes()
        multi = FIXTURES / "synthetic_multisave.pdf"
        multi.write_bytes(source + b"\n" + source)
        self.addCleanup(multi.unlink)
        result = self._check("synthetic_multisave.pdf")
        self.assertTrue(result.accepted)
        self.assertTrue(result.notes)

    def test_path_traversal_is_refused(self):
        with self.assertRaises(ValueError):
            guard.resolve_storage_path("../../etc/passwd", FIXTURES)

    def test_missing_stored_file_is_refused(self):
        with self.assertRaises(FileNotFoundError):
            guard.resolve_storage_path("no_such_file.pdf", FIXTURES)


class TestPdfInventory(unittest.TestCase):

    def test_inventory_reads_page_count(self):
        info = inventory(FIXTURES / "synthetic_form_1.pdf")
        self.assertEqual(info.page_count, 1)
        self.assertFalse(info.signature_objects_present)

    def test_broken_structure_raises(self):
        broken = FIXTURES / "synthetic_broken.pdf"
        broken.write_bytes(b"%PDF-1.4\nnot really a pdf body")
        self.addCleanup(broken.unlink)
        with self.assertRaises(PdfStructureError):
            inventory(broken)


class TestNativeExtraction(unittest.TestCase):

    def test_text_pdf_yields_native_text(self):
        result = extract_pdf_text(FIXTURES / "synthetic_form_1.pdf")
        self.assertEqual(result.state, states.NATIVE_TEXT)
        self.assertGreater(result.total_chars, 40)

    def test_blank_pdf_is_unreadable_not_failed(self):
        """No text layer is a property of the document, not a system fault."""
        result = extract_pdf_text(FIXTURES / "synthetic_blank.pdf")
        self.assertEqual(result.state, states.UNREADABLE)
        self.assertNotEqual(result.state, states.FAILED)

    def test_page_offsets_map_back_to_pages(self):
        result = extract_pdf_text(FIXTURES / "synthetic_form_1.pdf")
        offsets = result.page_offsets()
        self.assertEqual(anchored.page_for_offset(offsets, 0), 1)


class TestAnchoredExtraction(unittest.TestCase):

    def test_missing_field_yields_none_with_a_reason(self):
        spec = {"field_id": "x", "field_source": states.RESEARCH_REQUIRED,
                "anchors": ["Nowhere To Be Found"], "pattern": r"(\d+)",
                "normalizer": "integer"}
        field = anchored.extract_field(spec, "some unrelated text", {}, "P", "1")
        self.assertIsNone(field.raw_value)
        self.assertIsNone(field.normalized_value)
        self.assertEqual(field.uncertainty_reason, "FIELD_NOT_FOUND_IN_DOCUMENT")
        self.assertEqual(field.confidence, 0.0)

    def test_value_is_only_read_near_its_anchor(self):
        """A document-wide search would attach 4242 to a label it never sat near."""
        spec = {"field_id": "x", "field_source": states.RESEARCH_REQUIRED,
                "anchors": ["Workers"], "pattern": r"(\d+)", "normalizer": "integer"}
        text = "Invoice 4242\n" + ("filler " * 80) + "\nWorkers: 67"
        field = anchored.extract_field(spec, text, {}, "P", "1")
        self.assertEqual(field.normalized_value, 67)

    def test_unparseable_value_is_flagged_not_guessed(self):
        spec = {"field_id": "d", "field_source": states.RESEARCH_REQUIRED,
                "anchors": ["Date"], "pattern": r"([0-9/]+)", "normalizer": "date"}
        field = anchored.extract_field(spec, "Date: 99/99/9999", {}, "P", "1")
        self.assertIsNotNone(field.raw_value)
        self.assertIsNone(field.normalized_value)
        self.assertEqual(field.uncertainty_reason,
                         "VALUE_FOUND_BUT_NOT_A_READABLE_DATE")

    def test_anchor_presence_field_returns_the_anchor(self):
        spec = {"field_id": "a", "field_source": states.PROFILE_GROUNDED,
                "anchors": ["Directorate of Industrial Safety and Health"],
                "normalizer": "text"}
        field = anchored.extract_field(
            spec, "issued by the directorate of industrial safety and health",
            {}, "P", "1")
        self.assertEqual(field.normalized_value,
                         "Directorate of Industrial Safety and Health")


class TestClassification(unittest.TestCase):

    def setUp(self):
        self.registry = get_profile_registry()
        self.form1 = self.registry.get("S02-FORM-1")
        self.formb = self.registry.get("F02-FORM-B")

    def _classify(self, fixture, slot):
        text = extract_pdf_text(FIXTURES / fixture).full_text
        return classifier.classify(text, slot, self.registry.all())

    def test_correct_document_matches(self):
        outcome = self._classify("synthetic_form_1.pdf", self.form1)
        self.assertEqual(outcome.state, states.MATCHES_EXPECTED)

    def test_wrong_known_document_is_identified_as_such(self):
        """The headline case: Form B uploaded into the Form No. 1 slot."""
        outcome = self._classify("synthetic_form_b.pdf", self.form1)
        self.assertEqual(outcome.state, states.DIFFERENT_KNOWN_TYPE)
        self.assertEqual(outcome.best.document_id, "F02-FORM-B")
        match, identified = classifier.requirement_match_for(outcome)
        self.assertEqual(match, states.MISMATCH)
        self.assertEqual(identified, "F02-FORM-B")

    def test_unrelated_document_is_unknown_not_mismatch(self):
        outcome = self._classify("synthetic_unrelated.pdf", self.form1)
        self.assertEqual(outcome.state, states.UNKNOWN_TYPE)
        match, _ = classifier.requirement_match_for(outcome)
        self.assertEqual(match, states.INDETERMINATE)
        self.assertNotEqual(match, states.MISMATCH)

    def test_empty_text_is_insufficient_evidence(self):
        outcome = classifier.classify("", self.form1, self.registry.all())
        self.assertEqual(outcome.state, states.INSUFFICIENT_EVIDENCE)

    # --- filename independence, both directions ---------------------------

    def test_misnamed_correct_document_still_matches(self):
        outcome = self._classify("linux_assignment.pdf", self.form1)
        self.assertEqual(outcome.state, states.MATCHES_EXPECTED)

    def test_correctly_named_wrong_document_still_fails(self):
        outcome = self._classify("factory_form_no_1.pdf", self.form1)
        self.assertEqual(outcome.state, states.DIFFERENT_KNOWN_TYPE)

    def test_classifier_takes_no_filename_argument(self):
        """Structural guarantee: there is no parameter for a filename."""
        import inspect
        signature = inspect.signature(classifier.classify)
        self.assertEqual(list(signature.parameters),
                         ["text", "expected_profile", "all_profiles"])


if __name__ == "__main__":
    unittest.main()
