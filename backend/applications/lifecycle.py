"""Slice 4: prototype department lifecycle rules.

This module is a pure state machine over the *already persisted* application
case created in Slice 3. It contains no regulatory reasoning of any kind.

Explicitly out of scope here, and deliberately not imported anywhere in this
module or in ``lifecycle_service``:

  * engine-v3 evaluation (``evaluate_facts``)
  * M3 workflow construction (``build_workflow_for_facts``)
  * M4 requirement or readiness evaluation
  * M4 condition evaluation
  * M5 document extraction or classification

Applicability, readiness and verification findings are read from the stored
case snapshot exactly as upstream established them. Nothing in Slice 4 may
change them.

Nothing in this module represents a real government decision. A GRANTED
approval here means an officer pressed a button in a simulation.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Optional

# --- Departments simulated by the prototype ---------------------------------
#
# The department code is read from the approval snapshot the applicant filed,
# which itself carries the value the approval catalogue already recorded. It is
# never inferred, guessed, or derived from the approval id.

DEPARTMENT_DISH = "DISH"
DEPARTMENT_FSSAI = "FSSAI"

PROTOTYPE_DEPARTMENTS: FrozenSet[str] = frozenset({DEPARTMENT_DISH, DEPARTMENT_FSSAI})

DEPARTMENT_LABELS: Dict[str, str] = {
    DEPARTMENT_DISH: "Directorate of Industrial Safety and Health (Prototype Simulation)",
    DEPARTMENT_FSSAI: "Food Safety and Standards Authority (Prototype Simulation)",
}

# --- Approval lifecycle -----------------------------------------------------

APPROVAL_SUBMITTED = "SUBMITTED"
APPROVAL_IN_SCRUTINY = "IN_SCRUTINY"
APPROVAL_QUERY_PENDING = "QUERY_PENDING"
APPROVAL_GRANTED = "GRANTED"
APPROVAL_REJECTED = "REJECTED"

APPROVAL_STATES: FrozenSet[str] = frozenset({
    APPROVAL_SUBMITTED,
    APPROVAL_IN_SCRUTINY,
    APPROVAL_QUERY_PENDING,
    APPROVAL_GRANTED,
    APPROVAL_REJECTED,
})

APPROVAL_TERMINAL_STATES: FrozenSet[str] = frozenset({APPROVAL_GRANTED, APPROVAL_REJECTED})

# Allowed approval transitions. Grant and reject are reachable only from
# IN_SCRUTINY, so an officer cannot decide a case they never opened, and cannot
# decide one while a query is outstanding.
APPROVAL_TRANSITIONS: Dict[str, FrozenSet[str]] = {
    APPROVAL_SUBMITTED: frozenset({APPROVAL_IN_SCRUTINY}),
    APPROVAL_IN_SCRUTINY: frozenset({APPROVAL_QUERY_PENDING, APPROVAL_GRANTED, APPROVAL_REJECTED}),
    APPROVAL_QUERY_PENDING: frozenset({APPROVAL_IN_SCRUTINY}),
    APPROVAL_GRANTED: frozenset(),
    APPROVAL_REJECTED: frozenset(),
}

# --- Application lifecycle --------------------------------------------------

APPLICATION_SUBMITTED = "SUBMITTED"
APPLICATION_UNDER_REVIEW = "UNDER_REVIEW"
APPLICATION_QUERY_RAISED = "QUERY_RAISED"
APPLICATION_RESPONDED = "RESPONDED"
APPLICATION_GRANTED = "GRANTED"
APPLICATION_REJECTED = "REJECTED"

APPLICATION_STATES: FrozenSet[str] = frozenset({
    APPLICATION_SUBMITTED,
    APPLICATION_UNDER_REVIEW,
    APPLICATION_QUERY_RAISED,
    APPLICATION_RESPONDED,
    APPLICATION_GRANTED,
    APPLICATION_REJECTED,
})

# --- Query lifecycle --------------------------------------------------------

QUERY_OPEN = "OPEN"
QUERY_RESPONDED = "RESPONDED"
QUERY_RESOLVED = "RESOLVED"

QUERY_STATES: FrozenSet[str] = frozenset({QUERY_OPEN, QUERY_RESPONDED, QUERY_RESOLVED})

QUERY_TRANSITIONS: Dict[str, FrozenSet[str]] = {
    QUERY_OPEN: frozenset({QUERY_RESPONDED}),
    QUERY_RESPONDED: frozenset({QUERY_RESOLVED}),
    QUERY_RESOLVED: frozenset(),
}

# --- Event types ------------------------------------------------------------

EVENT_REVIEW_STARTED = "REVIEW_STARTED"
EVENT_QUERY_RAISED = "QUERY_RAISED"
EVENT_QUERY_RESPONDED = "QUERY_RESPONDED"
EVENT_QUERY_RESOLVED = "QUERY_RESOLVED"
EVENT_APPROVAL_GRANTED = "APPROVAL_GRANTED"
EVENT_APPROVAL_REJECTED = "APPROVAL_REJECTED"

# Wording used anywhere a decision is surfaced. A prototype decision is never
# described as a government act.
DECISION_LABELS: Dict[str, str] = {
    APPROVAL_GRANTED: "Granted in Simulation",
    APPROVAL_REJECTED: "Rejected in Simulation",
}

MAX_TEXT_LENGTH = 2000
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# --- Errors -----------------------------------------------------------------


class LifecycleError(Exception):
    """Base class for lifecycle failures that are safe to report to a client."""


class LifecycleNotFound(LifecycleError):
    """A referenced application, approval, or query does not exist."""


class LifecycleValidation(LifecycleError):
    """The submitted payload is structurally unacceptable."""


class LifecycleForbidden(LifecycleError):
    """A department attempted to act on an approval it does not own."""


class InvalidTransition(LifecycleError):
    """The requested state change is not permitted from the current state."""


# --- Helpers ----------------------------------------------------------------


def normalise_department(value: Optional[str]) -> str:
    """Normalise a department code for comparison.

    The value originates from the stored approval snapshot. Anything unknown is
    reported as ``UNASSIGNED`` rather than being mapped onto a real department.
    """
    if not value or not str(value).strip():
        return "UNASSIGNED"
    return str(value).strip().upper()


def is_prototype_department(value: Optional[str]) -> bool:
    return normalise_department(value) in PROTOTYPE_DEPARTMENTS


def department_of_approval(approval: Mapping[str, Any]) -> str:
    """Department that owns an approval, read from the stored snapshot only."""
    return normalise_department(approval.get("department"))


def reviewable_approvals(approvals: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Approvals that one of the two simulated departments can act on."""
    return [dict(a) for a in approvals if is_prototype_department(a.get("department"))]


