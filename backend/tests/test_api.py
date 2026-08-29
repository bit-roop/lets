import socket
import threading
import time
import unittest
import requests
import uvicorn

from backend.main import app


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestBackendAPI(unittest.TestCase):
    server = None
    server_thread = None
    base_url = None

    @classmethod
    def setUpClass(cls):
        port = get_free_port()
        cls.base_url = f"http://127.0.0.1:{port}"
        
        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=port,
            log_level="error",
        )
        cls.server = uvicorn.Server(config)
        cls.server_thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.server_thread.start()

        # Wait for server to start
        for _ in range(50):
            try:
                resp = requests.get(f"{cls.base_url}/api/health", timeout=0.5)
                if resp.status_code == 200:
                    break
            except Exception:
                time.sleep(0.05)
        else:
            raise RuntimeError(f"Server did not start on {cls.base_url}")

    @classmethod
    def tearDownClass(cls):
        if cls.server:
            cls.server.should_exit = True

    def test_01_health_endpoint(self):
        resp = requests.get(f"{self.base_url}/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["engine_version"], "3.0.0")
        self.assertEqual(data["requirements_count"], 16)
        self.assertEqual(data["rules_count"], 18)
        self.assertEqual(data["sources_count"], 11)
        self.assertEqual(data["verification_summary"].get("VERIFIED"), 9)
        self.assertEqual(data["verification_summary"].get("SECONDARY"), 6)
        self.assertEqual(data["verification_summary"].get("UNVERIFIED"), 3)

    def test_02_catalogue_endpoint(self):
        resp = requests.get(f"{self.base_url}/api/catalogue")
        self.assertEqual(resp.status_code, 200)
        catalogue = resp.json()
        self.assertEqual(len(catalogue), 16)
        self.assertIn("S-01", catalogue)
        self.assertIn("S-02", catalogue)
        self.assertIn("F-02", catalogue)
        self.assertIn("E-05", catalogue)
        self.assertEqual(catalogue["S-02"]["requirement_type"], "LICENCE")

    def test_03_sources_endpoint(self):
        resp = requests.get(f"{self.base_url}/api/sources")
        self.assertEqual(resp.status_code, 200)
        sources = resp.json()
        self.assertEqual(len(sources), 11)
        self.assertIn("SRC-DISH-001", sources)
        self.assertIn("SRC-FSSAI-001", sources)
        self.assertEqual(sources["SRC-FSSAI-001"]["verification_status"], "VERIFIED")

    def test_04_personas_list_and_detail(self):
        resp = requests.get(f"{self.base_url}/api/personas")
        self.assertEqual(resp.status_code, 200)
        personas = resp.json()
        ids = [p["id"] for p in personas]
        self.assertIn("persona_a", ids)
        self.assertIn("persona_b", ids)
        self.assertIn("persona_c", ids)

        # Get Persona B detail
        resp_b = requests.get(f"{self.base_url}/api/personas/persona_b")
        self.assertEqual(resp_b.status_code, 200)
        data_b = resp_b.json()
        self.assertEqual(data_b["annual_turnover"], 80000000)
        self.assertEqual(data_b["entity_type"], "private_limited")

        # 404 for non-existent persona
        resp_404 = requests.get(f"{self.base_url}/api/personas/non_existent_persona")
        self.assertEqual(resp_404.status_code, 404)

    def test_05_evaluate_persona_b(self):
        # Fetch persona B facts
        resp_b = requests.get(f"{self.base_url}/api/personas/persona_b")
        facts = resp_b.json()

        resp = requests.post(
            f"{self.base_url}/api/evaluate",
            json={"facts": facts, "as_of": "2026-08-29"},
        )
        self.assertEqual(resp.status_code, 200)
        res = resp.json()

        # Check summary counts match baseline
        summary = res["summary"]
        self.assertEqual(summary["applicable"], 10)
        self.assertEqual(summary["not_applicable"], 2)
        self.assertEqual(summary["unknown"], 3)
        self.assertEqual(summary["conflict"], 0)
        self.assertEqual(summary["derived_facts"], 1)
        self.assertEqual(summary["derivation_passes"], 2)

        # Check derived fact
        self.assertIn("msme_eligible", res["derived_facts"])
        self.assertTrue(res["derived_facts"]["msme_eligible"]["value"])
        self.assertEqual(res["derived_facts"]["msme_eligible"]["verification_status"], "VERIFIED")

        # Check applicable items
        app_ids = [r["requirement_id"] for r in res["applicable"]]
        expected_applicable = ["E-05", "E-08", "F-02", "F-09", "S-01", "S-02", "S-03", "S-04", "S-10", "S-14"]
        for expected in expected_applicable:
            self.assertIn(expected, app_ids)

        # Check FSSAI State Licence evidence & source
        f02 = next(r for r in res["applicable"] if r["requirement_id"] == "F-02")
        self.assertEqual(f02["state"], "APPLICABLE")
        self.assertEqual(f02["confidence"], "high")
        self.assertTrue(len(f02["evidence"]) > 0)
        ev = f02["evidence"][0]
        self.assertEqual(ev["rule_id"], "FSSAI-CAT-STATE")
        self.assertEqual(ev["verification_status"], "VERIFIED")
        self.assertIn("source_detail", ev)

        # Check FoSTaC Quantity
        f09 = next(r for r in res["applicable"] if r["requirement_id"] == "F-09")
        self.assertEqual(f09["quantity"]["value"], 2)

        # Check not applicable items (active exclusions)
        not_app_ids = [r["requirement_id"] for r in res["not_applicable"]]
        self.assertIn("F-01", not_app_ids)
        self.assertIn("F-03", not_app_ids)

        # Check unknown items
        unk_ids = [r["requirement_id"] for r in res["unknown"]]
        self.assertIn("E-09", unk_ids)
        self.assertIn("V-01", unk_ids)
        self.assertIn("V-02", unk_ids)

    def test_06_missing_facts_remain_unknown(self):
        # Only supply minimal facts; everything else missing
        sparse_facts = {
            "is_food_business": True,
            # annual_turnover missing
        }
        resp = requests.post(
            f"{self.base_url}/api/evaluate",
            json={"facts": sparse_facts, "as_of": "2026-08-29"},
        )
        self.assertEqual(resp.status_code, 200)
        res = resp.json()

        # FSSAI requirements must be UNKNOWN, not FALSE or NOT_APPLICABLE
        unk_ids = [r["requirement_id"] for r in res["unknown"]]
        self.assertIn("F-01", unk_ids)
        self.assertIn("F-02", unk_ids)

        # Indeterminate derivation for msme_eligible must be recorded
        ind_facts = [i["fact"] for i in res["indeterminate_derivations"]]
        self.assertIn("msme_eligible", ind_facts)

    def test_07_invalid_payload_error(self):
        # Missing 'facts' field
        resp = requests.post(f"{self.base_url}/api/evaluate", json={"as_of": "2026-08-29"})
        self.assertEqual(resp.status_code, 422)

        # 'facts' not an object
        resp2 = requests.post(f"{self.base_url}/api/evaluate", json={"facts": "not-a-dict"})
        self.assertEqual(resp2.status_code, 422)

        # Invalid date format
        resp3 = requests.post(f"{self.base_url}/api/evaluate", json={"facts": {}, "as_of": "bad-date"})
        self.assertEqual(resp3.status_code, 422)


if __name__ == "__main__":
    unittest.main()
