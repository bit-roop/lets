import json
import threading
import time
import unittest
from unittest.mock import patch

import requests
import uvicorn

from backend.documents.conditions import evaluate_condition
from backend.documents.models import DocumentSubmission
from backend.documents.readiness import compute_readiness
from backend.documents.registry import DocumentRegistry, RegistryError, get_document_registry
from backend.documents.submissions import SubmissionStore, safe_filename
from backend.documents.validators import validate_structured_fields
from backend.documents.service import requirements_for_application
from backend.engine_adapter import build_workflow_for_facts
from backend.main import app


class TestM4Registry(unittest.TestCase):
    def test_seeded_scope_and_provenance(self):
        registry = get_document_registry()
        self.assertEqual(registry.supported_approval_ids(), ["F-02", "S-02", "S-03"])
        self.assertEqual(len(registry.coverage()), 16)
        self.assertEqual(len(registry.requirements()), 51)
        for req in registry.requirements():
            self.assertTrue(req.source.source_id)
            self.assertTrue(req.source.last_verified)
            self.assertTrue(req.source.title)

    def test_unsupported_coverage_is_explicit(self):
        unsupported = [c.approval_id for c in get_document_registry().coverage() if c.status == "UNSUPPORTED"]
        self.assertEqual(len(unsupported), 13)
        self.assertNotIn("F-02", unsupported)

    def test_malformed_registry_rejected(self):
        calls = iter([{}, [], {}, [{"requirement_id": "x"}], [], []])
        with patch("backend.documents.registry._read", side_effect=lambda path: next(calls)):
            with self.assertRaises(RegistryError):
                DocumentRegistry("unused")

    def test_scope_unclear_and_unsupported_blocking_records_rejected(self):
        source = {"SRC": {"authority": "Test", "title": "Test", "source_url": "https://example.test"}}
        specs = [{"document_id": "D", "name": "D", "item_kind": "UPLOAD_DOCUMENT", "description": "D"}]
        coverage = {"X": {"status": "SUPPORTED", "reason": "test"}}
        for status in ("VERIFIED_SCOPE_UNCLEAR", "UNSUPPORTED"):
            calls = iter([source, specs, coverage, [{"requirement_id":"R","approval_id":"X","document_id":"D","obligation":"MANDATORY","blocking":True,"source_id":"SRC","verification_status":status,"last_verified":"2026-08-30"}], [], []])
            with patch("backend.documents.registry._read", side_effect=lambda path: next(calls)):
                with self.assertRaises(RegistryError):
                    DocumentRegistry("unused")


