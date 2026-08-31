"""Tests for Slice 4: prototype department review lifecycle.

Covers:
 1. Department listing and department-scoped case listing.
 2. Start review, query creation, query persistence.
 3. Applicant response and the officer seeing that response.
 4. Grant and reject decisions.
 5. Invalid state transitions and cross-department manipulation.
 6. Persistence across store re-instantiation (backend restart).
 7. Upstream isolation: the lifecycle works with engine-v3, M3, M4, and M5
    entry points sabotaged.
 8. Privacy/storage boundary: no document bytes, document text, filenames, or
    M5 extracted values reach storage or the officer view.
 9. Generic exception handling at the API boundary.
"""

import gc
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.applications import lifecycle_service as svc
from backend.applications.lifecycle import (
    APPLICATION_GRANTED,
    APPLICATION_QUERY_RAISED,
    APPLICATION_REJECTED,
    APPLICATION_RESPONDED,
    APPLICATION_SUBMITTED,
    APPLICATION_UNDER_REVIEW,
    APPROVAL_GRANTED,
    APPROVAL_IN_SCRUTINY,
    APPROVAL_QUERY_PENDING,
    APPROVAL_REJECTED,
    APPROVAL_SUBMITTED,
    QUERY_OPEN,
    QUERY_RESOLVED,
    QUERY_RESPONDED,
    InvalidTransition,
    LifecycleForbidden,
    LifecycleNotFound,
    LifecycleValidation,
    derive_application_status,
)
from backend.applications.store import ApplicationStore, reset_application_store
from backend.main import app

APP_ID = "APP-SLICE4-FOOD-001"

BASE_PAYLOAD = {
    "application_id": APP_ID,
    "entity_name": "Sahyadri Foods Private Limited",
    "facts": {"is_food_business": True, "annual_turnover": 80000000},
    "as_of": "2026-08-31",
    "approvals": [
        {
            "approval_id": "F-02",
            "name": "FSSAI State Licence",
            "department": "FSSAI",
            "sla_days": 60,
            "readiness_status": "READY",
        },
        {
            "approval_id": "S-02",
            "name": "Factory Licence",
            "department": "DISH",
            "sla_days": 30,
            "readiness_status": "INCOMPLETE",
        },
        {
            # Not simulated in this prototype; must never appear in either
            # department portal.
            "approval_id": "E-05",
            "name": "Udyam Registration",
            "department": "MSME",
            "readiness_status": "UNSUPPORTED",
        },
    ],
    "submissions": [
        {
            "document_id": "F02-FORM-B",
            "submission_id": "sub-form-b-001",
            "filename": "rahul_kulkarni_aadhaar_scan.pdf",
            "state": "PROVIDED_UNVALIDATED",
        }
    ],
    "verification_records": [
        {
            "document_id": "F02-FORM-B",
            "record_id": "rec-001",
            "disposition": "ACCEPTED_FOR_REVIEW",
            "internal_consistency": "CONSISTENT",
            "confidence_overall": 0.82,
        }
    ],
    "workflow_snapshot": {
        "schedule": {"nodes": {"F-02": {"depth": 0, "blocked_by": []},
                               "S-02": {"depth": 1, "blocked_by": ["S-01"]}}}
    },
}


class Slice4TestBase(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.gettempdir()) / "sih26_slice4_test_dbs"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.test_dir / f"test_lifecycle_{uuid.uuid4().hex}.db"
        reset_application_store(self.db_path)
        self.client = TestClient(app)
        created = self.client.post("/api/applications", json=BASE_PAYLOAD)
        self.assertEqual(created.status_code, 201, created.text)

    def tearDown(self):
        reset_application_store(None)
        gc.collect()
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except OSError:
                pass

    # Convenience helpers -------------------------------------------------

    def start_review(self, approval_id="F-02", department="FSSAI"):
        return self.client.post(
            f"/api/applications/{APP_ID}/approvals/{approval_id}/start-review",
            json={"department": department},
        )

    def raise_query(self, approval_id="F-02", department="FSSAI",
                    text="Please provide the current site layout plan.",
                    deadline="2026-09-30"):
        return self.client.post(
            f"/api/applications/{APP_ID}/queries",
            json={"approval_id": approval_id, "department": department,
                  "query_text": text, "deadline": deadline},
        )


