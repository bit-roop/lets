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


if __name__ == "__main__":
    unittest.main()
