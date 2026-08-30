"""
Regression: proves Milestone 3 did not change engine-v3.

Five layers:
  1. byte-equality of derive() output against pre-milestone baselines
  2. SHA-256 integrity of every protected engine-v3 file
  3. endpoint invariance (/api/evaluate unchanged)
  4. read-only enforcement
  5. Persona A/B/C workflow snapshots
"""

import copy
import hashlib
import json
import unittest
from datetime import date
from pathlib import Path

from backend.config import ENGINE_V3_DIR, PERSONAS_DIR, derive, get_registry
from backend.engine_adapter import build_workflow_for_facts, evaluate_facts
from backend.workflow import build_workflow

FIXTURES = Path(__file__).resolve().parent / "fixtures"
AS_OF = date(2026, 8, 29)
PERSONAS = ("a", "b", "c")


def _normalise(result):
    """derived_at is wall-clock; normalise for stable comparison."""
    r = copy.deepcopy(result)
    for df in r.get("derived_facts", {}).values():
        df["derived_at"] = "<NORMALISED>"
    return r


def _facts(letter):
    return json.loads((PERSONAS_DIR / f"persona_{letter}.json").read_text())


class TestEngineOutputUnchanged(unittest.TestCase):
    """Layer 1: byte-equality against baselines captured before Milestone 3."""

    def test_all_personas_match_baseline(self):
        registry = get_registry()
        for letter in PERSONAS:
            baseline_path = FIXTURES / f"engine_baseline_{letter}.json"
            self.assertTrue(baseline_path.exists(),
                            f"baseline for persona_{letter} missing")
            baseline = json.loads(baseline_path.read_text())
            current = _normalise(derive(_facts(letter), registry, AS_OF))
            self.assertEqual(
                json.loads(json.dumps(current, sort_keys=True)),
                json.loads(json.dumps(baseline, sort_keys=True)),
                f"engine output for persona_{letter} changed during Milestone 3")

    def test_summaries_unchanged(self):
        expected = {
            "a": {"applicable": 5, "not_applicable": 10, "unknown": 0, "conflict": 0},
            "b": {"applicable": 10, "not_applicable": 2, "unknown": 3, "conflict": 0},
            "c": {"applicable": 8, "not_applicable": 4, "unknown": 3, "conflict": 0},
        }
        registry = get_registry()
        for letter, exp in expected.items():
            summary = derive(_facts(letter), registry, AS_OF)["summary"]
            for k, v in exp.items():
                self.assertEqual(summary[k], v,
                                 f"persona_{letter}.{k} changed")


class TestEngineFileIntegrity(unittest.TestCase):
    """Layer 2: no protected file was created, modified or deleted."""

    def setUp(self):
        self.manifest = json.loads(
            (FIXTURES / "engine_v3_manifest.json").read_text())
        self.root = ENGINE_V3_DIR.parent

    def test_no_protected_file_modified(self):
        changed = []
        for rel, expected in self.manifest["files"].items():
            path = self.root / rel
            if not path.exists():
                changed.append(f"DELETED: {rel}")
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                changed.append(f"MODIFIED: {rel}")
        self.assertEqual(changed, [],
                         "protected engine-v3 files changed:\n  "
                         + "\n  ".join(changed))

    def test_no_protected_file_added(self):
        known = set(self.manifest["files"])
        added = []
        for d in self.manifest["protected_directories"]:
            for path in (self.root / d).rglob("*"):
                if path.is_file() and "__pycache__" not in str(path):
                    rel = str(path.relative_to(self.root)).replace("\\", "/")
                    if rel not in known:
                        added.append(rel)
        self.assertEqual(added, [],
                         f"files added under protected engine-v3 paths: {added}")

    def test_manifest_covers_all_protected_dirs(self):
        self.assertEqual(
            sorted(self.manifest["protected_directories"]),
            ["engine-v3/engine", "engine-v3/personas",
             "engine-v3/regulatory", "engine-v3/tests"])


class TestEndpointInvariance(unittest.TestCase):
    """Layer 3: /api/evaluate output is untouched by the workflow layer."""

    def test_evaluate_equals_direct_derive(self):
        registry = get_registry()
        for letter in PERSONAS:
            direct = derive(_facts(letter), registry, AS_OF)
            adapter = evaluate_facts(_facts(letter), AS_OF)
            self.assertEqual(_normalise(direct), _normalise(adapter))

    def test_evaluation_block_equals_evaluate(self):
        for letter in PERSONAS:
            plain = evaluate_facts(_facts(letter), AS_OF)
            combined = build_workflow_for_facts(_facts(letter), AS_OF)
            self.assertEqual(_normalise(plain),
                             _normalise(combined["evaluation"]),
                             "evaluate-with-workflow.evaluation diverged "
                             "from /api/evaluate")

    def test_workflow_does_not_alter_states(self):
        for letter in PERSONAS:
            combined = build_workflow_for_facts(_facts(letter), AS_OF)
            ev, wf = combined["evaluation"], combined["workflow"]
            engine_states = {}
            for bucket, state in (("applicable", "APPLICABLE"),
                                  ("unknown", "UNKNOWN"),
                                  ("not_applicable", "NOT_APPLICABLE"),
                                  ("conflict", "CONFLICT")):
                for r in ev[bucket]:
                    engine_states[r["requirement_id"]] = state
            for rid, node in wf["nodes"].items():
                self.assertEqual(node["state"], engine_states[rid],
                                 f"workflow altered state of {rid}")


