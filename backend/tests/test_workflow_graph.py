import unittest

from backend import config as _engine_path
from backend.tests.fixtures.synthetic_graphs import (
    catalogue,
    dependency,
    engine_result,
    requirement,
)
from backend.workflow.graph import build_graph, find_cycles
from backend.workflow.models import (
    INCLUSION_EXCLUDED,
    INCLUSION_PROVISIONAL,
    INCLUSION_SCHEDULED,
)


class TestWorkflowGraph(unittest.TestCase):
    def test_node_admission_by_engine_state(self):
        a = requirement("A")
        unknown = requirement("U", "UNKNOWN", missing_facts=["x"])
        not_applicable = requirement("N", "NOT_APPLICABLE")
        conflict = requirement("C", "CONFLICT")
        graph = build_graph(
            engine_result(a, unknown, not_applicable, conflict),
            catalogue(a, unknown, not_applicable, conflict),
        )
        self.assertEqual(graph.nodes["A"].inclusion, INCLUSION_SCHEDULED)
        self.assertEqual(graph.nodes["U"].inclusion, INCLUSION_PROVISIONAL)
        self.assertNotIn("N", graph.nodes)
        self.assertEqual(graph.nodes["C"].inclusion, INCLUSION_EXCLUDED)

    def test_dependency_admission_and_candidate_rejection(self):
        a = requirement("A")
        b = requirement(
            "B",
            depends_on=[dependency("A", "LEGAL")],
            candidate_dependencies=[dependency("A", "LEGAL")],
        )
        graph = build_graph(engine_result(a, b), catalogue(a, b))
        self.assertEqual(len(graph.admitted_edges()), 1)
        self.assertEqual(sum(e.origin == "candidate_dependencies" for e in graph.edges), 1)
        candidate = next(e for e in graph.edges if e.origin == "candidate_dependencies")
        self.assertFalse(candidate.admitted)

    def test_conflict_and_not_applicable_prerequisites_are_dropped(self):
        conflict = requirement("C", "CONFLICT")
        not_applicable = requirement("N", "NOT_APPLICABLE")
        dependent = requirement(
            "D",
            depends_on=[
                dependency("C", "LEGAL"),
                dependency("N", "LEGAL"),
            ],
        )
        graph = build_graph(
            engine_result(conflict, not_applicable, dependent),
            catalogue(conflict, not_applicable, dependent),
        )
        self.assertEqual(graph.admitted_edges(), [])
        self.assertEqual(
            {edge.dropped_reason for edge in graph.edges},
            {"PREREQUISITE_IN_CONFLICT", "PREREQUISITE_NOT_APPLICABLE"},
        )

    def test_cycles_and_self_loops_are_detected(self):
        a = requirement("A", depends_on=[dependency("B")])
        b = requirement("B", depends_on=[dependency("A")])
        loop = requirement("L", depends_on=[dependency("L")])
        graph = build_graph(engine_result(a, b, loop), catalogue(a, b, loop))
        self.assertEqual(find_cycles(graph), [["A", "B"], ["L"]])

    def test_disconnected_graph_has_independent_components(self):
        a = requirement("A")
        b = requirement("B", depends_on=[dependency("A")])
        c = requirement("C")
        graph = build_graph(engine_result(a, b, c), catalogue(a, b, c))
        self.assertEqual(graph.predecessors(), {"A": [], "B": ["A"], "C": []})
        self.assertEqual(graph.successors(), {"A": ["B"], "B": [], "C": []})

    def test_graph_output_is_deterministic(self):
        a = requirement("A")
        b = requirement("B", depends_on=[dependency("A")])
        first = build_graph(engine_result(b, a), catalogue(b, a))
        second = build_graph(engine_result(a, b), catalogue(a, b))
        self.assertEqual(
            [edge.as_dict() for edge in first.edges],
            [edge.as_dict() for edge in second.edges],
        )


if __name__ == "__main__":
    unittest.main()