class TestDepartmentListing(Slice4TestBase):
    def test_department_directory_lists_only_simulated_departments(self):
        res = self.client.get("/api/departments")
        self.assertEqual(res.status_code, 200)
        codes = {d["department"] for d in res.json()["departments"]}
        self.assertEqual(codes, {"DISH", "FSSAI"})
        for entry in res.json()["departments"]:
            self.assertIn("Simulation", entry["label"])

    def test_department_listing_scopes_cases_to_owning_department(self):
        fssai = self.client.get("/api/departments/FSSAI/applications").json()
        self.assertEqual(fssai["total_count"], 1)
        case = fssai["cases"][0]
        self.assertEqual(case["tracking_reference"], "MH-FOOD-2026-0001")
        self.assertEqual(case["entity_name"], "Sahyadri Foods Private Limited")
        self.assertEqual([a["approval_id"] for a in case["approvals"]], ["F-02"])
        self.assertEqual(case["application_status"], APPLICATION_SUBMITTED)

        dish = self.client.get("/api/departments/DISH/applications").json()
        self.assertEqual([a["approval_id"] for a in dish["cases"][0]["approvals"]], ["S-02"])

    def test_non_simulated_approvals_are_never_listed(self):
        for department in ("FSSAI", "DISH"):
            listing = self.client.get(f"/api/departments/{department}/applications").json()
            ids = {a["approval_id"] for case in listing["cases"] for a in case["approvals"]}
            self.assertNotIn("E-05", ids)

    def test_unknown_department_is_rejected(self):
        self.assertEqual(self.client.get("/api/departments/MPCB/applications").status_code, 422)

    def test_officer_case_detail_echoes_upstream_status_unchanged(self):
        detail = self.client.get(f"/api/departments/DISH/applications/{APP_ID}").json()
        approval = detail["approvals"][0]
        # M4 established INCOMPLETE. Slice 4 must show it as-is and must not
        # promote it just because a case was filed.
        self.assertEqual(approval["readiness_status"], "INCOMPLETE")
        self.assertEqual(approval["sla_days"], 30)
        self.assertIn("do not establish authenticity", detail["evidence_notice"])

    def test_department_cannot_open_a_case_it_does_not_own(self):
        res = self.client.get("/api/departments/FSSAI/applications/UNKNOWN-CASE")
        self.assertEqual(res.status_code, 404)


