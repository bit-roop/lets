"""The single choke point through which M5 reads M4 *static data*.

Everything here is a data lookup. Nothing here evaluates applicability,
conditions, workflow, or readiness.

Specifically, this module must never import ``backend.documents.service``.
That module's ``requirements_for_application`` and ``readiness_for_application``
call ``evaluate_facts`` / ``build_workflow_for_facts`` and ``evaluate_condition``
internally, so calling them would make M5 re-run the engine while appearing to
read M4. Applicability reaches M5 as an already-computed payload instead --
see ``backend/verification/m4_context.py``.

What remains here is genuinely static:

* the document registry, which loads JSON from ``regulatory-documents/`` and
  performs no evaluation;
* the submission store, an in-memory dictionary of what was uploaded.

M5 also never imports ``engine.*`` or ``backend.workflow.*``.
"""

from typing import List

from backend.documents.registry import get_document_registry
from backend.documents.submissions import get_submission_store


def spec(document_id: str):
    """DocumentSpec is a frozen dataclass; returned as-is."""
    return get_document_registry().spec(document_id)


def document_ids() -> List[str]:
    return [s.document_id for s in get_document_registry().specs()]


def requirements_for_document(document_id: str):
    """Frozen DocumentRequirement objects referencing this document_id.

    Static registry data. Carries no condition_state, because computing one
    would mean evaluating a condition.
    """
    return [r for r in get_document_registry().requirements()
            if r.document_id == document_id]


def all_requirements():
    """Every frozen DocumentRequirement in the M4 registry."""
    return list(get_document_registry().requirements())


def submission(submission_id: str):
    """The live M4 submission object. Callers MUST NOT mutate it."""
    return get_submission_store().items.get(submission_id)


def submissions_for_application(application_id: str):
    return get_submission_store().for_application(application_id)


def submission_storage_root():
    return get_submission_store().root