def assert_approval_transition(current: str, target: str) -> None:
    if current not in APPROVAL_STATES:
        raise InvalidTransition(f"Unrecognised approval state '{current}'.")
    if target not in APPROVAL_STATES:
        raise InvalidTransition(f"Unrecognised target approval state '{target}'.")
    if target not in APPROVAL_TRANSITIONS[current]:
        raise InvalidTransition(
            f"An approval in state '{current}' cannot move to '{target}'."
        )


def assert_query_transition(current: str, target: str) -> None:
    if current not in QUERY_STATES:
        raise InvalidTransition(f"Unrecognised query state '{current}'.")
    if target not in QUERY_STATES:
        raise InvalidTransition(f"Unrecognised target query state '{target}'.")
    if target not in QUERY_TRANSITIONS[current]:
        raise InvalidTransition(
            f"A query in state '{current}' cannot move to '{target}'."
        )


def validate_text(value: Optional[str], field: str, required: bool = True) -> str:
    text = (value or "").strip()
    if required and not text:
        raise LifecycleValidation(f"{field} is required.")
    if len(text) > MAX_TEXT_LENGTH:
        raise LifecycleValidation(f"{field} exceeds the maximum length of {MAX_TEXT_LENGTH} characters.")
    return text


def validate_deadline(value: Optional[str]) -> str:
    """Deadlines are plain ISO dates. No SLA arithmetic happens here.

    Slice 4 never computes or re-derives an SLA. The officer types a date; M3's
    established SLA figures are shown alongside it for context only.
    """
    text = (value or "").strip()
    if not text:
        raise LifecycleValidation("A query deadline date is required.")
    if not _ISO_DATE.match(text):
        raise LifecycleValidation("Deadline must be an ISO date in YYYY-MM-DD form.")
    try:
        date.fromisoformat(text)
    except ValueError:
        raise LifecycleValidation("Deadline is not a valid calendar date.")
    return text


def derive_application_status(
    approval_states: Mapping[str, str],
    queries: Iterable[Mapping[str, Any]],
) -> str:
    """Aggregate the application status from persisted approval and query rows.

    This reads persisted lifecycle rows only. It does not consult the engine,
    the workflow, M4 readiness, or M5 findings, and it cannot change any of
    them.

    Only approvals owned by a simulated department are considered, because no
    officer view exists for the others; treating those as permanently
    outstanding would make GRANTED unreachable and would misrepresent the
    prototype's scope.
    """
    states = [s for s in approval_states.values() if s in APPROVAL_STATES]
    query_states = [str(q.get("status")) for q in queries]

    if QUERY_OPEN in query_states:
        return APPLICATION_QUERY_RAISED
    if QUERY_RESPONDED in query_states:
        return APPLICATION_RESPONDED
    if not states:
        return APPLICATION_SUBMITTED
    if all(s == APPROVAL_GRANTED for s in states):
        return APPLICATION_GRANTED
    if all(s in APPROVAL_TERMINAL_STATES for s in states):
        # Every reviewable approval is decided and at least one was refused.
        return APPLICATION_REJECTED
    if any(s != APPROVAL_SUBMITTED for s in states):
        return APPLICATION_UNDER_REVIEW
    return APPLICATION_SUBMITTED


