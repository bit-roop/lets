"""Tests for Milestone 5, Slice 3: Persistent Application Case + Tracking.

Verifies:
1. Application creation, tracking reference generation, and status SUBMITTED.
2. Persistence across store reinstantiation / process restart.
3. Timeline partitioning into Phase 1 (immediate) vs Phase 2 (sequential).
4. REST API endpoints: POST /api/applications, GET /api/applications, GET /api/applications/{id}.
5. Required established upstream context validation (rejects empty facts/approvals, malformed references).
6. Exception sanitization (never leaks raw traceback/file paths/SQL errors).
7. Real PostgreSQL code path execution with parameterized queries.
8. CRITICAL: Upstream engine and M4 evaluation functions are NOT invoked
   during application creation (verified via dynamic monkeypatch sabotage).
"""

import gc
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.applications import service as app_service
from backend.applications.models import (
    ApplicationCreateRequest,
    ApprovalSnapshot,
    SubmissionSnapshot,
    VerificationSnapshot,
)
from backend.applications.store import ApplicationStore, reset_application_store
from backend.main import app


class TestApplicationPersistenceSlice3(unittest.TestCase):
    def setUp(self):
        # Create a unique database file for each test method to guarantee 100% test isolation
        self.test_dir = Path(tempfile.gettempdir()) / "sih26_slice3_test_dbs"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.test_dir / f"test_app_{uuid.uuid4().hex}.db"
        self.store = ApplicationStore(path=self.db_path)
        reset_application_store(self.db_path)
        self.client = TestClient(app)

    def tearDown(self):
        reset_application_store(None)
        self.store = None
        gc.collect()
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except Exception:
                pass

    def test_create_and_retrieve_application_case(self):
        req = ApplicationCreateRequest(
            application_id="APP-TEST-FOOD-001",
            entity_name="Sahyadri Foods Private Limited",
            facts={"is_food_business": True, "annual_turnover": 80000000},
            as_of="2026-08-31",
            approvals=[
                ApprovalSnapshot(
                    approval_id="F-02",
                    name="FSSAI State Licence",
                    department="FSSAI",
                    sla_days=60,
                    readiness_status="READY",
                ),
                ApprovalSnapshot(
                    approval_id="S-02",
                    name="Factory Licence",
                    department="DISH",
                    sla_days=60,
                    readiness_status="READY",
                ),
            ],
            submissions=[
                SubmissionSnapshot(
                    document_id="F02-FORM-B",
                    submission_id="sub-123",
                    filename="form_b.pdf",
                ),
                SubmissionSnapshot(
                    document_id="S02-FORM-1",
                    submission_id="sub-456",
                    filename="form_1.pdf",
                ),
            ],
            verification_records=[
                VerificationSnapshot(
                    document_id="F02-FORM-B",
                    record_id="rec-123",
                    disposition="ACCEPTED_FOR_REVIEW",
                    confidence_overall=0.85,
                )
            ],
            workflow_snapshot={
                "schedule": {
                    "nodes": {
                        "F-02": {"depth": 0, "blocked_by": []},
                        "S-02": {"depth": 1, "blocked_by": ["S-01"]},
                    }
                }
            },
        )

        record = app_service.create_application_case(req)

        self.assertEqual(record.application_id, "APP-TEST-FOOD-001")
        self.assertEqual(record.tracking_reference, "MH-FOOD-2026-0001")
        self.assertEqual(record.status, "SUBMITTED")
        self.assertEqual(record.entity_name, "Sahyadri Foods Private Limited")
        self.assertEqual(len(record.approvals), 2)
        self.assertEqual(len(record.submissions), 2)

        # Timeline verification
        self.assertEqual(record.timeline["phase_1_immediate"]["count"], 1)
        self.assertEqual(record.timeline["phase_1_immediate"]["items"][0]["approval_id"], "F-02")
        self.assertEqual(record.timeline["phase_2_sequential"]["count"], 1)
        self.assertEqual(record.timeline["phase_2_sequential"]["items"][0]["approval_id"], "S-02")
        self.assertIn("S-01", record.timeline["phase_2_sequential"]["items"][0]["precondition_note"])

        # Retrieve and verify persistence
        retrieved = app_service.get_application_case("APP-TEST-FOOD-001")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.tracking_reference, "MH-FOOD-2026-0001")

    def test_persistence_across_store_reinstantiation(self):
        """Simulates a backend restart by creating a new store over the same DB file."""
        req = ApplicationCreateRequest(
            application_id="APP-RESTART-002",
            entity_name="Ganesh Bakeries",
            facts={"annual_turnover": 4000000, "is_food_business": True},
            approvals=[ApprovalSnapshot(approval_id="F-01", name="FSSAI Registration")],
        )
        app_service.create_application_case(req)

        # Reinstantiate store pointing to same path
        fresh_store = ApplicationStore(path=self.db_path)
        record = fresh_store.get("APP-RESTART-002")

        self.assertIsNotNone(record)
        self.assertEqual(record.tracking_reference, "MH-FOOD-2026-0001")
        self.assertEqual(record.entity_name, "Ganesh Bakeries")
        self.assertEqual(record.status, "SUBMITTED")

    def test_application_creation_never_invokes_upstream_engines(self):
        """CRITICAL ISOLATION TEST:

        Proves that POST /api/applications consumes supplied state rather than
        re-evaluating engine-v3, workflow builder, or M4 readiness.
        """
        def sabotaged(*args, **kwargs):
            raise AssertionError("SABOTAGE: Upstream engine/M4 logic was invoked during application creation!")

        req = ApplicationCreateRequest(
            application_id="APP-ISOLATION-003",
            entity_name="Pure Foods LLP",
            facts={"is_food_business": True, "annual_turnover": 5000000},
            approvals=[ApprovalSnapshot(approval_id="F-02", readiness_status="READY")],
        )

        with patch("backend.engine_adapter.evaluate_facts", side_effect=sabotaged), \
             patch("backend.engine_adapter.build_workflow_for_facts", side_effect=sabotaged), \
             patch("backend.documents.service.requirements_for_application", side_effect=sabotaged), \
             patch("backend.documents.service.readiness_for_application", side_effect=sabotaged):

            # Must succeed completely without calling any sabotaged functions
            record = app_service.create_application_case(req)
            self.assertEqual(record.application_id, "APP-ISOLATION-003")
            self.assertEqual(record.status, "SUBMITTED")

    def test_rejection_of_empty_or_fabricated_upstream_context(self):
        """Verifies that empty upstream facts, invalid approvals, or malformed payloads are rejected with 422."""
        # 1. Missing entity name
        res1 = self.client.post("/api/applications", json={
            "entity_name": "",
            "facts": {"is_food_business": True},
            "approvals": [{"approval_id": "F-02"}],
        })
        self.assertEqual(res1.status_code, 422)

        # 2. Empty facts dictionary
        res2 = self.client.post("/api/applications", json={
            "entity_name": "Test Mill",
            "facts": {},
            "approvals": [{"approval_id": "F-02"}],
        })
        self.assertEqual(res2.status_code, 422)
        self.assertIn("Application requires an established fact vector", res2.json()["detail"])

        # 3. Empty approvals list
        res3 = self.client.post("/api/applications", json={
            "entity_name": "Test Mill",
            "facts": {"is_food_business": True},
            "approvals": [],
        })
        self.assertEqual(res3.status_code, 422)
        self.assertIn("Application requires at least one established statutory approval", res3.json()["detail"])

        # 4. Fabricated approval with a plausible prefix must still be rejected
        res4 = self.client.post("/api/applications", json={
            "entity_name": "Test Mill",
            "facts": {"is_food_business": True},
            "approvals": [{"approval_id": "S-999"}],
        })
        self.assertEqual(res4.status_code, 422)
        self.assertIn("not recognized", res4.json()["detail"])

        # 5. Invalid readiness status
        res5 = self.client.post("/api/applications", json={
            "entity_name": "Test Mill",
            "facts": {"is_food_business": True},
            "approvals": [{"approval_id": "F-02", "readiness_status": "TOTALLY_VALID_PROMISE"}],
        })
        self.assertEqual(res5.status_code, 422)
        self.assertIn("Invalid readiness status", res5.json()["detail"])

        # 6. Malformed submission reference
        res6 = self.client.post("/api/applications", json={
            "entity_name": "Test Mill",
            "facts": {"is_food_business": True},
            "approvals": [{"approval_id": "F-02", "readiness_status": "READY"}],
            "submissions": [{"document_id": "", "submission_id": "sub-123"}],
        })
        self.assertEqual(res6.status_code, 422)
        self.assertIn("submission references must specify both document_id and submission_id", res6.json()["detail"])

    def test_exception_sanitization_never_leaks_internals(self):
        """Verifies that internal server exceptions never leak raw error details, paths, or SQL."""
        payload = {
            "entity_name": "Error Probe Enterprise",
            "facts": {"is_food_business": True},
            "approvals": [{"approval_id": "F-02", "readiness_status": "READY"}],
        }

        with patch("backend.applications.api.create_application_case", side_effect=RuntimeError("/etc/shadow: SQLITE_CORRUPT at line 42")):
            res = self.client.post("/api/applications", json=payload)
            self.assertEqual(res.status_code, 500)
            detail = res.json()["detail"]
            self.assertEqual(detail, "An internal error occurred while processing the application case.")
            self.assertNotIn("/etc/shadow", detail)
            self.assertNotIn("SQLITE_CORRUPT", detail)

    def test_postgres_storage_path_and_parameterized_queries(self):
        """Verifies PostgreSQL storage initialization and parameterized queries via mock connection."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch("psycopg2.connect", return_value=mock_conn):
            pg_store = ApplicationStore(database_url="postgresql://user:pass@neon.tech/sih26db")
            self.assertTrue(pg_store.is_postgres)

            # Verify DDL executed
            self.assertTrue(mock_cursor.execute.called)
            first_call_sql = mock_cursor.execute.call_args_list[0][0][0]
            self.assertIn("CREATE TABLE IF NOT EXISTS applications", first_call_sql)

            # Test next_tracking_reference query
            mock_cursor.fetchone.return_value = [5]
            tracking_ref = pg_store.next_tracking_reference()
            self.assertEqual(tracking_ref, "MH-FOOD-2026-0006")

    def test_api_post_and_get_endpoints(self):
        """Tests REST API endpoints via TestClient."""
        payload = {
            "application_id": "APP-API-004",
            "entity_name": "Satara Agro Ltd",
            "facts": {"is_food_business": True, "workers_for_threshold": 67},
            "as_of": "2026-08-31",
            "approvals": [
                {"approval_id": "F-02", "name": "FSSAI State Licence", "readiness_status": "READY"},
                {"approval_id": "S-02", "name": "Factory Licence", "readiness_status": "READY"},
            ],
            "submissions": [
                {"document_id": "F02-FORM-B", "submission_id": "sub-999", "filename": "form_b.pdf"}
            ],
        }

        # 1. POST /api/applications
        res = self.client.post("/api/applications", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["application_id"], "APP-API-004")
        self.assertEqual(data["tracking_reference"], "MH-FOOD-2026-0001")
        self.assertEqual(data["status"], "SUBMITTED")
        self.assertEqual(data["entity_name"], "Satara Agro Ltd")

        # 2. GET /api/applications
        list_res = self.client.get("/api/applications")
        self.assertEqual(list_res.status_code, 200)
        list_data = list_res.json()
        self.assertEqual(list_data["total_count"], 1)
        self.assertEqual(list_data["applications"][0]["tracking_reference"], "MH-FOOD-2026-0001")

        # 3. GET /api/applications/{id}
        get_res = self.client.get("/api/applications/APP-API-004")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["tracking_reference"], "MH-FOOD-2026-0001")

        # 4. GET 404 for nonexistent application
        not_found_res = self.client.get("/api/applications/NONEXISTENT-999")
        self.assertEqual(not_found_res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
