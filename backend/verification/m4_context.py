"""A read-only view over an M4 result that has already been established.

Why this module exists
----------------------
M5 previously obtained applicability by calling
``backend.documents.service.requirements_for_application``. That looked like
reading M4, but it is not: internally that function calls ``evaluate_facts``
(and, when workflow-aware, ``build_workflow_for_facts``) and then
``evaluate_condition`` for every requirement. So every M5 analysis silently
re-ran the engine and re-evaluated every condition.

Re-running produces an answer that is usually the same, which is exactly what
makes it dangerous: M5 could diverge from the applicability the applicant was
actually shown -- different `as_of`, different workflow-awareness, a fact edited
between calls -- and nothing would surface the divergence. M5's whole claim is
that it observes M4's decision rather than forming its own.

So M5 is now *handed* the M4 result and reads it. The payload is exactly what
``POST /api/documents/requirements`` returns, which is exactly what the UI
already holds when it asks for verification. M5 consumes that artefact and has
no route to produce one.

This module performs no evaluation. It indexes a dictionary.
"""

from typing import Any, Dict, List, Optional, Tuple

from . import states
from .models import M4Observation


class M4ContextError(ValueError):
    """The supplied M4 result is missing or not shaped like an M4 result."""


class M4Context:
    """An immutable index over one already-computed M4 requirements result.

    Construction copies the payload, so a caller cannot mutate what M5 read,
    and M5 cannot mutate what the caller holds.
    """

    def __init__(self, payload: Dict[str, Any]):
        if not isinstance(payload, dict):
            raise M4ContextError("the M4 result must be an object")
        approvals = payload.get("approvals")
        if not isinstance(approvals, list):
            raise M4ContextError(
                "the M4 result must contain an 'approvals' list; supply the "
                "response from POST /api/documents/requirements")

        self._approvals: List[Dict[str, Any]] = []
        self._rows_by_document: Dict[str, List[Dict[str, Any]]] = {}

        for approval in approvals:
            if not isinstance(approval, dict):
                raise M4ContextError("each approval in the M4 result must be an object")
            coverage = approval.get("coverage") or {}
            entry = {
                "approval_id": approval.get("approval_id"),
                "engine_state": approval.get("engine_state"),
                "coverage_status": coverage.get("status"),
                "requirements": [],
            }
            for row in approval.get("requirements") or []:
                if not isinstance(row, dict) or not row.get("document_id"):
                    continue
                # Copy so later mutation by anyone cannot change what M5 observed.
                frozen = dict(row)
                frozen["_approval_id"] = entry["approval_id"]
                frozen["_engine_state"] = entry["engine_state"]
                frozen["_coverage_status"] = entry["coverage_status"]
                entry["requirements"].append(frozen)
                self._rows_by_document.setdefault(row["document_id"], []).append(frozen)
            self._approvals.append(entry)

        if not self._rows_by_document:
            raise M4ContextError(
                "the M4 result contains no requirement rows; M5 has nothing to observe")

    # -- observation -------------------------------------------------------

    def rows_for_document(self, document_id: str) -> List[Dict[str, Any]]:
        return list(self._rows_by_document.get(document_id, []))

    def approvals(self) -> List[Dict[str, Any]]:
        return [dict(approval, requirements=list(approval["requirements"]))
                for approval in self._approvals]

    def observe_document(self, document_id: str) -> Tuple[str, List[M4Observation]]:
        """What M4 already decided about every requirement using this document.

        Precedence when a document backs several requirements: any TRUE wins,
        else any UNKNOWN wins, else FALSE. UNKNOWN outranks FALSE so that an
        unresolved condition is never discarded in favour of a resolved one.
        """
        rows = self._rows_by_document.get(document_id)
        if not rows:
            return states.UNSUPPORTED_APPROVAL, []

        observations = [observation_from_row(row) for row in rows]
        ranked = [observed_state_for_row(row) for row in rows]

        for candidate in (states.APPLICABLE_CONDITION_TRUE,
                          states.UNRESOLVED_CONDITION_UNKNOWN,
                          states.UNRESOLVED_ENGINE_STATE,
                          states.NOT_APPLICABLE_CONDITION_FALSE,
                          states.UNSUPPORTED_APPROVAL):
            if candidate in ranked:
                return candidate, observations
        return states.UNSUPPORTED_APPROVAL, observations


def observed_state_for_row(row: Dict[str, Any]) -> str:
    """Map one already-evaluated M4 row onto M4_APPLICABILITY_OBSERVED.

    Pure lookup over strings M4 produced. No condition is evaluated here, and
    ``row['condition']`` is deliberately never consulted -- only the
    ``condition_state`` M4 already derived from it.
    """
    if row.get("_coverage_status") == "UNSUPPORTED":
        return states.UNSUPPORTED_APPROVAL
    if row.get("verification_status") == "UNSUPPORTED":
        return states.UNSUPPORTED_APPROVAL
    if row.get("_engine_state") != "APPLICABLE":
        return states.UNRESOLVED_ENGINE_STATE

    condition_state = row.get("condition_state")
    if condition_state == "TRUE":
        return states.APPLICABLE_CONDITION_TRUE
    if condition_state == "FALSE":
        return states.NOT_APPLICABLE_CONDITION_FALSE
    # UNKNOWN, or absent. Unresolved is not false.
    return states.UNRESOLVED_CONDITION_UNKNOWN


def observation_from_row(row: Dict[str, Any]) -> M4Observation:
    source = row.get("source") or {}
    return M4Observation(
        requirement_id=row.get("requirement_id", ""),
        approval_id=row.get("_approval_id") or row.get("approval_id", ""),
        document_id=row.get("document_id", ""),
        obligation=row.get("obligation", ""),
        blocking=bool(row.get("blocking", False)),
        m4_verification_status=row.get("verification_status", ""),
        coverage_status=row.get("_coverage_status", ""),
        engine_state=row.get("_engine_state"),
        condition_state=row.get("condition_state"),
        condition_description=row.get("condition_description"),
        condition_trace=row.get("condition_trace") or [],
        source_authority=source.get("authority"),
        source_checklist_item=source.get("checklist_item"),
        source_url=source.get("url"),
    )


def requirement_match_for(applicability: str) -> Optional[str]:
    """The requirement_match forced by applicability, or None to let
    classification decide.

    Note the asymmetry, which is the point of the whole module: FALSE and
    UNSUPPORTED give NOT_APPLICABLE, while UNKNOWN gives INDETERMINATE.
    "We do not know whether this is required" is not "this is not required".
    """
    if applicability in (states.NOT_APPLICABLE_CONDITION_FALSE,
                         states.UNSUPPORTED_APPROVAL):
        return states.NOT_APPLICABLE
    if applicability in (states.UNRESOLVED_CONDITION_UNKNOWN,
                         states.UNRESOLVED_ENGINE_STATE):
        return states.INDETERMINATE
    return None


def disposition_reason_for(applicability: str) -> Optional[str]:
    return {
        states.NOT_APPLICABLE_CONDITION_FALSE: states.REASON_M4_NOT_APPLICABLE,
        states.UNRESOLVED_CONDITION_UNKNOWN: states.REASON_M4_UNRESOLVED,
        states.UNRESOLVED_ENGINE_STATE: states.REASON_M4_UNRESOLVED,
        states.UNSUPPORTED_APPROVAL: states.REASON_M4_UNSUPPORTED,
    }.get(applicability)