class TestOfficerReviewFlow(Slice4TestBase):
    def test_start_review_moves_approval_into_scrutiny(self):
        res = self.start_review()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], APPROVAL_IN_SCRUTINY)

        app_status = self.client.get(f"/api/applications/{APP_ID}").json()["lifecycle"]["application_status"]
        self.assertEqual(app_status, APPLICATION_UNDER_REVIEW)

    def test_grant_requires_review_to_have_started(self):
        res = self.client.post(
            f"/api/applications/{APP_ID}/approvals/F-02/grant",
            json={"department": "FSSAI"},
        )
        self.assertEqual(res.status_code, 409)
        self.assertIn("SUBMITTED", res.json()["detail"])

    def test_grant_decision_is_recorded_as_a_prototype_decision(self):
        self.start_review()
        res = self.client.post(
            f"/api/applications/{APP_ID}/approvals/F-02/grant",
            json={"department": "FSSAI", "decision_note": "Checklist satisfied in simulation."},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], APPROVAL_GRANTED)
        self.assertIsNotNone(res.json()["decided_at"])

        events = self.client.get(f"/api/applications/{APP_ID}").json()["lifecycle"]["events"]
        decision = [e for e in events if e["event_type"] == "APPROVAL_GRANTED"]
        self.assertEqual(len(decision), 1)
        self.assertIn("simulation", decision[0]["detail"].lower())

    def test_reject_decision_is_terminal(self):
        self.start_review("S-02", "DISH")
        res = self.client.post(
            f"/api/applications/{APP_ID}/approvals/S-02/reject",
            json={"department": "DISH", "decision_note": "Mandatory evidence absent."},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], APPROVAL_REJECTED)

        # No further transition is possible out of a terminal state.
        again = self.start_review("S-02", "DISH")
        self.assertEqual(again.status_code, 409)
        grant = self.client.post(
            f"/api/applications/{APP_ID}/approvals/S-02/grant", json={"department": "DISH"}
        )
        self.assertEqual(grant.status_code, 409)

    def test_application_reaches_granted_only_when_every_reviewable_approval_is_granted(self):
        self.start_review("F-02", "FSSAI")
        self.client.post(f"/api/applications/{APP_ID}/approvals/F-02/grant", json={"department": "FSSAI"})
        status = self.client.get(f"/api/applications/{APP_ID}").json()["lifecycle"]["application_status"]
        self.assertEqual(status, APPLICATION_UNDER_REVIEW)

        self.start_review("S-02", "DISH")
        self.client.post(f"/api/applications/{APP_ID}/approvals/S-02/grant", json={"department": "DISH"})
        status = self.client.get(f"/api/applications/{APP_ID}").json()["lifecycle"]["application_status"]
        self.assertEqual(status, APPLICATION_GRANTED)

    def test_application_is_rejected_when_all_decided_and_one_refused(self):
        self.start_review("F-02", "FSSAI")
        self.client.post(f"/api/applications/{APP_ID}/approvals/F-02/grant", json={"department": "FSSAI"})
        self.start_review("S-02", "DISH")
        self.client.post(f"/api/applications/{APP_ID}/approvals/S-02/reject", json={"department": "DISH"})
        status = self.client.get(f"/api/applications/{APP_ID}").json()["lifecycle"]["application_status"]
        self.assertEqual(status, APPLICATION_REJECTED)