class TestReadOnly(unittest.TestCase):
    """Layer 4: the workflow layer cannot reach back into engine output."""

    def test_input_not_mutated(self):
        registry = get_registry()
        result = derive(_facts("b"), registry, AS_OF)
        snapshot = copy.deepcopy(result)
        build_workflow(result, registry.catalogue, AS_OF)
        self.assertEqual(result, snapshot)

    def test_catalogue_not_mutated(self):
        registry = get_registry()
        snapshot = copy.deepcopy(registry.catalogue)
        result = derive(_facts("b"), registry, AS_OF)
        build_workflow(result, registry.catalogue, AS_OF)
        self.assertEqual(registry.catalogue, snapshot)


class TestPersonaWorkflowSnapshots(unittest.TestCase):
    """Layer 5: the figures reported in the design report, asserted."""

    def _wf(self, letter):
        return build_workflow_for_facts(_facts(letter), AS_OF)["workflow"]

    def test_persona_b_committed_schedule(self):
        s = self._wf("b")["schedule"]
        self.assertEqual(s["label"], "COMMITTED")
        self.assertEqual(len(s["nodes"]), 10)
        self.assertEqual(s["sequential_duration_days"], 189)
        self.assertEqual(s["parallel_duration_days"], 60)
        self.assertEqual(s["duration_completeness"], "COMPLETE")

    def test_persona_b_has_two_critical_paths(self):
        s = self._wf("b")["schedule"]
        self.assertEqual(s["critical_paths"], [["F-02"], ["S-01", "S-02"]])
        self.assertEqual(len(s["critical_paths"]), 2)

    def test_persona_b_confidence_is_medium(self):
        s = self._wf("b")["schedule"]
        self.assertEqual(s["schedule_confidence"], "medium")
        self.assertIn("SECONDARY", s["confidence_basis"])

    def test_persona_b_provisional_doubles_timeline(self):
        wf = self._wf("b")
        self.assertEqual(wf["provisional_schedule"]["parallel_duration_days"], 120)
        d = wf["provisional_delta"]
        self.assertEqual(d["critical_path_change_days"], 60)
        self.assertTrue(d["critical_path_changed"])
        self.assertIn("mpcb_category", d["unlocked_by_facts"])

    def test_persona_b_unknowns_never_in_committed(self):
        wf = self._wf("b")
        for rid in ("V-01", "V-02", "E-09"):
            self.assertNotIn(rid, wf["schedule"]["nodes"])
            self.assertIn(rid, wf["provisional_schedule"]["nodes"])

    def test_persona_b_sparse_data_warned(self):
        types = {w["type"] for w in self._wf("b")["warnings"]}
        self.assertIn("SPARSE_DEPENDENCY_DATA", types)

    def test_persona_b_candidate_edges_not_admitted(self):
        wf = self._wf("b")
        candidates = [e for e in wf["edges"]
                      if e["origin"] == "candidate_dependencies"]
        self.assertEqual(len(candidates), 2)
        for e in candidates:
            self.assertFalse(e["admitted"])

    def test_persona_b_zero_duration_node_present(self):
        s = self._wf("b")["schedule"]
        self.assertIn("S-14", s["nodes"])
        self.assertEqual(s["nodes"]["S-14"]["duration_days"], 0)

    def test_persona_a_schedules(self):
        s = self._wf("a")["schedule"]
        self.assertEqual(len(s["nodes"]), 5)
        self.assertIsNotNone(s["parallel_duration_days"])

    def test_persona_c_schedules(self):
        s = self._wf("c")["schedule"]
        self.assertEqual(len(s["nodes"]), 8)

    def test_all_personas_acyclic(self):
        for letter in PERSONAS:
            self.assertEqual(self._wf(letter)["cycles"], [])

    def test_all_personas_deterministic(self):
        for letter in PERSONAS:
            a = json.dumps(self._wf(letter), sort_keys=True)
            b = json.dumps(self._wf(letter), sort_keys=True)
            self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
