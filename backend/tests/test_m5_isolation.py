"""M5 isolation: the architectural claims, made mechanically testable.

The strongest property of this design is that M5 *cannot* change applicability,
workflow, or M4 requirements. Every test in this file exists to make that
property falsifiable rather than merely asserted in a document.
"""

import ast
import copy
import hashlib
import json
import unittest
from pathlib import Path

from backend.tests import m5_support as support

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROTECTED_TREES = [
    "engine-v3",
    "backend/workflow",
    "backend/documents",
    "regulatory-documents",
]

VERIFICATION_PKG = PROJECT_ROOT / "backend" / "verification"

#: The single module allowed to reach into M4. Everything else must go via it.
M4_ACCESS_CHOKE_POINT = "m4_gateway.py"


def _stable_json(value):
    """Remove only M4's volatile timestamp before comparing two responses."""
    if isinstance(value, dict):
        return {
            key: _stable_json(item)
            for key, item in value.items()
            if key != "derived_at"
        }
    if isinstance(value, list):
        return [_stable_json(item) for item in value]
    return value


def _tree_digest(relative: str) -> str:
    root = PROJECT_ROOT / relative
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if "__pycache__" in path.parts:
            continue
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


class TestProtectedTreesUnchanged(unittest.TestCase):
    """Tests 1-4: engine-v3, workflow, documents and regulatory data are inert.

    A full analyze run happens between the two digests, so anything M5 wrote to
    a protected path would show up here.
    """

    def test_protected_trees_unchanged_by_analysis(self):
        before = {tree: _tree_digest(tree) for tree in PROTECTED_TREES}

        api = support.client(self)
        support.ensure_fixtures()
        support.isolated_store(self)
        m4 = support.m4_result(api, support.PERSONA_B)
        submission_id = support.submit_upload(
            api, "iso-app", "S02-FORM-1", "synthetic_form_1.pdf")
        response = api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": m4})
        self.assertEqual(response.status_code, 200)

        after = {tree: _tree_digest(tree) for tree in PROTECTED_TREES}
        for tree in PROTECTED_TREES:
            self.assertEqual(before[tree], after[tree],
                             f"M5 modified the protected tree {tree}")


class TestNoForbiddenImports(unittest.TestCase):
    """Test 9: extracted information has no route back into engine-v3 or M3."""

    def _imports(self, path: Path):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)
        return names

    def test_m5_never_imports_engine_or_workflow(self):
        for path in VERIFICATION_PKG.rglob("*.py"):
            for name in self._imports(path):
                self.assertFalse(
                    name.startswith("engine") or name == "engine",
                    f"{path.name} imports {name}: M5 must not reach engine-v3")
                self.assertFalse(
                    name.startswith("backend.workflow"),
                    f"{path.name} imports {name}: M5 must not reach the M3 scheduler")

    def test_no_module_imports_m4_service(self):
        """The rule the original implementation broke.

        backend.documents.service re-runs the engine and re-evaluates every
        condition internally, so importing it at all puts M5 one call away from
        recomputing M4. The dynamic proof is in test_m5_engine_isolation.py;
        this keeps the door shut statically as well.
        """
        for path in VERIFICATION_PKG.rglob("*.py"):
            for name in self._imports(path):
                self.assertNotEqual(
                    name, "backend.documents.service",
                    f"{path.name} imports M4's service layer, which re-runs the "
                    f"engine internally. M5 must consume an established M4 result.")

    def test_only_the_gateway_touches_m4(self):
        for path in VERIFICATION_PKG.rglob("*.py"):
            if path.name == M4_ACCESS_CHOKE_POINT:
                continue
            for name in self._imports(path):
                if name.startswith("backend.documents"):
                    self.assertEqual(
                        path.name, M4_ACCESS_CHOKE_POINT,
                        f"{path.name} imports {name} directly; all M4 access must "
                        f"route through {M4_ACCESS_CHOKE_POINT} so the read-only "
                        f"property stays auditable")

    def test_m5_never_calls_engine_evaluation(self):
        """M5 must not evaluate applicability, conditions, or the rule set."""
        forbidden = ("evaluate_facts", "build_workflow_for_facts", "evaluate_condition")
        for path in VERIFICATION_PKG.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for name in forbidden:
                self.assertNotIn(
                    name + "(", source,
                    f"{path.name} calls {name}(): M5 observes applicability, "
                    f"it never computes it")


