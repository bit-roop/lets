"""
Dependency admission policy.

The ONLY module permitted to interpret dependency_type. Every other module
asks this one whether an edge constrains scheduling.

SCHEDULING_ADMITTED is pinned to engine-v3's CRITICAL_PATH_TYPES. The
workflow layer must never widen it; promoting a dependency type is a
regulatory decision made by editing dependencies.json under domain review,
not a scheduler flag.
"""

from engine.validate_data import CRITICAL_PATH_TYPES

SCHEDULING_ADMITTED = frozenset(CRITICAL_PATH_TYPES)

KNOWN_DEPENDENCY_TYPES = frozenset({
    "LEGAL", "OPERATIONAL", "PROCESS", "RECOMMENDED", "UNVERIFIED",
})

ORIGIN_DEPENDS_ON = "depends_on"
ORIGIN_CANDIDATE = "candidate_dependencies"

_REASONS = {
    "LEGAL": "Statute or rule conditions the dependent requirement on this one.",
    "OPERATIONAL": "Physically impossible to complete the dependent requirement first.",
    "PROCESS": "Department practice, not a legal precondition. Advisory only.",
    "RECOMMENDED": "Sensible ordering, not binding. Advisory only.",
    "UNVERIFIED": "Asserted but unconfirmed. Never admitted to scheduling.",
}


def is_admitted(dependency_type, origin):
    """
    Does this edge constrain scheduling?

    candidate_dependencies are NEVER admitted regardless of their declared
    type. They are relationships explicitly recorded as retracted or
    unconfirmed; honouring one would produce a critical path that is
    elegant and legally wrong.
    """
    if origin == ORIGIN_CANDIDATE:
        return False
    return dependency_type in SCHEDULING_ADMITTED


def admission_reason(dependency_type, origin, admitted):
    if origin == ORIGIN_CANDIDATE:
        return ("Recorded in candidate_dependencies. Never admitted to "
                "scheduling regardless of declared dependency_type.")
    if dependency_type not in KNOWN_DEPENDENCY_TYPES:
        return (f"Unrecognised dependency_type {dependency_type!r}. "
                "Not admitted to scheduling.")
    base = _REASONS[dependency_type]
    if admitted:
        return f"Admitted to scheduling. {base}"
    return f"Not admitted to scheduling. {base}"


def schedule_confidence(admitted_edges):
    """
    Mirrors engine-v3's rule-level confidence derivation: the weakest
    admitted edge governs. An admitted edge can never raise confidence
    above the verification status of its own basis.
    """
    if not admitted_edges:
        return "not_applicable", (
            "No admitted scheduling dependencies. Every requirement is "
            "independently startable; ordering is unconstrained by the "
            "regulatory data currently recorded.")

    statuses = {e.verification_status for e in admitted_edges}
    if "UNVERIFIED" in statuses:
        weakest = "UNVERIFIED"
        level = "low"
    elif "SECONDARY" in statuses:
        weakest = "SECONDARY"
        level = "medium"
    else:
        weakest = "VERIFIED"
        level = "high"

    culprits = sorted(
        f"{e.to_id}<-{e.from_id}"
        for e in admitted_edges if e.verification_status == weakest)
    return level, (
        f"Weakest admitted scheduling dependency has verification_status "
        f"{weakest}: {', '.join(culprits)}.")