class TestM4ConditionsAndValidation(unittest.TestCase):
    def test_three_valued_conditions(self):
        condition = {"fact": "manufacturing_processing", "op": "==", "value": True}
        self.assertEqual(evaluate_condition(condition, {"manufacturing_processing": True})[0], "TRUE")
        self.assertEqual(evaluate_condition(condition, {"manufacturing_processing": False})[0], "FALSE")
        self.assertEqual(evaluate_condition(condition, {})[0], "UNKNOWN")

    def test_format_only_and_cross_document_consistency(self):
        result = validate_structured_fields({"pan": "ABCDE1234F", "gstin": "27ABCDE1234F1Z5"})
        self.assertEqual(result["status"], "FORMAT_ONLY")
        self.assertEqual(validate_structured_fields({"pan": "BAD"})["status"], "FORMAT_INVALID")
        mismatch = validate_structured_fields({"pan": "ABCDE1234F", "gstin": "27ZZZZZ1234F1Z5"})
        self.assertIn("INCONSISTENT", [x["code"] for x in mismatch["issues"]])

    def test_aadhaar_is_masked(self):
        result = validate_structured_fields({"aadhaar": "123412341234"})
        self.assertNotIn("123412341234", json.dumps(result))
        self.assertEqual(result["fields"]["aadhaar"], "********1234")

    def test_readiness_states_and_unsupported_never_ready(self):
        registry = get_document_registry()
        f02 = registry.requirements(["F-02"])
        self.assertEqual(compute_readiness("E-05", "UNSUPPORTED", [], [], {}, "APPLICABLE").status, "UNSUPPORTED")
        known = [r for r in f02 if not r.condition]
        result = compute_readiness("F-02", "SUPPORTED", known, [], {}, "APPLICABLE")
        self.assertEqual(result.status, "INCOMPLETE")
        conditional = [r for r in f02 if r.condition]
        result = compute_readiness("F-02", "SUPPORTED", conditional, [], {}, "APPLICABLE")
        self.assertEqual(result.status, "INDETERMINATE")

    def test_readiness_requires_valid_submission(self):
        req = next(r for r in get_document_registry().requirements(["F-02"]) if r.requirement_id == "F02-REQ-001")
        def submission(state, validation=None, reused_from=None):
            return DocumentSubmission("s-" + state, req.document_id, "app", state=state, validation=validation, reused_from=reused_from)
        self.assertEqual(compute_readiness("F-02", "SUPPORTED", [req], [submission("PROVIDED_UNVALIDATED")], {}, "APPLICABLE").status, "INCOMPLETE")
        self.assertEqual(compute_readiness("F-02", "SUPPORTED", [req], [submission("PROVIDED_UNVALIDATED", {"status":"FORMAT_INVALID"})], {}, "APPLICABLE").status, "INCOMPLETE")
        self.assertEqual(compute_readiness("F-02", "SUPPORTED", [req], [submission("VALID")], {}, "APPLICABLE").status, "READY")

    def test_supporting_invalid_evidence_does_not_block(self):
        req = next(r for r in get_document_registry().requirements(["F-02"]) if r.requirement_id == "F02-REQ-003")
        sub = DocumentSubmission("support", req.document_id, "app", state="PROVIDED_UNVALIDATED", validation={"status":"FORMAT_INVALID"})
        self.assertEqual(compute_readiness("F-02", "SUPPORTED", [req], [sub], {}, "APPLICABLE").status, "READY")

    def test_reuse_requires_valid_target_and_exact_identity(self):
        req = next(r for r in get_document_registry().requirements(["F-02"]) if r.requirement_id == "F02-REQ-002")
        valid = DocumentSubmission("valid", req.document_id, "app", state="VALID")
        reused = DocumentSubmission("reused", req.document_id, "app", state="REUSED_FROM", reused_from="valid")
        self.assertEqual(compute_readiness("F-02", "SUPPORTED", [req], [valid, reused], {}, "APPLICABLE").status, "READY")
        invalid = DocumentSubmission("invalid", req.document_id, "app", state="INVALID")
        bad_reuse = DocumentSubmission("bad-reuse", req.document_id, "app", state="REUSED_FROM", reused_from="invalid")
        self.assertEqual(compute_readiness("F-02", "SUPPORTED", [req], [invalid, bad_reuse], {}, "APPLICABLE").status, "INCOMPLETE")

    def test_workflow_aware_m4_consumes_immutable_m3_output(self):
        from backend.engine_adapter import get_persona
        facts = get_persona("persona_b")
        expected = build_workflow_for_facts(facts, as_of=None)["workflow"]
        result = requirements_for_application(facts, workflow_aware=True)
        self.assertEqual(result["workflow"], expected)
        self.assertIn("workflow", result)

    def test_workflow_aware_readiness_uses_committed_approval_scope(self):
        from backend.engine_adapter import get_persona
        facts = get_persona("persona_b")
        from backend.documents.service import readiness_for_application
        result = readiness_for_application("workflow-readiness", facts, workflow_aware=True, approval_ids=["F-02"])
        self.assertEqual(result["readiness"][0]["approval_id"], "F-02")
        self.assertNotEqual(result["readiness"][0]["reasons"], ["Approval is not in the committed M3 schedule scope."])


