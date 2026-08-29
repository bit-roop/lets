"""
Requirement-level resolution.

Three-valued Kleene logic governs CONDITION evaluation.
Requirement aggregation has DIFFERENT semantics and lives here.

The distinction that matters: there are two kinds of negative evidence.

  ACTIVE EXCLUSION   a rule fired TRUE with excludes:[R]
                     -> positive evidence that R does not apply
                     -> definitive; outranks an indeterminate requires

  ABSENCE OF TRIGGER a rule with requires:[R] evaluated FALSE
                     -> merely nothing fired
                     -> weak; does NOT outrank an indeterminate requires

Collapsing these into one "NOT_APPLICABLE" bucket is the bug this
module exists to prevent.
"""

from enum import Enum


class State(Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


class Evidence:
    """One rule's contribution to one requirement."""

    POSITIVE_DEFINITE = "POSITIVE_DEFINITE"        # requires, TRUE
    POSITIVE_INDETERMINATE = "POSITIVE_INDETERMINATE"  # requires, UNKNOWN
    ABSENCE_OF_TRIGGER = "ABSENCE_OF_TRIGGER"      # requires, FALSE
    ACTIVE_EXCLUSION = "ACTIVE_EXCLUSION"          # excludes, TRUE
    EXCLUSION_INDETERMINATE = "EXCLUSION_INDETERMINATE"  # excludes, UNKNOWN

    def __init__(self, kind, rule_evidence):
        self.kind = kind
        self.rule = rule_evidence

    @property
    def missing_facts(self):
        return sorted({
            t["fact"] for t in self.rule.get("facts_used", [])
            if t["result"] == "UNKNOWN"
        })

    def as_dict(self):
        d = dict(self.rule)
        d["evidence_kind"] = self.kind
        return d


def classify(effect_key: str, condition_result: str) -> str:
    """Map (effect kind, condition outcome) onto an evidence kind."""
    if effect_key == "requires":
        return {
            "TRUE": Evidence.POSITIVE_DEFINITE,
            "UNKNOWN": Evidence.POSITIVE_INDETERMINATE,
            "FALSE": Evidence.ABSENCE_OF_TRIGGER,
        }[condition_result]
    if effect_key == "excludes":
        return {
            "TRUE": Evidence.ACTIVE_EXCLUSION,
            "UNKNOWN": Evidence.EXCLUSION_INDETERMINATE,
            "FALSE": None,   # an exclusion that did not fire says nothing
        }[condition_result]
    raise ValueError(f"unknown effect key: {effect_key}")


def resolve(evidences):
    """
    Resolve one requirement from all evidence bearing on it.

    Precedence, in order:
      1. POSITIVE_DEFINITE + ACTIVE_EXCLUSION      -> CONFLICT
      2. ACTIVE_EXCLUSION (no positive definite)   -> NOT_APPLICABLE
      3. POSITIVE_DEFINITE                         -> APPLICABLE
      4. any indeterminate evidence                -> UNKNOWN
      5. only ABSENCE_OF_TRIGGER                   -> NOT_APPLICABLE

    Returns (State, reasons, warnings).
    """
    by_kind = {}
    for e in evidences:
        by_kind.setdefault(e.kind, []).append(e)

    pos_def = by_kind.get(Evidence.POSITIVE_DEFINITE, [])
    pos_ind = by_kind.get(Evidence.POSITIVE_INDETERMINATE, [])
    excl_act = by_kind.get(Evidence.ACTIVE_EXCLUSION, [])
    excl_ind = by_kind.get(Evidence.EXCLUSION_INDETERMINATE, [])
    absence = by_kind.get(Evidence.ABSENCE_OF_TRIGGER, [])

    warnings = []

    # 1 — contradiction between definitive rules
    if pos_def and excl_act:
        return State.CONFLICT, pos_def + excl_act, [{
            "type": "RULE_CONTRADICTION",
            "severity": "error",
            "requiring_rules": [e.rule["rule_id"] for e in pos_def],
            "excluding_rules": [e.rule["rule_id"] for e in excl_act],
            "message": (
                "Rules contradict: "
                f"{', '.join(e.rule['rule_id'] for e in pos_def)} require this "
                f"while {', '.join(e.rule['rule_id'] for e in excl_act)} exclude it. "
                "The engine will not choose between them."
            ),
        }]

    # 2 — active exclusion is definitive; it outranks an indeterminate requires.
    #     THIS is the case blanket "UNKNOWN wins" got wrong.
    if excl_act:
        if pos_ind:
            warnings.append({
                "type": "EXCLUSION_OVERRODE_INDETERMINATE",
                "severity": "info",
                "message": (
                    "An indeterminate requirement was overridden by a definitive "
                    f"exclusion ({', '.join(e.rule['rule_id'] for e in excl_act)}). "
                    "Missing facts were not needed."
                ),
            })
        return State.NOT_APPLICABLE, excl_act, warnings

    # 3 — required, with no active exclusion
    if pos_def:
        if excl_ind:
            warnings.append({
                "type": "INDETERMINATE_EXCLUSION",
                "severity": "warning",
                "missing_facts": sorted({f for e in excl_ind for f in e.missing_facts}),
                "message": (
                    "A rule that could exclude this requirement is indeterminate. "
                    "Reported as APPLICABLE (the conservative direction), but the "
                    "requirement may be lifted once the missing facts are supplied."
                ),
            })
        return State.APPLICABLE, pos_def, warnings

    # 4 — nothing definitive, something indeterminate
    if pos_ind or excl_ind:
        ind = pos_ind + excl_ind
        missing = sorted({f for e in ind for f in e.missing_facts})
        warnings.append({
            "type": "INSUFFICIENT_FACTS",
            "severity": "warning",
            "missing_facts": missing,
            "message": (
                "Cannot determine applicability. Missing: "
                + ", ".join(missing) if missing else
                "Cannot determine applicability."
            ),
        })
        return State.UNKNOWN, ind, warnings

    # 5 — only absence of trigger
    return State.NOT_APPLICABLE, absence, warnings