class TestQueryLifecycle(Slice4TestBase):
    def test_query_creation_moves_approval_to_query_pending(self):
        self.start_review()
        res = self.raise_query()
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(body["status"], QUERY_OPEN)
        self.assertEqual(body["deadline"], "2026-09-30")
        self.assertEqual(body["approval_name"], "FSSAI State Licence")

        detail = self.client.get(f"/api/departments/FSSAI/applications/{APP_ID}").json()
        self.assertEqual(detail["approvals"][0]["status"], APPROVAL_QUERY_PENDING)
        self.assertEqual(detail["application_status"], APPLICATION_QUERY_RAISED)

    def test_query_persists_and_is_listable(self):
        self.start_review()
        query_id = self.raise_query().json()["query_id"]

        listing = self.client.get(f"/api/applications/{APP_ID}/queries").json()
        self.assertEqual(listing["total_count"], 1)
        self.assertEqual(listing["queries"][0]["query_id"], query_id)

        single = self.client.get(f"/api/applications/{APP_ID}/queries/{query_id}")
        self.assertEqual(single.status_code, 200)
        self.assertEqual(single.json()["query_text"], "Please provide the current site layout plan.")

        scoped = self.client.get(f"/api/applications/{APP_ID}/queries?department=DISH").json()
        self.assertEqual(scoped["total_count"], 0)

    def test_applicant_response_is_visible_to_the_department(self):
        self.start_review()
        query_id = self.raise_query().json()["query_id"]

        responded = self.client.post(
            f"/api/applications/{APP_ID}/queries/{query_id}/respond",
            json={"response_text": "Revised layout plan has been uploaded.",
                  "response_document_id": "F02-LAYOUT",
                  "response_submission_id": "sub-form-b-001"},
        )
        self.assertEqual(responded.status_code, 200)
        self.assertEqual(responded.json()["status"], QUERY_RESPONDED)
        self.assertIsNotNone(responded.json()["responded_at"])

        officer_view = self.client.get(f"/api/departments/FSSAI/applications/{APP_ID}").json()
        officer_query = officer_view["queries"][0]
        self.assertEqual(officer_query["response_text"], "Revised layout plan has been uploaded.")
        self.assertEqual(officer_query["response_document_id"], "F02-LAYOUT")
        self.assertEqual(officer_view["application_status"], APPLICATION_RESPONDED)

    def test_response_may_only_reference_a_submission_already_on_the_case(self):
        self.start_review()
        query_id = self.raise_query().json()["query_id"]
        res = self.client.post(
            f"/api/applications/{APP_ID}/queries/{query_id}/respond",
            json={"response_text": "See attached.", "response_submission_id": "sub-never-filed"},
        )
        self.assertEqual(res.status_code, 422)
        self.assertIn("not attached to this application case", res.json()["detail"])

    def test_resolve_returns_approval_to_scrutiny_and_allows_grant(self):
        self.start_review()
        query_id = self.raise_query().json()["query_id"]
        self.client.post(
            f"/api/applications/{APP_ID}/queries/{query_id}/respond",
            json={"response_text": "Layout supplied."},
        )
        resolved = self.client.post(
            f"/api/applications/{APP_ID}/queries/{query_id}/resolve",
            json={"department": "FSSAI", "resolution_note": "Response accepted in simulation."},
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["status"], QUERY_RESOLVED)

        detail = self.client.get(f"/api/departments/FSSAI/applications/{APP_ID}").json()
        self.assertEqual(detail["approvals"][0]["status"], APPROVAL_IN_SCRUTINY)

        granted = self.client.post(
            f"/api/applications/{APP_ID}/approvals/F-02/grant", json={"department": "FSSAI"}
        )
        self.assertEqual(granted.status_code, 200)
        self.assertEqual(granted.json()["status"], APPROVAL_GRANTED)

    def test_full_journey_submitted_query_response_granted(self):
        self.assertEqual(
            self.client.get(f"/api/applications/{APP_ID}").json()["lifecycle"]["application_status"],
            APPLICATION_SUBMITTED,
        )
        self.start_review()
        query_id = self.raise_query().json()["query_id"]
        self.client.post(f"/api/applications/{APP_ID}/queries/{query_id}/respond",
                         json={"response_text": "Provided."})
        self.client.post(f"/api/applications/{APP_ID}/queries/{query_id}/resolve",
                         json={"department": "FSSAI"})
        self.client.post(f"/api/applications/{APP_ID}/approvals/F-02/grant",
                         json={"department": "FSSAI"})
        self.start_review("S-02", "DISH")
        self.client.post(f"/api/applications/{APP_ID}/approvals/S-02/grant",
                         json={"department": "DISH"})

        final = self.client.get(f"/api/applications/{APP_ID}").json()["lifecycle"]
        self.assertEqual(final["application_status"], APPLICATION_GRANTED)
        self.assertEqual(final["open_queries"], [])
        self.assertIn("simulation", final["simulation_notice"].lower())


