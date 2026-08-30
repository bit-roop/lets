"""Dynamic proof that M5 cannot re-evaluate M4.

A static import or grep test is not sufficient and was the reason the original
implementation shipped a real violation: M5 did not name ``evaluate_facts``
anywhere in its own source, but it called
``backend.documents.service.requirements_for_application``, which calls it
internally. The grep passed. The boundary was broken.

The test here sabotages every engine and condition entry point at every binding
site, then runs the whole M5 pipeline. If any code path reaches the engine, the
sabotage raises and the test fails. M5 must still produce a correct result from
the M4 observation it was handed.
"""

import json
import unittest
from unittest import mock

from backend.tests import m5_support as support
from backend.verification import states


class EngineWasInvoked(AssertionError):
    """Raised by the sabotage. Reaching it means the boundary was crossed."""


def _sabotage(*_args, **_kwargs):
    raise EngineWasInvoked(
        "M5 reached an engine or condition evaluation entry point. M5 must "
        "observe the M4 result it was given, never compute a new one.")


#: Every binding site through which engine evaluation, workflow construction or
#: condition evaluation can be reached. Module-level `from X import y` bindings
#: mean patching the definition alone is not enough, so each importer is patched
#: at its own name.
ENGINE_ENTRY_POINTS = (
    # Deepest: the engine itself.
    "backend.config.derive",
    "engine.evaluator.evaluate",
    # The adapter and its bound names.
    "backend.engine_adapter.derive",
    "backend.engine_adapter.build_workflow",
    "backend.engine_adapter.evaluate_facts",
    "backend.engine_adapter.build_workflow_for_facts",
    # M4's condition adapter and its bound engine function.
    "backend.documents.conditions.evaluate",
    "backend.documents.conditions.evaluate_condition",
    # M4's service layer: the route the original violation actually took.
    "backend.documents.service.evaluate_facts",
    "backend.documents.service.build_workflow_for_facts",
    "backend.documents.service.evaluate_condition",
    "backend.documents.service.requirements_for_application",
    "backend.documents.service.readiness_for_application",
)


def sabotage_engine():
    """Context manager making every engine entry point fail loudly."""
    return _MultiPatch(ENGINE_ENTRY_POINTS)


class _MultiPatch:
    def __init__(self, targets):
        self.targets = targets
        self.patchers = []

    def __enter__(self):
        for target in self.targets:
            patcher = mock.patch(target, side_effect=_sabotage)
            patcher.start()
            self.patchers.append(patcher)
        return self

    def __exit__(self, *exc):
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.patchers = []
        return False


class TestSabotageItselfWorks(unittest.TestCase):
    """A negative control.

    If the sabotage did not actually intercept M4, every other test in this
    file would pass vacuously. So first prove that M4 *does* trip it.
    """

    def test_m4_requirements_trips_the_sabotage(self):
        api = support.client(self)
        with sabotage_engine():
            with self.assertRaises(EngineWasInvoked):
                from backend.documents import service as m4_service
                m4_service.requirements_for_application(facts=support.PERSONA_B)

    def test_m4_endpoint_trips_the_sabotage(self):
        api = support.client(self)
        with sabotage_engine():
            with self.assertRaises(EngineWasInvoked):
                api.post("/api/documents/requirements", json={"facts": support.PERSONA_B})