class TestM4OutputUnchanged(unittest.TestCase):
    """Tests 5, 6 and 10: M4's answers and objects survive M5 untouched."""

    def setUp(self):
        self.api = support.client(self)
        support.ensure_fixtures()
        support.isolated_store(self)
        self.facts = support.PERSONA_B
        self.application_id = "iso-m4"
        self.m4 = support.m4_result(self.api, self.facts)

    def _readiness(self):
        return support.m4_readiness(self.api, self.application_id, self.facts)

    def _requirements(self):
        return self.api.post("/api/documents/requirements",
                             json={"facts": self.facts}).json()

    def test_m4_readiness_and_requirements_unchanged(self):
        submission_id = support.submit_upload(
            self.api, self.application_id, "S02-FORM-1", "synthetic_form_1.pdf")

        readiness_before = _stable_json(self._readiness())
        requirements_before = _stable_json(self._requirements())

        self.api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": self.m4})

        self.assertEqual(readiness_before, _stable_json(self._readiness()),
                         "M5 changed the M4 readiness response")
        self.assertEqual(requirements_before,
                         _stable_json(self._requirements()),
                         "M5 changed the M4 requirements response")

    def test_submission_objects_unchanged(self):
        from backend.documents.submissions import get_submission_store

        submission_id = support.submit_upload(
            self.api, self.application_id, "S02-FORM-1", "synthetic_form_1.pdf")
        store = get_submission_store()
        before = copy.deepcopy(store.items[submission_id].__dict__)

        self.api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": self.m4})

        after = store.items[submission_id].__dict__
        self.assertEqual(sorted(before), sorted(after))
        for key in before:
            self.assertEqual(before[key], after[key],
                             f"M5 mutated DocumentSubmission.{key}")

    def test_m5_cannot_produce_valid_in_m4(self):
        from backend.documents.submissions import get_submission_store

        submission_id = support.submit_upload(
            self.api, self.application_id, "S02-FORM-1", "synthetic_form_1.pdf")
        self.api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": self.m4})

        for submission in get_submission_store().for_application(self.application_id):
            self.assertNotEqual(
                submission.state, "VALID",
                "M5 promoted an M4 submission to VALID; readiness must stay M4's")

    def test_readiness_never_becomes_ready_through_m5(self):
        submission_id = support.submit_upload(
            self.api, self.application_id, "S02-FORM-1", "synthetic_form_1.pdf")
        self.api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": self.m4})

        overlay = self.api.post("/api/verification/evidence", json={
            "application_id": self.application_id,
            "m4_result": self.m4,
            "m4_readiness": self._readiness()}).json()

        for approval in overlay["m4_readiness"]["readiness"]:
            self.assertNotEqual(
                approval.get("state"), "READY",
                "M5 evidence acceptance leaked into M4 readiness")


class TestOverlaySeparation(unittest.TestCase):
    """The overlay annotates M4; it never replaces or renames it."""

    def test_layers_are_separate_and_labelled(self):
        api = support.client(self)
        support.ensure_fixtures()
        support.isolated_store(self)
        m4 = support.m4_result(api, support.PERSONA_B)
        overlay = api.post("/api/verification/evidence", json={
            "application_id": "iso-sep",
            "m4_result": m4,
            "m4_readiness": support.m4_readiness(
                api, "iso-sep", support.PERSONA_B)}).json()

        self.assertIn("m4_readiness", overlay)
        self.assertIn("m5_evidence", overlay)
        self.assertNotIn("readiness", overlay,
                         "the overlay must not present an unqualified readiness key")

        note = overlay["m5_evidence"]["note"].lower()
        self.assertIn("does not mean the requirement is satisfied", note)
        self.assertIn("unchanged by m5", note)


class TestVerificationCors(unittest.TestCase):
    """M4/M3 behaviour is untouched; M5 responses are origin-restricted."""

    def setUp(self):
        self.api = support.client(self)
        self.hostile = "http://evil.example"
        self.allowed = "http://localhost:5173"

    def test_m4_endpoints_keep_existing_cors_behaviour(self):
        response = self.api.get("/api/health", headers={"origin": self.hostile})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"), self.hostile,
            "the existing global CORS behaviour on M4/M3 endpoints was altered")

    def test_m5_endpoint_strips_headers_for_unlisted_origin(self):
        response = self.api.get("/api/verification/capabilities",
                                headers={"origin": self.hostile})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.headers.get("access-control-allow-origin"),
                          "an unlisted origin was granted access to M5 content")
        self.assertIsNone(response.headers.get("access-control-allow-credentials"))

    def test_m5_endpoint_allows_configured_origin(self):
        response = self.api.get("/api/verification/capabilities",
                                headers={"origin": self.allowed})
        self.assertEqual(response.headers.get("access-control-allow-origin"),
                         self.allowed)
        self.assertIn("Origin", response.headers.get("vary", ""))


if __name__ == "__main__":
    unittest.main()
