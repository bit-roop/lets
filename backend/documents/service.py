"""M4 orchestration downstream of engine-v3 and M3."""

import copy

from backend.engine_adapter import evaluate_facts, build_workflow_for_facts
from .conditions import evaluate_condition
from .models import ReuseLink
from .readiness import compute_readiness
from .registry import get_document_registry
from .submissions import get_submission_store
from .validators import validate_structured_fields


def _state_map(evaluation):
    return {item["requirement_id"]: item["state"] for key in ("applicable", "not_applicable", "unknown", "conflict") for item in evaluation.get(key, [])}


def _engine_and_workflow(facts, as_of, workflow_aware):
    if workflow_aware:
        combined = build_workflow_for_facts(facts, as_of=as_of, include_provisional=True)
        return combined["evaluation"], combined["workflow"]
    return evaluate_facts(facts, as_of=as_of), None


def requirements_for_application(facts=None, as_of=None, approval_ids=None, include_provisional=True, workflow_aware=False):
    facts = dict(facts or {})
    registry = get_document_registry()
    evaluation, workflow = _engine_and_workflow(facts, as_of, workflow_aware)
    states = _state_map(evaluation) if evaluation else {}
    selected = set(approval_ids) if approval_ids else set(registry.coverage_raw)
    output = []
    for coverage in registry.coverage(selected):
        reqs = registry.requirements([coverage.approval_id])
        rows = []
        for req in reqs:
            condition_state, trace = evaluate_condition(req.condition, facts)
            row = req.as_dict()
            row["source"] = req.source.as_dict()
            row["condition_state"] = condition_state
            row["condition_trace"] = trace
            rows.append(row)
        state = states.get(coverage.approval_id)
        output.append({"approval_id": coverage.approval_id, "engine_state": state, "coverage": coverage.as_dict(), "requirements": rows})
    result = {"approvals": output, "engine_evaluation": evaluation}
    if workflow is not None:
        result["workflow"] = copy.deepcopy(workflow)
    return result


def readiness_for_application(application_id, facts=None, as_of=None, approval_ids=None, include_provisional=True, workflow_aware=False):
    facts = dict(facts or {})
    registry = get_document_registry()
    evaluation, workflow = _engine_and_workflow(facts, as_of, workflow_aware)
    states = _state_map(evaluation)
    submissions = get_submission_store().for_application(application_id)
    rows = []
    selected = set(approval_ids) if approval_ids else set(registry.coverage_raw)
    committed_approval_ids = None
    if workflow is not None and workflow.get("schedule"):
        committed_requirement_ids = set(workflow["schedule"].get("nodes", {}))
        committed_approval_ids = {
            req.approval_id for req in registry.requirements()
            if req.approval_id in committed_requirement_ids
        }
    for coverage in registry.coverage(selected):
        reqs = registry.requirements([coverage.approval_id])
        if committed_approval_ids is not None and coverage.approval_id not in committed_approval_ids and coverage.status != "UNSUPPORTED":
            rows.append({"approval_id": coverage.approval_id, "status": "INDETERMINATE", "mandatory_total": 0,
                         "mandatory_satisfied": 0, "missing_requirement_ids": [],
                         "indeterminate_requirement_ids": [], "unsupported_requirement_ids": [],
                         "supporting_missing_requirement_ids": [],
                         "reasons": ["Approval is not in the committed M3 schedule scope."]})
            continue
        ready = compute_readiness(coverage.approval_id, coverage.status, reqs, submissions, facts, states.get(coverage.approval_id, "UNKNOWN"))
        rows.append(ready.as_dict())
    result = {"application_id": application_id, "readiness": rows, "submissions": [s.as_dict() for s in submissions]}
    if workflow is not None:
        result["workflow"] = copy.deepcopy(workflow)
    return result


def reuse_links(application_id, approval_ids=None):
    registry = get_document_registry()
    submissions = get_submission_store().for_application(application_id)
    selected = set(approval_ids) if approval_ids else None
    links = []
    for req in registry.requirements(selected):
        spec = registry.spec(req.document_id)
        if spec.reusable:
            for sub in submissions:
                if sub.document_id == req.document_id:
                    links.append(ReuseLink(sub.submission_id, req.requirement_id, req.document_id, "exact_document_spec_id", "REUSED_FROM").as_dict())
    return links