class TestInvalidTransitions(Slice4TestBase):
    def test_cannot_respond_to_a_nonexistent_query(self):
        res = self.client.post(
            f"/api/applications/{APP_ID}/queries/QRY-does-not-exist/respond",
            json={"response_text": "Anything."},
        )
        self.assertEqual(res.status_code, 404)

    def test_cannot_respond_to_an_already_resolved_query(self):
        self.start_review()
        query_id = self.raise_query().json()["query_id"]
        self.client.post(f"/api/applications/{APP_ID}/queries/{query_id}/respond",
                         json={"response_text": "First response."})
        self.client.post(f"/api/applications/{APP_ID}/queries/{query_id}/resolve",
                         json={"department": "FSSAI"})
        res = self.client.post(f"/api/applications/{APP_ID}/queries/{query_id}/respond",
                               json={"response_text": "Second response."})
        self.assertEqual(res.status_code, 409)

    def test_cannot_respond_twice_to_the_same_open_query(self):
        self.start_review()
        query_id = self.raise_query().json()["query_id"]
        self.client.post(f"/api/applications/{APP_ID}/queries/{query_id}/respond",
                         json={"response_text": "First."})
        second = self.client.post(f"/api/applications/{APP_ID}/queries/{query_id}/respond",
                                  json={"response_text": "Second."})
        self.assertEqual(second.status_code, 409)

    def test_cannot_resolve_a_query_that_has_no_response(self):
        self.start_review()
        query_id = self.raise_query().json()["query_id"]
        res = self.client.post(f"/api/applications/{APP_ID}/queries/{query_id}/resolve",
                               json={"department": "FSSAI"})
        self.assertEqual(res.status_code, 409)

    def test_cannot_create_a_query_for_an_unknown_application(self):
        res = self.client.post(
            "/api/applications/APP-NOT-FILED/queries",
            json={"approval_id": "F-02", "department": "FSSAI",
                  "query_text": "Hello", "deadline": "2026-09-30"},
        )
        self.assertEqual(res.status_code, 404)

    def test_cannot_create_a_query_for_an_approval_not_on_the_case(self):
        res = self.raise_query(approval_id="F-03")
        self.assertEqual(res.status_code, 404)

    def test_cannot_raise_a_query_before_review_starts(self):
        res = self.raise_query()
        self.assertEqual(res.status_code, 409)

    def test_cannot_manipulate_another_departments_approval(self):
        # DISH attempting to act on the FSSAI-owned approval.
        self.assertEqual(self.start_review("F-02", "DISH").status_code, 403)
        self.start_review("F-02", "FSSAI")
        self.assertEqual(self.raise_query(approval_id="F-02", department="DISH").status_code, 403)
        self.assertEqual(
            self.client.post(f"/api/applications/{APP_ID}/approvals/F-02/grant",
                             json={"department": "DISH"}).status_code,
            403,
        )

    def test_cannot_resolve_another_departments_query(self):
        self.start_review()
        query_id = self.raise_query().json()["query_id"]
        self.client.post(f"/api/applications/{APP_ID}/queries/{query_id}/respond",
                         json={"response_text": "Done."})
        res = self.client.post(f"/api/applications/{APP_ID}/queries/{query_id}/resolve",
                               json={"department": "DISH"})
        self.assertEqual(res.status_code, 403)

    def test_query_payload_validation(self):
        self.start_review()
        blank = self.raise_query(text="   ")
        self.assertEqual(blank.status_code, 422)
        bad_date = self.raise_query(deadline="30-09-2026")
        self.assertEqual(bad_date.status_code, 422)
        impossible_date = self.raise_query(deadline="2026-02-31")
        self.assertEqual(impossible_date.status_code, 422)
        too_long = self.raise_query(text="x" * 2001)
        self.assertEqual(too_long.status_code, 422)

    def test_unsimulated_department_is_rejected_on_actions(self):
        res = self.start_review("F-02", "MPCB")
        self.assertEqual(res.status_code, 422)
        self.assertIn("not a simulated department", res.json()["detail"])

    def test_state_machine_rejects_illegal_transitions_directly(self):
        opened = svc.start_review(APP_ID, "F-02", "FSSAI")
        self.assertEqual(opened.status, APPROVAL_IN_SCRUTINY)
        # IN_SCRUTINY -> IN_SCRUTINY is not a permitted edge.
        with self.assertRaises(InvalidTransition):
            svc.start_review(APP_ID, "F-02", "FSSAI")

    def test_service_raises_typed_errors(self):
        with self.assertRaises(LifecycleNotFound):
            svc.get_department_case("FSSAI", "APP-MISSING")
        with self.assertRaises(LifecycleValidation):
            svc.list_department_cases("NOT-A-DEPARTMENT")
        with self.assertRaises(LifecycleForbidden):
            svc.start_review(APP_ID, "E-05", "DISH")