class TestM5DoesNotReEvaluateM4(unittest.TestCase):
    """The main proof: freeze M4, sabotage the engine, run M5, get a result."""

    def setUp(self):
        self.api = support.client(self)
        support.ensure_fixtures()
        support.isolated_store(self)
        self.application_id = "dyn-app"

        # Step 1: establish the M4 result normally, before any sabotage.
        self.m4_result = support.m4_result(self.api, support.PERSONA_B)
        self.m4_readiness = support.m4_readiness(
            self.api, self.application_id, support.PERSONA_B)

        # Step 2: upload through M4's real endpoint, also before sabotage.
        self.submission_id = support.submit_upload(
            self.api, self.application_id, "S02-FORM-1", "synthetic_form_1.pdf")

    def test_analyze_runs_with_every_engine_entry_point_sabotaged(self):
        with sabotage_engine():
            response = self.api.post("/api/verification/analyze", json={
                "submission_id": self.submission_id,
                "m4_result": self.m4_result,
            })

        self.assertEqual(response.status_code, 200, response.text)
        record = response.json()

        # M5 still did its job using the observation it was handed.
        self.assertEqual(record["m4_applicability_observed"],
                         states.APPLICABLE_CONDITION_TRUE)
        self.assertEqual(record["requirement_match"], states.MATCH)
        self.assertEqual(record["classification"], states.MATCHES_EXPECTED)
        self.assertEqual(record["disposition"], states.ACCEPTED_FOR_REVIEW)

    def test_analyze_of_a_wrong_document_runs_sabotaged(self):
        wrong = support.submit_upload(
            self.api, self.application_id, "F02-FORM-B", "synthetic_form_1.pdf")
        with sabotage_engine():
            record = self.api.post("/api/verification/analyze", json={
                "submission_id": wrong, "m4_result": self.m4_result}).json()
        self.assertEqual(record["requirement_match"], states.MISMATCH)
        self.assertEqual(record["disposition"], states.NEEDS_APPLICANT_ACTION)

    def test_evidence_overlay_runs_with_the_engine_sabotaged(self):
        with sabotage_engine():
            self.api.post("/api/verification/analyze", json={
                "submission_id": self.submission_id, "m4_result": self.m4_result})
            response = self.api.post("/api/verification/evidence", json={
                "application_id": self.application_id,
                "m4_result": self.m4_result,
                "m4_readiness": self.m4_readiness,
            })

        self.assertEqual(response.status_code, 200, response.text)
        overlay = response.json()
        self.assertEqual(overlay["m5_evidence"]["counters"]["m5_analyzed_count"], 1)

    def test_readiness_is_echoed_verbatim_not_recomputed(self):
        """M5 cannot alter M4 readiness because M5 never produces one."""
        with sabotage_engine():
            overlay = self.api.post("/api/verification/evidence", json={
                "application_id": self.application_id,
                "m4_result": self.m4_result,
                "m4_readiness": self.m4_readiness,
            }).json()

        self.assertEqual(
            json.dumps(overlay["m4_readiness"], sort_keys=True),
            json.dumps(self.m4_readiness, sort_keys=True),
            "M5 altered the M4 readiness it was given")

    def test_records_endpoint_runs_sabotaged(self):
        with sabotage_engine():
            self.api.post("/api/verification/analyze", json={
                "submission_id": self.submission_id, "m4_result": self.m4_result})
            response = self.api.get("/api/verification/records", params={
                "application_id": self.application_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["records"]), 1)

    def test_capabilities_endpoint_runs_sabotaged(self):
        with sabotage_engine():
            response = self.api.get("/api/verification/capabilities")
        self.assertEqual(response.status_code, 200)


class TestM5ConsumesRatherThanDerives(unittest.TestCase):
    """M5 reads condition_state; it never looks at the condition itself."""

    def setUp(self):
        self.api = support.client(self)
        support.ensure_fixtures()
        support.isolated_store(self)

    def test_m5_honours_a_supplied_condition_state_it_could_not_have_derived(self):
        """Hand M5 an M4 result whose condition_state contradicts the facts.

        If M5 were re-deriving applicability it would compute UNKNOWN for
        F02-LAYOUT (the fact is absent from every persona) and disagree with the
        payload. Reading the supplied state is the whole contract, so M5 must
        report exactly what it was given.
        """
        m4_result = support.m4_result(self.api, support.PERSONA_B)

        # Flip the stored condition_state without touching the condition.
        flipped = 0
        for approval in m4_result["approvals"]:
            for row in approval["requirements"]:
                if row["document_id"] == "F02-LAYOUT":
                    self.assertEqual(row["condition_state"], "UNKNOWN")
                    row["condition_state"] = "FALSE"
                    flipped += 1
        self.assertTrue(flipped, "expected a conditional F02-LAYOUT row")

        from backend.verification.m4_context import M4Context
        observed, _ = M4Context(m4_result).observe_document("F02-LAYOUT")

        # It followed the payload, not the facts.
        self.assertEqual(observed, states.NOT_APPLICABLE_CONDITION_FALSE)

    def test_a_malformed_m4_result_is_rejected_rather_than_recomputed(self):
        """With no usable M4 result, M5 refuses. It does not fall back to
        deriving one, because there is no code path that could."""
        support.ensure_fixtures()
        submission_id = support.submit_upload(
            self.api, "bad-ctx", "S02-FORM-1", "synthetic_form_1.pdf")
        response = self.api.post("/api/verification/analyze", json={
            "submission_id": submission_id, "m4_result": {"approvals": []}})
        self.assertEqual(response.status_code, 400)
        self.assertIn("nothing to observe", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
