"""
Workflow orchestration.

The only module the API layer calls. Owns the committed/provisional split
and the human-readable explanation strings the UI renders.

Contract invariants enforced here:
  - the committed schedule contains ONLY APPLICABLE requirements
  - UNKNOWN requirements appear ONLY in the provisional schedule
  - both schedules carry an explicit label and scope_note so they cannot
    be confused for one another
"""

import copy

from .errors import CyclicGraphError
from .graph import build_graph, find_cycles
from .models import (
    WorkflowResult, warning,
    INCLUSION_SCHEDULED, INCLUSION_PROVISIONAL,
    SLA_UNSPECIFIED, SLA_INVALID, DURATION_UNIT,
)
from .scheduler import compute_schedule, rank_blockers

WORKFLOW_VERSION = "1.0.0"


def build_workflow(engine_result, catalogue=None, as_of=None,
                   include_provisional=True, include_candidate_edges=True):
    """
    Build a workflow view over an engine-v3 derive() result.

    The engine result is deep-copied on entry; nothing this module does can
    reach back into the caller's object.
    """
    engine_result = copy.deepcopy(engine_result)
    catalogue = copy.deepcopy(catalogue) if catalogue else {}

    graph = build_graph(engine_result, catalogue)
    warnings = list(graph.warnings)

    if not include_candidate_edges:
        graph.edges = [e for e in graph.edges if e.origin != "candidate_dependencies"]

    cycles = find_cycles(graph)
    committed = provisional = delta = None

    if cycles:
        warnings.append(warning(
            "WORKFLOW_CYCLE", "error",
            "The admitted dependency graph contains a cycle, so no valid "
            "ordering exists. No schedule has been produced. Cycles are never "
            "broken automatically: choosing an edge to ignore would be an "
            "arbitrary decision about a legal precondition.",
            cycles=cycles))
    else:
        try:
            committed, w = compute_schedule(
                graph, {INCLUSION_SCHEDULED}, "COMMITTED")
            warnings.extend(w)

            if include_provisional:
                provisional, w = compute_schedule(
                    graph, {INCLUSION_SCHEDULED, INCLUSION_PROVISIONAL},
                    "PROVISIONAL")
                warnings.extend(w)
                delta, dw = _provisional_delta(graph, committed, provisional)
                warnings.extend(dw)
        except CyclicGraphError as exc:
            cycles = exc.cycles
            committed = provisional = delta = None
            warnings.append(warning(
                "WORKFLOW_CYCLE", "error", str(exc), cycles=cycles))

    diagnostics = dict(graph.diagnostics)
    if committed:
        diagnostics["critical_path_count"] = len(committed.critical_paths)
        diagnostics["top_blockers"] = rank_blockers(committed, graph)

    severity_rank = {"error": 0, "warning": 1, "info": 2}
    warnings.sort(key=lambda w: (severity_rank.get(w["severity"], 3), w["type"]))

    return WorkflowResult(
        workflow_version=WORKFLOW_VERSION,
        generated_for={
            "as_of": as_of.isoformat() if hasattr(as_of, "isoformat") else as_of,
            "duration_unit": DURATION_UNIT,
            "duration_unit_note": (
                "Durations are expressed in the catalogue's own sla_days units. "
                "The regulatory data does not state whether these are working "
                "or calendar days, so no calendar conversion is performed and "
                "no dates are produced."),
            "engine_summary": engine_result.get("summary", {}),
        },
        nodes=graph.nodes,
        edges=graph.edges,
        schedule=committed,
        provisional_schedule=provisional,
        provisional_delta=delta,
        cycles=cycles,
        graph_diagnostics=diagnostics,
        warnings=warnings,
    )


