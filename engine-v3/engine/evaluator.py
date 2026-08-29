"""
Condition evaluator — three-valued, with fact-level provenance.

Returns (Tri, trace) where trace records which facts were consulted,
what they held, and which were missing. The trace is what makes the
"why?" panel a render of data rather than a generated explanation.
"""

from datetime import date
from .tri import Tri, T, F, U, tri_and, tri_or, tri_not, from_bool


class MissingFact(Exception):
    pass


OPS = {
    ">":  lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<":  lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
    "intersects": lambda a, b: bool(set(a) & set(b)),
    "disjoint":   lambda a, b: not (set(a) & set(b)),
}


def evaluate(condition, facts, trace=None):
    """
    condition : nested {all|any|not|leaf}
    facts     : dict; a key that is absent OR explicitly None is UNKNOWN
    returns   : (Tri, trace_list)
    """
    if trace is None:
        trace = []

    if "all" in condition:
        results = [evaluate(c, facts, trace)[0] for c in condition["all"]]
        return tri_and(results), trace

    if "any" in condition:
        results = [evaluate(c, facts, trace)[0] for c in condition["any"]]
        return tri_or(results), trace

    if "not" in condition:
        inner, _ = evaluate(condition["not"], facts, trace)
        return tri_not(inner), trace

    # ── leaf ──
    fact_name = condition["fact"]
    op = condition["op"]
    target = condition["value"]

    if fact_name not in facts or facts[fact_name] is None:
        trace.append({
            "fact": fact_name, "value": None, "op": op, "target": target,
            "result": "UNKNOWN", "reason": "fact not provided",
        })
        return U, trace

    val = facts[fact_name]
    try:
        outcome = from_bool(OPS[op](val, target))
        result = outcome
        reason = f"{fact_name} ({val!r}) {op} {target!r}"
    except (TypeError, KeyError) as e:
        result = U
        reason = f"could not evaluate: {e}"

    trace.append({
        "fact": fact_name, "value": val, "op": op, "target": target,
        "result": result.value, "reason": reason,
    })
    return result, trace


# ─────────────────────────────────────────────────────────────
# Temporal rule selection
# ─────────────────────────────────────────────────────────────

def select_version(rule_versions, as_of: date):
    """
    Pick the rule version in force on `as_of`.
    An application filed 2026-03-15 is judged under the rules of that date,
    not today's. effective_to = None means 'still in force'.
    """
    candidates = []
    for rv in rule_versions:
        eff = rv["source"].get("effective_from")
        end = rv["source"].get("effective_to")
        start = date.fromisoformat(eff) if eff else date.min
        stop = date.fromisoformat(end) if end else date.max
        if start <= as_of <= stop:
            candidates.append((start, rv))
    if not candidates:
        return None
    # latest effective_from wins if several overlap
    return max(candidates, key=lambda x: x[0])[1]
