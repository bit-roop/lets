import unittest

import requests

from test_api import TestBackendAPI


class TestWorkflowAPI(TestBackendAPI):
    @classmethod
    def setUpClass(cls):
        TestBackendAPI.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        TestBackendAPI.tearDownClass.__func__(cls)

    @property
    def url(self):
        return self.base_url

    def payload(self):
        facts = requests.get(f"{self.url}/api/personas/persona_b").json()
        return {"facts": facts, "as_of": "2026-08-29"}

    def test_workflow_endpoint(self):
        response = requests.post(f"{self.url}/api/workflow", json=self.payload())
        self.assertEqual(response.status_code, 200)
        workflow = response.json()
        self.assertEqual(len(workflow["schedule"]["nodes"]), 10)
        self.assertEqual(len(workflow["provisional_schedule"]["nodes"]), 13)
        self.assertEqual(len(workflow["schedule"]["critical_paths"]), 2)
        scheduled_ids = {node["requirement_id"] for node in workflow["schedule"]["nodes"].values()}
        self.assertNotIn("E-09", scheduled_ids)
        self.assertNotIn("V-01", scheduled_ids)
        self.assertNotIn("V-02", scheduled_ids)

    def test_evaluate_with_workflow_preserves_evaluation(self):
        payload = self.payload()
        evaluation = requests.post(f"{self.url}/api/evaluate", json=payload).json()
        combined = requests.post(f"{self.url}/api/evaluate-with-workflow", json=payload)
        self.assertEqual(combined.status_code, 200)
        actual = combined.json()["evaluation"]
        for item in (evaluation, actual):
            for fact in item.get("derived_facts", {}).values():
                fact["derived_at"] = "<NORMALISED>"
        self.assertEqual(actual, evaluation)

    def test_workflow_without_provisional(self):
        payload = self.payload()
        payload["include_provisional"] = False
        response = requests.post(f"{self.url}/api/workflow", json=payload)
        self.assertEqual(response.status_code, 200)
        workflow = response.json()
        self.assertIsNone(workflow["provisional_schedule"])
        self.assertIsNone(workflow["provisional_delta"])

    def test_workflow_malformed_requests(self):
        for endpoint in ("/api/workflow", "/api/evaluate-with-workflow"):
            self.assertEqual(requests.post(f"{self.url}{endpoint}", json={}).status_code, 422)
            self.assertEqual(requests.post(f"{self.url}{endpoint}", json={"facts": "bad"}).status_code, 422)
            self.assertEqual(
                requests.post(f"{self.url}{endpoint}", json={"facts": {}, "as_of": "bad-date"}).status_code,
                422,
            )


if __name__ == "__main__":
    unittest.main()
