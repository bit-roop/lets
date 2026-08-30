"""Deterministic checklist/readiness computation."""

from .conditions import evaluate_condition
from .models import Readiness


def _submission_satisfies(submission, by_id, seen=None):
    """Only VALID submissions satisfy; reuse must point to a valid submission."""
    if submission is None:
        return False
    if seen is None:
        seen = set()
    if submission.submission_id in seen:
        return False
    seen.add(submission.submission_id)
    if submission.validation and submission.validation.get("status") in {"FORMAT_INVALID", "INVALID"}:
        return False
    if submission.state == "VALID":
        return True
    if submission.state == "REUSED_FROM":
        return _submission_satisfies(by_id.get(submission.reused_from), by_id, seen)
    return False


def compute_readiness(approval_id, coverage_status, requirements, submissions, facts, approval_state="APPLICABLE"):
    if coverage_status == "UNSUPPORTED":
        return Readiness(approval_id, "UNSUPPORTED", 0, 0, reasons=["No authoritative checklist is available."])
    if approval_state == "NOT_APPLICABLE":
        return Readiness(approval_id, "INDETERMINATE", 0, 0, reasons=["Applicability was not established by the engine."])
    if approval_state in {"UNKNOWN", "CONFLICT"}:
        return Readiness(approval_id, "INDETERMINATE", 0, 0, reasons=[f"Engine applicability state is {approval_state}."])
    provided = {s.document_id: s for s in submissions}
    by_id = {s.submission_id: s for s in submissions}
    missing, indeterminate, unsupported, supporting_missing = [], [], [], []
    mandatory_total = mandatory_satisfied = 0
    for req in requirements:
        if req.verification_status == "UNSUPPORTED":
            unsupported.append(req.requirement_id)
            continue
        condition_state, _ = evaluate_condition(req.condition, facts)
        if condition_state == "FALSE":
            continue
        if condition_state == "UNKNOWN":
            indeterminate.append(req.requirement_id)
            continue
        is_satisfied = req.document_id in provided and _submission_satisfies(provided[req.document_id], by_id)
        if req.obligation == "MANDATORY" or req.blocking:
            mandatory_total += 1
            if is_satisfied:
                mandatory_satisfied += 1
            else:
                missing.append(req.requirement_id)
        elif not is_satisfied:
            supporting_missing.append(req.requirement_id)
    if indeterminate:
        status = "INDETERMINATE"
    elif missing:
        status = "INCOMPLETE"
    else:
        status = "READY"
    reasons = []
    if missing: reasons.append("Known mandatory evidence is missing or unusable.")
    if indeterminate: reasons.append("One or more conditional requirements need facts that are not supplied.")
    if unsupported: reasons.append("Some catalogue items have no authoritative checklist and remain unsupported.")
    return Readiness(approval_id, status, mandatory_total, mandatory_satisfied, missing, indeterminate, unsupported, supporting_missing, reasons)
