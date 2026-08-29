"""
Quantity computation.

Regulatory JSON must never contain executable expressions. Quantities are
declared structurally and dispatched through a fixed table. An unknown
operation is an error, not an eval().
"""

import math


def _ceil_divide(facts, spec):
    val = facts.get(spec["fact"])
    if val is None:
        return None, [spec["fact"]]
    return math.ceil(val / spec["divisor"]), []


def _floor_divide(facts, spec):
    val = facts.get(spec["fact"])
    if val is None:
        return None, [spec["fact"]]
    return math.floor(val / spec["divisor"]), []


def _fixed(facts, spec):
    return spec["value"], []


def _per_unit_min(facts, spec):
    """ceil(fact/divisor) but never below `minimum`."""
    val = facts.get(spec["fact"])
    if val is None:
        return None, [spec["fact"]]
    return max(math.ceil(val / spec["divisor"]), spec.get("minimum", 0)), []


OPERATIONS = {
    "ceil_divide": _ceil_divide,
    "floor_divide": _floor_divide,
    "fixed": _fixed,
    "per_unit_min": _per_unit_min,
}


def compute(spec, facts):
    """
    spec e.g. {"operation": "ceil_divide", "fact": "food_handlers", "divisor": 25}
    returns {"value": int|None, "missing_facts": [...], "formula": "..."}
    """
    if not spec:
        return None
    op = spec.get("operation")
    if op not in OPERATIONS:
        raise ValueError(
            f"unknown quantity operation {op!r}. "
            f"Permitted: {sorted(OPERATIONS)}. Expressions are not evaluated."
        )
    value, missing = OPERATIONS[op](facts, spec)
    return {
        "value": value,
        "missing_facts": missing,
        "formula": _describe(spec),
    }


def _describe(spec):
    op = spec["operation"]
    if op == "ceil_divide":
        return f"ceil({spec['fact']} / {spec['divisor']})"
    if op == "floor_divide":
        return f"floor({spec['fact']} / {spec['divisor']})"
    if op == "per_unit_min":
        return (f"max(ceil({spec['fact']} / {spec['divisor']}), "
                f"{spec.get('minimum', 0)})")
    if op == "fixed":
        return str(spec["value"])
    return op
