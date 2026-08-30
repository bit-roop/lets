"""M5 applicability observation.

The rule these tests defend: M5 observes what M4 said and never recomputes it,
and an UNKNOWN condition stays unresolved rather than collapsing into
NOT_APPLICABLE. Those are different claims about the world -- "we do not know
whether this is required" is not "this is not required" -- and merging them
would quietly drop a requirement the applicant may well owe.
"""

import json
import unittest

from backend.tests import m5_support as support
from backend.verification import m4_context, states
from backend.verification.m4_context import M4Context

#: Conditional F-02 requirements. `manufacturing_processing` is absent from
#: every persona in the repository and is not collectable through the intake
#: wizard, so M4 reports UNKNOWN for these on every real run.
CONDITIONAL_DOCUMENT_IDS = ["F02-LAYOUT", "F02-WATER-ANALYSIS"]


class TestConditionUnknownPreserved(unittest.TestCase):

    def setUp(self):
        self.api = support.client(self)
        support.ensure_fixtures()
        support.isolated_store(self)

    def test_m4_actually_reports_unknown_for_these_requirements(self):
        """Guard the premise: if M4 ever resolves these, this suite must be revisited."""
        states_seen = {}
        for approval in support.m4_result(self.api, support.PERSONA_B)["approvals"]:
            for row in approval.get("requirements", []):
                if row["document_id"] in CONDITIONAL_DOCUMENT_IDS:
                    states_seen[row["document_id"]] = row.get("condition_state")
        self.assertEqual(set(states_seen), set(CONDITIONAL_DOCUMENT_IDS))
        for document_id, condition_state in states_seen.items():
            self.assertEqual(condition_state, "UNKNOWN", document_id)

    def test_unknown_becomes_indeterminate_not_not_applicable(self):
        context = M4Context(support.m4_result(self.api, support.PERSONA_B))
        for document_id in CONDITIONAL_DOCUMENT_IDS:
            observed, observations = context.observe_document(document_id)

            self.assertEqual(observed, states.UNRESOLVED_CONDITION_UNKNOWN, document_id)
            self.assertNotEqual(observed, states.NOT_APPLICABLE_CONDITION_FALSE)

            forced = m4_context.requirement_match_for(observed)
            self.assertEqual(forced, states.INDETERMINATE, document_id)
            self.assertNotEqual(forced, states.NOT_APPLICABLE,
                                "an unresolved condition was reported as inapplicable")

            # The observation is a verbatim copy of M4's own string.
            self.assertTrue(observations)
            for observation in observations:
                self.assertEqual(observation.condition_state, "UNKNOWN")

    def test_condition_false_is_not_applicable(self):
        facts = dict(support.PERSONA_B, manufacturing_processing=False)
        context = M4Context(support.m4_result(self.api, facts))
        observed, _ = context.observe_document("F02-LAYOUT")
        self.assertEqual(observed, states.NOT_APPLICABLE_CONDITION_FALSE)
        self.assertEqual(m4_context.requirement_match_for(observed),
                         states.NOT_APPLICABLE)

    def test_condition_true_is_analysable(self):
        facts = dict(support.PERSONA_B, manufacturing_processing=True)
        context = M4Context(support.m4_result(self.api, facts))
        observed, _ = context.observe_document("F02-LAYOUT")
        self.assertEqual(observed, states.APPLICABLE_CONDITION_TRUE)
        self.assertIsNone(m4_context.requirement_match_for(observed),
                          "an applicable requirement must be left to classification")
        self.assertIn(observed, states.ANALYSABLE_APPLICABILITY)

    def test_unresolved_never_enters_the_denominator_as_inapplicable(self):
        overlay = self.api.post("/api/verification/evidence", json={
            "application_id": "cond-app",
            "m4_result": support.m4_result(self.api, support.PERSONA_B),
            "m4_readiness": support.m4_readiness(
                self.api, "cond-app", support.PERSONA_B)}).json()
        counters = overlay["m5_evidence"]["counters"]

        self.assertGreater(counters["m5_applicability_unresolved_count"], 0)

        by_document = {e["document_id"]: e
                       for e in overlay["m5_evidence"]["per_requirement"]}
        for document_id in CONDITIONAL_DOCUMENT_IDS:
            entry = by_document[document_id]
            self.assertEqual(entry["m4_applicability_observed"],
                             states.UNRESOLVED_CONDITION_UNKNOWN)
            self.assertFalse(entry["in_m5_denominator"])


class TestUnresolvedRequirementIsNotAnalysed(unittest.TestCase):
    """A submission against an unresolved requirement is not judged."""

    def test_unresolved_submission_is_not_analysed_and_emits_no_blocking_finding(self):
        api = support.client(self)
        support.ensure_fixtures()
        support.isolated_store(self)

        # F02-LAYOUT has no profile, so exercise the gate through a profiled
        # document whose applicability we force to unresolved via absent facts.
        submission_id = support.submit_upload(
            api, "unres-app", "F02-FORM-B", "synthetic_form_b.pdf")

        # Empty facts leave the engine unable to resolve F-02 at all. That M4
        # result is established once, up front, and then observed.
        record = api.post("/api/verification/analyze", json={
            "submission_id": submission_id,
            "m4_result": support.m4_result(api, {})}).json()

        if record["m4_applicability_observed"] in (
                states.UNRESOLVED_CONDITION_UNKNOWN, states.UNRESOLVED_ENGINE_STATE):
            self.assertEqual(record["requirement_match"], states.INDETERMINATE)
            self.assertEqual(record["disposition"], states.NOT_ANALYZED)
            self.assertEqual(record["disposition_reason"], states.REASON_M4_UNRESOLVED)
            self.assertFalse(
                [f for f in record["findings"] if f["severity"] == states.BLOCKING],
                "an unresolved requirement produced a blocking finding")
        else:
            self.skipTest("F-02 resolved for empty facts; gate covered elsewhere")


if __name__ == "__main__":
    unittest.main()