class TestPersistence(Slice4TestBase):
    def test_lifecycle_survives_store_reinstantiation(self):
        self.start_review()
        query_id = self.raise_query().json()["query_id"]
        self.client.post(f"/api/applications/{APP_ID}/queries/{query_id}/respond",
                         json={"response_text": "Layout uploaded."})
        self.client.post(f"/api/applications/{APP_ID}/queries/{query_id}/resolve",
                         json={"department": "FSSAI"})
        self.client.post(f"/api/applications/{APP_ID}/approvals/F-02/grant",
                         json={"department": "FSSAI", "decision_note": "Granted in simulation."})

        # Simulate a backend restart over the same database file.
        fresh = ApplicationStore(path=self.db_path)

        approvals = {r["approval_id"]: r for r in fresh.list_approval_lifecycle(APP_ID)}
        self.assertEqual(approvals["F-02"]["status"], APPROVAL_GRANTED)
        self.assertEqual(approvals["F-02"]["decision_note"], "Granted in simulation.")

        queries = fresh.list_queries(APP_ID)
        self.assertEqual(len(queries), 1)
        self.assertEqual(queries[0]["status"], QUERY_RESOLVED)
        self.assertEqual(queries[0]["response_text"], "Layout uploaded.")
        self.assertEqual(queries[0]["deadline"], "2026-09-30")

        record = fresh.get(APP_ID)
        self.assertEqual(record.status, APPLICATION_UNDER_REVIEW)

        events = fresh.list_events(APP_ID)
        self.assertIn("APPROVAL_GRANTED", {e["event_type"] for e in events})

    def test_lifecycle_tables_live_in_the_existing_application_database(self):
        self.start_review()
        self.raise_query()
        with sqlite3.connect(str(self.db_path)) as conn:
            names = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
        # One database, extended. Not a second store.
        self.assertIn("applications", names)
        self.assertIn("approval_lifecycle", names)
        self.assertIn("application_queries", names)
        self.assertIn("application_events", names)

    def test_default_state_is_submitted_for_untouched_approvals(self):
        lifecycle = self.client.get(f"/api/applications/{APP_ID}").json()["lifecycle"]
        states = {a["approval_id"]: a["status"] for a in lifecycle["approvals"]}
        self.assertEqual(states, {"F-02": APPROVAL_SUBMITTED, "S-02": APPROVAL_SUBMITTED})


