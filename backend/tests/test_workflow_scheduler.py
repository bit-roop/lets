import unittest

from backend import config as _engine_path
from backend.tests.fixtures.synthetic_graphs import (
    catalogue,
    dependency,
    engine_result,
    requirement,
)
from backend.workflow.errors import CyclicGraphError
from backend.workflow.graph import build_graph
from backend.workflow.models import classify_sla
from backend.workflow.scheduler import compute_schedule, topological_order


def schedule(*requirements):
    graph = build_graph(engine_result(*requirements), catalogue(*requirements))
    return graph, compute_schedule(graph, {"SCHEDULED"}, "COMMITTED")[0]


class TestWorkflowScheduler(unittest.TestCase):
    def test_topological_order_is_sorted_and_cycle_safe(self):
        a = requirement("A")
        b = requirement("B", depends_on=[dependency("A")])
        graph, result = schedule(a, b)
        self.assertEqual(result.topological_order, ["A", "B"])
        with self.assertRaises(CyclicGraphError):
            topological_order({"A", "B"}, {"A": ["B"], "B": ["A"]}, {"A": ["B"], "B": ["A"]})

    def test_earliest_finish_parallel_and_sequential_duration(self):
        a = requirement("A", sla_days=2)
        b = requirement("B", sla_days=3, depends_on=[dependency("A")])
        c = requirement("C", sla_days=5)
        _, result = schedule(a, b, c)
        self.assertEqual(result.sequential_duration_days, 10)
        self.assertEqual(result.parallel_duration_days, 5)
        self.assertEqual(result.nodes["A"].earliest_start_day, 0)
        self.assertEqual(result.nodes["A"].earliest_finish_day, 2)
        self.assertEqual(result.nodes["B"].earliest_start_day, 2)
        self.assertEqual(result.nodes["B"].earliest_finish_day, 5)

    def test_multiple_critical_paths_and_slack(self):
        root = requirement("A", sla_days=2)
        left = requirement("B", sla_days=3, depends_on=[dependency("A")])
        right = requirement("C", sla_days=3, depends_on=[dependency("A")])
        tail = requirement(
            "D",
            sla_days=1,
            depends_on=[dependency("B"), dependency("C")],
        )
        independent = requirement("E", sla_days=1)
        _, result = schedule(root, left, right, tail, independent)
        self.assertEqual(result.critical_paths, [["A", "B", "D"], ["A", "C", "D"]])
        self.assertEqual(result.critical_path_duration_days, 6)
        self.assertEqual(result.nodes["A"].slack_days, 0)
        self.assertEqual(result.nodes["E"].slack_days, 5)
        self.assertEqual(result.nodes["A"].blocks, ["B", "C"])
        self.assertEqual(result.nodes["A"].blocks_transitively, ["B", "C", "D"])
        self.assertEqual(result.nodes["D"].blocked_by, ["B", "C"])

    def test_zero_null_and_invalid_slas_are_explicit(self):
        self.assertEqual(classify_sla(0).duration, 0)
        self.assertEqual(classify_sla(None).kind, "UNSPECIFIED")
        self.assertEqual(classify_sla(-1).kind, "INVALID")
        self.assertEqual(classify_sla("5").kind, "INVALID")
        zero = requirement("A", sla_days=0)
        missing = requirement("B", sla_days=None)
        invalid = requirement("C", sla_days=-1)
        _, result = schedule(zero, missing, invalid)
        self.assertEqual(result.nodes["A"].duration_days, 0)
        self.assertEqual(result.duration_completeness, "PARTIAL")
        self.assertEqual(result.excluded_from_duration, ["B", "C"])
        self.assertIsNone(result.nodes["B"].slack_days)

    def test_unknown_is_only_in_provisional_scope(self):
        known = requirement("A", sla_days=2)
        unknown = requirement("U", "UNKNOWN", sla_days=4, missing_facts=["x"])
        graph = build_graph(engine_result(known, unknown), catalogue(known, unknown))
        committed, _ = compute_schedule(graph, {"SCHEDULED"}, "COMMITTED")
        provisional, _ = compute_schedule(
            graph, {"SCHEDULED", "PROVISIONAL"}, "PROVISIONAL"
        )
        self.assertEqual(set(committed.nodes), {"A"})
        self.assertEqual(set(provisional.nodes), {"A", "U"})


if __name__ == "__main__":
    unittest.main()