def _provisional_delta(graph, committed, provisional):
    """
    Difference between the committed and provisional schedules, with a
    per-requirement human-readable explanation.
    """
    warnings = []
    additional = sorted(set(provisional.nodes) - set(committed.nodes))

    if not additional:
        return {
            "additional_requirements": [],
            "additional_node_count": 0,
            "committed_duration_days": committed.parallel_duration_days,
            "provisional_duration_days": provisional.parallel_duration_days,
            "critical_path_change_days": 0,
            "committed_critical_paths": committed.critical_paths,
            "provisional_critical_paths": provisional.critical_paths,
            "critical_path_changed": False,
            "unlocked_by_facts": [],
            "summary_explanation": (
                "No requirements are pending unknown facts. The committed "
                "schedule is complete on the facts supplied."),
        }, warnings

    change = (provisional.parallel_duration_days
              - committed.parallel_duration_days)
    cp_changed = committed.critical_paths != provisional.critical_paths

    facts = sorted({f for rid in additional
                    for f in graph.nodes[rid].missing_facts})

    details = []
    for rid in additional:
        node = graph.nodes[rid]
        sn = provisional.nodes[rid]
        missing = node.missing_facts
        fact_phrase = _join(missing) if missing else "the missing information"

        if node.sla.kind == SLA_UNSPECIFIED:
            impact = (f"{node.name} may be required if {fact_phrase} "
                      f"confirms that it applies. Its processing time is not "
                      f"recorded in the regulatory data, so the effect on the "
                      f"timeline cannot be estimated.")
        elif node.sla.kind == SLA_INVALID:
            impact = (f"{node.name} may be required if {fact_phrase} confirms "
                      f"that it applies. Its recorded processing time is "
                      f"unusable, so the effect on the timeline cannot be "
                      f"estimated.")
        else:
            impact = (f"{node.name} may add approximately {sn.duration_days} "
                      f"{DURATION_UNIT} if {fact_phrase} confirms that it "
                      f"applies.")
            if sn.on_critical_path:
                impact += (" It would fall on the critical path, so it would "
                           "extend the overall timeline rather than run "
                           "alongside other work.")
            else:
                impact += (" It would run in parallel with other work and "
                           "would not extend the overall timeline on its own.")

        details.append({
            "requirement_id": rid,
            "name": node.name,
            "requirement_type": node.requirement_type,
            "department": node.department,
            "state": node.state,
            "sla_kind": node.sla.kind,
            "sla_days": node.sla.days,
            "duration_days": sn.duration_days,
            "earliest_start_day": sn.earliest_start_day,
            "earliest_finish_day": sn.earliest_finish_day,
            "on_provisional_critical_path": sn.on_critical_path,
            "missing_facts": missing,
            "blocked_by": sn.blocked_by,
            "blocks": sn.blocks,
            "explanation": impact,
        })

    if change > 0:
        summary = (f"Supplying {_join(facts)} could extend the timeline by up "
                   f"to {change} {DURATION_UNIT}, from "
                   f"{committed.parallel_duration_days} to "
                   f"{provisional.parallel_duration_days}.")
    elif change == 0:
        summary = (f"{len(additional)} requirement(s) are pending "
                   f"{_join(facts)}. If they apply they would run alongside "
                   f"existing work and would not extend the overall timeline.")
    else:
        summary = "Provisional schedule is shorter than committed; review data."

    if cp_changed:
        summary += " The critical path would change."

    if change > 0 or cp_changed:
        warnings.append(warning(
            "PROVISIONAL_SCHEDULE_DIFFERS", "warning",
            summary,
            additional_requirements=additional,
            unlocked_by_facts=facts,
            critical_path_change_days=change))

    return {
        "additional_requirements": details,
        "additional_node_count": len(additional),
        "committed_duration_days": committed.parallel_duration_days,
        "provisional_duration_days": provisional.parallel_duration_days,
        "critical_path_change_days": change,
        "committed_critical_paths": committed.critical_paths,
        "provisional_critical_paths": provisional.critical_paths,
        "critical_path_changed": cp_changed,
        "unlocked_by_facts": facts,
        "summary_explanation": summary,
    }, warnings


def _join(items):
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]
