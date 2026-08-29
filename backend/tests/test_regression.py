import json
from datetime import date
from pathlib import Path
import unittest

from backend.config import ENGINE_V3_DIR, PERSONAS_DIR, derive, get_registry
from backend.engine_adapter import evaluate_facts


class TestDeterministicRegression(unittest.TestCase):
    def setUp(self):
        self.registry = get_registry()
        self.sample_resp_b_path = ENGINE_V3_DIR / "docs" / "sample_response_persona_b.json"

    def test_persona_b_direct_vs_adapter(self):
        """Proves adapter produces identical output to direct engine-v3 derive() call."""
        facts_b = json.loads((PERSONAS_DIR / "persona_b.json").read_text(encoding="utf-8"))
        as_of = date(2026, 8, 29)

        direct_result = derive(facts=facts_b, registry=self.registry, as_of=as_of)
        adapter_result = evaluate_facts(facts=facts_b, as_of=as_of)

        self.assertEqual(direct_result, adapter_result)

    def test_persona_a_direct_vs_adapter(self):
        """Proves adapter matches direct engine for Persona A."""
        facts_a = json.loads((PERSONAS_DIR / "persona_a.json").read_text(encoding="utf-8"))
        as_of = date(2026, 8, 29)

        direct_result = derive(facts=facts_a, registry=self.registry, as_of=as_of)
        adapter_result = evaluate_facts(facts=facts_a, as_of=as_of)

        self.assertEqual(direct_result, adapter_result)

    def test_persona_c_direct_vs_adapter(self):
        """Proves adapter matches direct engine for Persona C (edge case)."""
        facts_c = json.loads((PERSONAS_DIR / "persona_c.json").read_text(encoding="utf-8"))
        as_of = date(2026, 8, 29)

        direct_result = derive(facts=facts_c, registry=self.registry, as_of=as_of)
        adapter_result = evaluate_facts(facts=facts_c, as_of=as_of)

        self.assertEqual(direct_result, adapter_result)

    def test_persona_b_matches_canonical_sample_json(self):
        """Verifies Persona B output matches docs/sample_response_persona_b.json summary and structure."""
        if not self.sample_resp_b_path.exists():
            self.skipTest("sample_response_persona_b.json not found")

        canonical_data = json.loads(self.sample_resp_b_path.read_text(encoding="utf-8"))
        facts_b = json.loads((PERSONAS_DIR / "persona_b.json").read_text(encoding="utf-8"))
        as_of = date(2026, 8, 29)

        result = evaluate_facts(facts=facts_b, as_of=as_of)

        # Compare summary block
        self.assertEqual(result["summary"], canonical_data["summary"])

        # Compare counts across all buckets
        self.assertEqual(len(result["applicable"]), len(canonical_data["applicable"]))
        self.assertEqual(len(result["not_applicable"]), len(canonical_data["not_applicable"]))
        self.assertEqual(len(result["unknown"]), len(canonical_data["unknown"]))
        self.assertEqual(len(result["conflict"]), len(canonical_data["conflict"]))

        # Compare derived facts keys
        self.assertEqual(set(result["derived_facts"].keys()), set(canonical_data["derived_facts"].keys()))


if __name__ == "__main__":
    unittest.main()
