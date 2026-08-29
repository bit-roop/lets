"""
Derived facts.

A derived fact is a fact produced by a rule rather than supplied by the
applicant. It is a first-class object carrying full provenance, never a
bare dictionary mutation.

Derivation operations come from a fixed registry. Regulatory JSON never
contains executable expressions; an unsupported operation raises rather
than executing anything.
"""

import math
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


VALUE_TYPES = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "enum": lambda v: isinstance(v, str),
    "list": lambda v: isinstance(v, list),
}


class DerivationError(Exception):
    """Raised for malformed or unsupported derivation specs."""


@dataclass
class DerivedFact:
    fact: str
    value: Any
    value_type: str
    rule_id: str
    rule_version: int
    source: dict
    verification_status: str
    input_facts: list = field(default_factory=list)
    derived_in_pass: int = 0
    derived_at: str = ""
    operation: str = ""

    def signature(self):
        """Identity for repeated-derivation detection."""
        return (self.rule_id, self.rule_version, self.fact, repr(self.value))

    def as_dict(self):
        return asdict(self)


@dataclass
class IndeterminateDerivation:
    fact: str
    rule_id: str
    rule_version: int
    source: dict
    verification_status: str
    missing_facts: list
    reason: str
    derived_in_pass: int = 0

    def as_dict(self):
        return asdict(self)


@dataclass
class DerivedFactConflict:
    fact: str
    competing: list          # list of DerivedFact dicts
    derived_in_pass: int = 0

    def as_dict(self):
        return {
            "fact": self.fact,
            "derived_in_pass": self.derived_in_pass,
            "competing_values": sorted({repr(c["value"]) for c in self.competing}),
            "competing_derivations": self.competing,
            "resolution": "NONE",
            "note": ("The engine does not choose between contradictory "
                     "derivations. The fact is withheld from downstream rules, "
                     "so consumers evaluate to UNKNOWN."),
        }


# ─────────────────────────────────────────────────────────────
# Derivation operations — fixed registry, no code execution
# ─────────────────────────────────────────────────────────────

def _op_constant(spec, facts):
    return spec["value"], []


def _op_copy_fact(spec, facts):
    src = spec["from_fact"]
    if src not in facts or facts[src] is None:
        return None, [src]
    return facts[src], []


def _op_ceil_divide(spec, facts):
    src = spec["from_fact"]
    if src not in facts or facts[src] is None:
        return None, [src]
    return math.ceil(facts[src] / spec["divisor"]), []


def _op_floor_divide(spec, facts):
    src = spec["from_fact"]
    if src not in facts or facts[src] is None:
        return None, [src]
    return math.floor(facts[src] / spec["divisor"]), []


def _op_sum(spec, facts):
    missing = [f for f in spec["from_facts"]
               if f not in facts or facts[f] is None]
    if missing:
        return None, missing
    return sum(facts[f] for f in spec["from_facts"]), []


def _op_max(spec, facts):
    missing = [f for f in spec["from_facts"]
               if f not in facts or facts[f] is None]
    if missing:
        return None, missing
    return max(facts[f] for f in spec["from_facts"]), []


def _op_min(spec, facts):
    missing = [f for f in spec["from_facts"]
               if f not in facts or facts[f] is None]
    if missing:
        return None, missing
    return min(facts[f] for f in spec["from_facts"]), []


OPERATIONS = {
    "constant":     (_op_constant,     {"value"}),
    "copy_fact":    (_op_copy_fact,    {"from_fact"}),
    "ceil_divide":  (_op_ceil_divide,  {"from_fact", "divisor"}),
    "floor_divide": (_op_floor_divide, {"from_fact", "divisor"}),
    "sum":          (_op_sum,          {"from_facts"}),
    "max":          (_op_max,          {"from_facts"}),
    "min":          (_op_min,          {"from_facts"}),
}


def input_facts_of(spec):
    """Which facts a derivation spec consumes. Used for static cycle detection."""
    if "from_fact" in spec:
        return [spec["from_fact"]]
    if "from_facts" in spec:
        return list(spec["from_facts"])
    return []


def execute(spec, facts, rule, pass_no):
    """
    Run one derivation spec.

    Returns DerivedFact | IndeterminateDerivation.
    Raises DerivationError for unsupported or malformed specs.
    """
    op = spec.get("operation")
    if op not in OPERATIONS:
        raise DerivationError(
            f"unsupported derivation operation {op!r}. "
            f"Permitted: {sorted(OPERATIONS)}. Expressions are never evaluated."
        )

    fn, required = OPERATIONS[op]
    missing_keys = required - set(spec)
    if missing_keys:
        raise DerivationError(
            f"derivation {op!r} missing required key(s): {sorted(missing_keys)}")

    fact_name = spec.get("fact")
    if not fact_name:
        raise DerivationError("derivation spec has no 'fact' name")

    value_type = spec.get("value_type")
    if value_type not in VALUE_TYPES:
        raise DerivationError(
            f"invalid value_type {value_type!r}. Permitted: {sorted(VALUE_TYPES)}")

    value, missing = fn(spec, facts)

    provenance = {
        "source": rule.get("source", {}),
        "verification_status": rule.get("verification_status", "UNVERIFIED"),
    }

    if missing:
        return IndeterminateDerivation(
            fact=fact_name,
            rule_id=rule["rule_id"],
            rule_version=rule["version"],
            source=provenance["source"],
            verification_status=provenance["verification_status"],
            missing_facts=sorted(missing),
            reason=(f"Cannot derive {fact_name}: input fact(s) "
                    f"{', '.join(sorted(missing))} not supplied."),
            derived_in_pass=pass_no,
        )

    if not VALUE_TYPES[value_type](value):
        raise DerivationError(
            f"derived value {value!r} for {fact_name!r} does not match "
            f"declared value_type {value_type!r}")

    if value_type == "enum":
        allowed = spec.get("enum_values")
        if allowed is None:
            raise DerivationError(
                f"enum derivation for {fact_name!r} must declare enum_values")
        if value not in allowed:
            raise DerivationError(
                f"derived enum value {value!r} not in declared enum_values {allowed}")

    return DerivedFact(
        fact=fact_name,
        value=value,
        value_type=value_type,
        rule_id=rule["rule_id"],
        rule_version=rule["version"],
        source=provenance["source"],
        verification_status=provenance["verification_status"],
        input_facts=input_facts_of(spec),
        derived_in_pass=pass_no,
        derived_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        operation=op,
    )