class TestUpstreamIsolation(Slice4TestBase):
    """Slice 4 must sit above M1-M5 and never re-enter them."""

    def _sabotage(self):
        def boom(*args, **kwargs):
            raise AssertionError(
                "SABOTAGE: an upstream regulatory/workflow/document function was "
                "invoked from the Slice 4 lifecycle."
            )
        return [
            patch("backend.engine_adapter.evaluate_facts", side_effect=boom),
            patch("backend.engine_adapter.build_workflow_for_facts", side_effect=boom),
            patch("backend.documents.service.requirements_for_application", side_effect=boom),
            patch("backend.documents.service.readiness_for_application", side_effect=boom),
            patch("backend.documents.conditions.evaluate_condition", side_effect=boom),
            patch("backend.workflow.service.build_workflow", side_effect=boom),
        ]

    def test_entire_lifecycle_runs_with_upstream_sabotaged(self):
        patches = self._sabotage()
        for p in patches:
            p.start()
        try:
            self.assertEqual(self.start_review().status_code, 200)
            query_id = self.raise_query().json()["query_id"]
            self.assertEqual(
                self.client.post(f"/api/applications/{APP_ID}/queries/{query_id}/respond",
                                 json={"response_text": "Provided."}).status_code, 200)
            self.assertEqual(
                self.client.post(f"/api/applications/{APP_ID}/queries/{query_id}/resolve",
                                 json={"department": "FSSAI"}).status_code, 200)
            self.assertEqual(
                self.client.post(f"/api/applications/{APP_ID}/approvals/F-02/grant",
                                 json={"department": "FSSAI"}).status_code, 200)
            self.assertEqual(
                self.client.get(f"/api/departments/FSSAI/applications/{APP_ID}").status_code, 200)
            self.assertEqual(self.client.get(f"/api/applications/{APP_ID}").status_code, 200)
        finally:
            for p in patches:
                p.stop()

    def test_lifecycle_modules_do_not_import_upstream_layers(self):
        import backend.applications.lifecycle as lifecycle_mod
        import backend.applications.lifecycle_service as service_mod

        for module in (lifecycle_mod, service_mod):
            source = Path(module.__file__).read_text(encoding="utf-8")
            for forbidden in (
                "import backend.engine_adapter",
                "from backend.engine_adapter",
                "from backend.workflow",
                "from backend.documents",
                "from backend.verification",
                "import engine",
            ):
                self.assertNotIn(
                    forbidden, source,
                    f"{module.__name__} must not import upstream layer: {forbidden}",
                )

    def test_lifecycle_never_alters_established_upstream_state(self):
        before = self.client.get(f"/api/applications/{APP_ID}").json()
        self.start_review("S-02", "DISH")
        self.client.post(f"/api/applications/{APP_ID}/approvals/S-02/grant",
                         json={"department": "DISH"})
        after = self.client.get(f"/api/applications/{APP_ID}").json()

        # Applicability, readiness, submissions, verification findings and the
        # M3 timeline snapshot must be byte-identical after a decision.
        self.assertEqual(before["approvals"], after["approvals"])
        self.assertEqual(before["submissions"], after["submissions"])
        self.assertEqual(before["verification_records"], after["verification_records"])
        self.assertEqual(before["timeline"], after["timeline"])
        self.assertEqual(before["facts"], after["facts"])

    def test_granting_does_not_promote_incomplete_readiness(self):
        self.start_review("S-02", "DISH")
        self.client.post(f"/api/applications/{APP_ID}/approvals/S-02/grant",
                         json={"department": "DISH"})
        detail = self.client.get(f"/api/departments/DISH/applications/{APP_ID}").json()
        approval = detail["approvals"][0]
        self.assertEqual(approval["status"], APPROVAL_GRANTED)
        # M4 said INCOMPLETE. A simulated grant does not make evidence ready.
        self.assertEqual(approval["readiness_status"], "INCOMPLETE")


class TestPrivacyBoundary(Slice4TestBase):
    def test_officer_view_exposes_no_filenames_or_extracted_values(self):
        raw = self.client.get(f"/api/departments/FSSAI/applications/{APP_ID}").text
        self.assertNotIn("rahul_kulkarni_aadhaar_scan.pdf", raw)
        self.assertNotIn("filename", raw)
        # Confidence scores are an internal M5 signal, not an officer artefact.
        self.assertNotIn("confidence_overall", raw)
        self.assertNotIn("0.82", raw)

    def test_officer_view_carries_evidence_references_only(self):
        detail = self.client.get(f"/api/departments/FSSAI/applications/{APP_ID}").json()
        self.assertEqual(len(detail["evidence"]), 1)
        item = detail["evidence"][0]
        self.assertEqual(set(item.keys()), {
            "document_id", "submission_reference",
            "evidence_state", "automated_check_outcome", "automated_check_consistency",
        })
        self.assertEqual(item["document_id"], "F02-FORM-B")
        self.assertEqual(item["automated_check_outcome"], "ACCEPTED_FOR_REVIEW")

    def test_officer_view_does_not_expose_the_applicant_fact_vector(self):
        detail = self.client.get(f"/api/departments/FSSAI/applications/{APP_ID}").json()
        self.assertNotIn("facts", detail)

    def test_no_document_bytes_or_text_reach_lifecycle_storage(self):
        self.start_review()
        self.raise_query(text="Please re-upload a legible copy.")
        with sqlite3.connect(str(self.db_path)) as conn:
            for table in ("approval_lifecycle", "application_queries", "application_events"):
                columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
                for banned in ("content", "file_bytes", "blob", "raw_text",
                               "document_text", "extracted_values", "sha256"):
                    self.assertNotIn(banned, columns,
                                     f"{table} must not carry a '{banned}' column")

    def test_decision_wording_never_claims_government_approval(self):
        self.start_review()
        self.client.post(f"/api/applications/{APP_ID}/approvals/F-02/grant",
                         json={"department": "FSSAI"})
        blob = (
            self.client.get(f"/api/departments/FSSAI/applications/{APP_ID}").text
            + self.client.get(f"/api/applications/{APP_ID}").text
            + self.client.get("/api/departments").text
        ).lower()
        for banned in ("government verified", "government approved", "officially approved",
                       "maitri approved", "maitri submitted", "authenticity verified"):
            self.assertNotIn(banned, blob)
        self.assertIn("simulation", blob)