class TestM4Submissions(unittest.TestCase):
    def test_metadata_hash_duplicate_and_safe_name(self):
        store = SubmissionStore()
        item, duplicate = store.submit_bytes("app", "F02-FORM-B", "..\\..\\evil.pdf", b"%PDF synthetic", "application/pdf")
        self.assertFalse(duplicate)
        self.assertEqual(item.state, "PROVIDED_UNVALIDATED")
        self.assertEqual(item.filename, "evil.pdf")
        self.assertEqual(len(item.sha256), 64)
        second, duplicate = store.submit_bytes("app", "F02-FORM-B", "another.pdf", b"%PDF synthetic", "application/pdf")
        self.assertTrue(duplicate)
        self.assertEqual(second.submission_id, item.submission_id)
        self.assertEqual(safe_filename("C:/tmp/a b.pdf"), "a_b.pdf")

    def test_upload_limits_and_type(self):
        store = SubmissionStore()
        with self.assertRaises(ValueError):
            store.submit_bytes("app", "x", "x.exe", b"x", "application/octet-stream")
        with self.assertRaises(ValueError):
            store.submit_bytes("app", "x", "x.pdf", b"x" * (10 * 1024 * 1024 + 1), "application/pdf")


class TestM4API(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import socket
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        cls.base_url = f"http://127.0.0.1:{port}"
        cls.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()
        for _ in range(50):
            try:
                if requests.get(cls.base_url + "/api/health", timeout=0.5).status_code == 200:
                    return
            except requests.RequestException:
                time.sleep(0.05)
        raise RuntimeError("API did not start")

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True

    def test_requirements_and_unsupported_api(self):
        response = requests.get(self.base_url + "/api/documents/requirements")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["coverage"]), 16)
        unsupported = next(c for c in body["coverage"] if c["approval_id"] == "E-05")
        self.assertEqual(unsupported["status"], "UNSUPPORTED")
        evaluated = requests.post(self.base_url + "/api/documents/requirements", json={"facts": {}, "approval_ids": ["F-02"]})
        self.assertEqual(evaluated.status_code, 200)
        self.assertEqual(evaluated.json()["approvals"][0]["approval_id"], "F-02")

        workflow = requests.post(self.base_url + "/api/documents/requirements", json={"facts": {}, "approval_ids": ["F-02"], "workflow_aware": True})
        self.assertEqual(workflow.status_code, 200)
        self.assertIn("workflow", workflow.json())

    def test_submission_readiness_and_malformed_input(self):
        payload = {"application_id":"m4-api", "document_id":"F02-FOOD-CATEGORIES", "item_kind":"FORM_INPUT", "structured_data":{"pan":"ABCDE1234F"}}
        submitted = requests.post(self.base_url + "/api/documents/submit", json=payload)
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json()["state"], "PROVIDED_UNVALIDATED")
        facts = requests.get(self.base_url + "/api/personas/persona_b").json()
        readiness = requests.get(self.base_url + "/api/documents/readiness", params={"application_id":"m4-api", "facts":json.dumps(facts)})
        self.assertEqual(readiness.status_code, 200)
        self.assertIn("readiness", readiness.json())
        self.assertEqual(requests.post(self.base_url + "/api/documents/submit", json={"application_id":"x", "document_id":"x", "structured_data":[]}).status_code, 422)

        unknown = requests.post(self.base_url + "/api/documents/submit", json={"application_id":"x", "document_id":"UNKNOWN", "structured_data":{}})
        self.assertEqual(unknown.status_code, 422)
        wrong_kind = requests.post(self.base_url + "/api/documents/submit", json={"application_id":"x", "document_id":"F02-FORM-B", "item_kind":"FORM_INPUT", "structured_data":{}})
        self.assertEqual(wrong_kind.status_code, 422)
        unsupported = requests.post(self.base_url + "/api/documents/submit", json={"application_id":"x", "document_id":"S03-TECHNICAL-DOCUMENTS", "structured_data":{}})
        self.assertEqual(unsupported.status_code, 422)

        upload = requests.post(self.base_url + "/api/documents/submit", data={"application_id":"m4-upload", "document_id":"F02-FORM-B", "item_kind":"UPLOAD_DOCUMENT"}, files={"file":("..\\evil.pdf", b"%PDF synthetic", "application/pdf")})
        self.assertEqual(upload.status_code, 200)
        self.assertEqual(len(upload.json()["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
