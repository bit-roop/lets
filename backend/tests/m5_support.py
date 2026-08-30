"""Shared helpers for the M5 test suites.

Submissions are created through M4's own public API, never by reaching into
M4's internals, so the tests exercise the same path the application uses.
"""

import json
import tempfile
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.tests.fixtures.m5 import make_fixtures
from backend.verification.profiles.registry import reset_profile_registry
from backend.verification.store import RecordStore, reset_record_store

FIXTURE_DIR = Path(make_fixtures.__file__).resolve().parent

#: Persona B facts are REAL REPOSITORY DATA (engine-v3/personas/persona_b.json).
#: Note that `manufacturing_processing` is absent from every persona in the
#: repository, so M4 reports UNKNOWN for the conditional F-02 requirements.
PERSONA_B = {
    "stage": "new_setup",
    "entity_type": "private_limited",
    "location_authority": "MIDC",
    "land_classification": "midc_industrial",
    "builtup_area_sqm": 4200,
    "is_food_business": True,
    "annual_turnover": 80000000,
    "investment_plant_machinery": 60000000,
    "employees_total": 45,
    "workers_for_threshold": 67,
    "uses_power": True,
    "contract_labourers": 22,
    "food_handlers": 30,
    "boiler_operates": True,
    "boiler_capacity_litres": 500,
    "export": False,
    "multi_state_operation": False,
}


def ensure_fixtures():
    make_fixtures.build_all(FIXTURE_DIR)


def isolated_store(test_case):
    """Point the M5 record store at a throwaway database for one test.

    Every M5 test isolates, including those that never look at a record: a test
    that quietly falls back to the on-disk store inherits whatever earlier runs
    left there, which makes failures depend on execution history rather than on
    the code. `client()` calls this, so isolation is the default and cannot be
    forgotten.
    """
    import gc
    root = Path(tempfile.gettempdir()) / "sih26_m5_test_dbs"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"records_{uuid.uuid4().hex}.db"
    def _cleanup():
        reset_record_store(None)
        gc.collect()
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass
    store = RecordStore(path)
    reset_record_store(path)
    test_case.addCleanup(_cleanup)
    return store


def client(test_case=None) -> TestClient:
    """A test client with a fresh profile registry and an isolated record store.

    Pass the TestCase so the store is isolated for the duration of that test.
    """
    reset_profile_registry()
    if test_case is not None:
        isolated_store(test_case)
    return TestClient(app)


def m4_result(api: TestClient, facts) -> dict:
    """Establish an M4 requirements result through M4's own endpoint.

    M5 consumes this artefact. Tests build it the same way the UI does, so the
    thing under test is the real integration boundary.
    """
    response = api.post("/api/documents/requirements", json={"facts": facts})
    assert response.status_code == 200, response.text
    return response.json()


def m4_readiness(api: TestClient, application_id: str, facts) -> dict:
    """M4's own readiness result, for the overlay to echo back."""
    response = api.get("/api/documents/readiness", params={
        "application_id": application_id, "facts": json.dumps(facts)})
    assert response.status_code == 200, response.text
    return response.json()


def submit_upload(api: TestClient, application_id: str, document_id: str,
                  fixture_name: str) -> str:
    """Upload through M4's real endpoint and return the submission_id."""
    path = FIXTURE_DIR / fixture_name
    with path.open("rb") as fh:
        response = api.post("/api/documents/submit", files={
            "file": (path.name, fh, "application/pdf"),
        }, data={
            "application_id": application_id,
            "document_id": document_id,
            "item_kind": "UPLOAD_DOCUMENT",
        })
    assert response.status_code == 200, response.text
    return response.json()["submission_id"]
