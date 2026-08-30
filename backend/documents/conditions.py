"""Constrained adapter around engine-v3's read-only condition evaluator."""

from backend.config import derive  # initializes the protected engine import path
from engine.evaluator import evaluate


def evaluate_condition(condition, facts):
    """Return TRUE/FALSE/UNKNOWN without changing engine applicability."""
    if not condition:
        return "TRUE", []
    result, trace = evaluate(condition, dict(facts or {}))
    return result.name, trace
