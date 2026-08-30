import unittest

from backend.config import ENGINE_V3_DIR
from engine.validate_data import CRITICAL_PATH_TYPES
from backend.workflow import policy


class TestEngineAlignment(unittest.TestCase):
    def test_scheduling_policy_matches_engine_constant(self):
        self.assertEqual(policy.SCHEDULING_ADMITTED, frozenset(CRITICAL_PATH_TYPES))
        self.assertEqual(policy.SCHEDULING_ADMITTED, frozenset({"LEGAL", "OPERATIONAL"}))

    def test_candidate_edges_are_never_admitted(self):
        self.assertFalse(policy.is_admitted("LEGAL", policy.ORIGIN_CANDIDATE))

    def test_operational_edges_are_admitted(self):
        self.assertTrue(policy.is_admitted("OPERATIONAL", policy.ORIGIN_DEPENDS_ON))

    def test_non_scheduling_edges_are_rejected(self):
        for dependency_type in ("PROCESS", "RECOMMENDED", "UNVERIFIED"):
            self.assertFalse(policy.is_admitted(dependency_type, policy.ORIGIN_DEPENDS_ON))

    def test_unknown_dependency_type_is_rejected(self):
        self.assertFalse(policy.is_admitted("INVENTED", policy.ORIGIN_DEPENDS_ON))

    def test_confidence_uses_weakest_admitted_edge(self):
        from backend.tests.fixtures.synthetic_graphs import dependency, engine_result, requirement, catalogue
        from backend.workflow.graph import build_graph

        a = requirement("A")
        b = requirement("B", depends_on=[dependency("A", verification_status="SECONDARY")])
        graph = build_graph(engine_result(a, b), catalogue(a, b))
        level, _ = policy.schedule_confidence(graph.admitted_edges())
        self.assertEqual(level, "medium")

    def test_no_edges_are_not_applicable_confidence(self):
        self.assertEqual(policy.schedule_confidence([])[0], "not_applicable")


if __name__ == "__main__":
    unittest.main()
