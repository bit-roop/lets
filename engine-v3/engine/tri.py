"""
Three-valued logic (Kleene / SQL semantics).

The critical distinction: a missing fact is NOT a false fact.
Collapsing UNKNOWN to FALSE causes requirements to silently disappear,
which is the most dangerous failure mode a compliance engine can have.
"""

from enum import Enum


class Tri(Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"

    def __bool__(self):
        raise TypeError(
            "Tri must not be used in a boolean context — that is exactly "
            "the collapse this type exists to prevent. Compare explicitly."
        )


T, F, U = Tri.TRUE, Tri.FALSE, Tri.UNKNOWN


def tri_not(a: Tri) -> Tri:
    if a is U:
        return U
    return F if a is T else T


def tri_and(values) -> Tri:
    """FALSE dominates. UNKNOWN only survives if nothing is FALSE."""
    seen_unknown = False
    for v in values:
        if v is F:
            return F          # short-circuit: one false kills the conjunction
        if v is U:
            seen_unknown = True
    return U if seen_unknown else T


def tri_or(values) -> Tri:
    """TRUE dominates. UNKNOWN only survives if nothing is TRUE."""
    seen_unknown = False
    for v in values:
        if v is T:
            return T          # short-circuit
        if v is U:
            seen_unknown = True
    return U if seen_unknown else F


def from_bool(b: bool) -> Tri:
    return T if b else F