class TestErrorHandling(Slice4TestBase):
    def test_internal_exceptions_are_not_leaked_to_clients(self):
        with patch("backend.applications.lifecycle_api.svc.list_department_cases",
                   side_effect=RuntimeError("/etc/shadow: SQLITE_CORRUPT at line 42")):
            res = self.client.get("/api/departments/FSSAI/applications")
            self.assertEqual(res.status_code, 500)
            detail = res.json()["detail"]
            self.assertNotIn("/etc/shadow", detail)
            self.assertNotIn("SQLITE_CORRUPT", detail)
            self.assertEqual(
                detail,
                "An internal error occurred while processing the department lifecycle request.",
            )

    def test_internal_exceptions_on_actions_are_not_leaked(self):
        with patch("backend.applications.lifecycle_api.svc.start_review",
                   side_effect=RuntimeError("psycopg2.OperationalError: password=hunter2")):
            res = self.start_review()
            self.assertEqual(res.status_code, 500)
            self.assertNotIn("hunter2", res.json()["detail"])


class TestStatusDerivation(unittest.TestCase):
    """The aggregation rule, exercised without any I/O."""

    def test_open_query_dominates(self):
        self.assertEqual(
            derive_application_status(
                {"F-02": APPROVAL_QUERY_PENDING, "S-02": APPROVAL_GRANTED},
                [{"status": QUERY_OPEN}],
            ),
            APPLICATION_QUERY_RAISED,
        )

    def test_responded_query_reported_before_review_state(self):
        self.assertEqual(
            derive_application_status(
                {"F-02": APPROVAL_QUERY_PENDING},
                [{"status": QUERY_RESPONDED}],
            ),
            APPLICATION_RESPONDED,
        )

    def test_resolved_queries_do_not_hold_the_application_open(self):
        self.assertEqual(
            derive_application_status({"F-02": APPROVAL_GRANTED}, [{"status": QUERY_RESOLVED}]),
            APPLICATION_GRANTED,
        )

    def test_no_reviewable_approvals_stays_submitted(self):
        self.assertEqual(derive_application_status({}, []), APPLICATION_SUBMITTED)

    def test_partial_progress_is_under_review(self):
        self.assertEqual(
            derive_application_status(
                {"F-02": APPROVAL_GRANTED, "S-02": APPROVAL_SUBMITTED}, []),
            APPLICATION_UNDER_REVIEW,
        )

    def test_mixed_terminal_outcome_is_rejected(self):
        self.assertEqual(
            derive_application_status(
                {"F-02": APPROVAL_GRANTED, "S-02": APPROVAL_REJECTED}, []),
            APPLICATION_REJECTED,
        )


if __name__ == "__main__":
    unittest.main()


