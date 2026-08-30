"""
Scheduling: topological order, earliest start/finish, critical paths.

Standard CPM over the admitted dependency graph. Durations come from the
catalogue's sla_days and are never invented. Requirements with unspecified
or invalid SLAs contribute zero to arithmetic and are flagged, so reported
durations are explicitly lower bounds rather than silently wrong.

Iterative algorithms throughout — no recursion — so deep chains cannot hit
a stack limit.
"""

from . import policy
from .errors import CyclicGraphError
from .graph import find_cycles
from .models import (
    Schedule, ScheduledNode, warning,
    INCLUSION_SCHEDULED, INCLUSION_PROVISIONAL,
    SLA_UNSPECIFIED, SLA_INVALID, DURATION_UNIT,
)

MAX_CRITICAL_PATHS = 20

COMMITTED_SCOPE_NOTE = (
    "COMMITTED: contains only requirements the engine resolved as APPLICABLE. "
    "Every item here is confirmed to apply on the facts supplied.")

PROVISIONAL_SCOPE_NOTE = (
    "PROVISIONAL: contains APPLICABLE requirements plus requirements whose "
    "applicability is UNKNOWN pending missing facts. This is a contingency "
    "view, NOT a confirmed schedule. Items may prove unnecessary.")


def topological_order(scope, predecessors, successors):
    """Kahn's algorithm. Ties broken by requirement_id for determinism."""
    indeg = {n: len(predecessors.get(n, [])) for n in scope}
    ready = sorted(n for n in scope if indeg[n] == 0)
    order = []
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m in successors.get(n, []):
            indeg[m] -= 1
            if indeg[m] == 0:
                ready.append(m)
                ready.sort()
    if len(order) != len(scope):
        remaining = sorted(set(scope) - set(order))
        raise CyclicGraphError([remaining])
    return order


def compute_schedule(graph, scope_inclusions, label):
    """
    Build a Schedule over nodes whose inclusion is in scope_inclusions.

    Raises CyclicGraphError if the scoped subgraph contains a cycle.
    """
    scope = set(graph.scoped_ids(scope_inclusions))
    warnings = []

    if not scope:
        return Schedule(
            label=label,
            scope_note=(COMMITTED_SCOPE_NOTE if label == "COMMITTED"
                        else PROVISIONAL_SCOPE_NOTE),
            topological_order=[], parallel_bands=[], nodes={},
            sequential_duration_days=0, parallel_duration_days=0,
            critical_paths=[], critical_path_duration_days=0,
            duration_completeness="COMPLETE", excluded_from_duration=[],
            schedule_confidence="not_applicable",
            confidence_basis="No requirements in scope.",
        ), warnings

    cycles = find_cycles(graph, scope)
    if cycles:
        raise CyclicGraphError(cycles)

    pred = graph.predecessors(scope)
    succ = graph.successors(scope)
    order = topological_order(scope, pred, succ)

    duration = {}
    lower_bound = {}
    excluded = []
    for n in scope:
        sla = graph.nodes[n].sla
        duration[n] = sla.duration
        is_lb = sla.kind in (SLA_UNSPECIFIED, SLA_INVALID)
        lower_bound[n] = is_lb
        if is_lb:
            excluded.append(n)

    # ── forward pass ──
    es, ef, depth = {}, {}, {}
    for n in order:
        ps = pred.get(n, [])
        es[n] = max((ef[p] for p in ps), default=0)
        ef[n] = es[n] + duration[n]
        depth[n] = max((depth[p] + 1 for p in ps), default=0)

    project_duration = max(ef.values(), default=0)
    sequential = sum(duration[n] for n in scope)

    # ── backward pass ──
    lf, ls = {}, {}
    for n in reversed(order):
        ss = succ.get(n, [])
        lf[n] = min((ls[s] for s in ss), default=project_duration)
        ls[n] = lf[n] - duration[n]

    # ── critical paths (all of them) ──
    endpoints = sorted(n for n in scope if ef[n] == project_duration)
    critical_paths = []
    truncated = False

    for endpoint in endpoints:
        stack = [[endpoint]]
        while stack:
            if len(critical_paths) >= MAX_CRITICAL_PATHS:
                truncated = True
                break
            path = stack.pop()
            head = path[0]
            criticals = sorted(p for p in pred.get(head, [])
                               if ef[p] == es[head])
            if not criticals:
                critical_paths.append(path)
            else:
                for p in reversed(criticals):
                    stack.append([p] + path)
        if truncated:
            break

    critical_paths.sort()
    critical_set = {n for p in critical_paths for n in p}

    if truncated:
        warnings.append(warning(
            "MANY_CRITICAL_PATHS", "info",
            f"More than {MAX_CRITICAL_PATHS} critical paths exist; the list "
            "has been truncated.", label=label))

    # slack is meaningless through an unspecified duration
    tainted = _nodes_on_paths_touching(scope, pred, succ, lower_bound)

    scheduled_nodes = {}
    for n in sorted(scope):
        transitive = _transitive_successors(n, succ)
        scheduled_nodes[n] = ScheduledNode(
            requirement_id=n,
            earliest_start_day=es[n],
            earliest_finish_day=ef[n],
            latest_start_day=None if n in tainted else ls[n],
            latest_finish_day=None if n in tainted else lf[n],
            slack_days=None if n in tainted else ls[n] - es[n],
            on_critical_path=n in critical_set,
            depth=depth[n],
            duration_days=duration[n],
            duration_is_lower_bound=lower_bound[n],
            blocks=sorted(succ.get(n, [])),
            blocks_transitively=sorted(transitive),
            blocked_by=sorted(pred.get(n, [])),
        )

    bands = []
    if scope:
        for d in range(max(depth.values()) + 1):
            bands.append(sorted(n for n in scope if depth[n] == d))

    admitted = graph.admitted_edges(scope)
    conf, basis = policy.schedule_confidence(admitted)

    schedule = Schedule(
        label=label,
        scope_note=(COMMITTED_SCOPE_NOTE if label == "COMMITTED"
                    else PROVISIONAL_SCOPE_NOTE),
        topological_order=order,
        parallel_bands=bands,
        nodes=scheduled_nodes,
        sequential_duration_days=sequential,
        parallel_duration_days=project_duration,
        critical_paths=critical_paths,
        critical_path_duration_days=project_duration,
        duration_completeness="PARTIAL" if excluded else "COMPLETE",
        excluded_from_duration=sorted(excluded),
        schedule_confidence=conf,
        confidence_basis=basis,
        duration_unit=DURATION_UNIT,
    )
    return schedule, warnings


def _transitive_successors(start, succ):
    seen, stack = set(), list(succ.get(start, []))
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(succ.get(n, []))
    return seen


def _nodes_on_paths_touching(scope, pred, succ, lower_bound):
    """Nodes whose slack would be computed through an unspecified duration."""
    tainted = {n for n in scope if lower_bound[n]}
    frontier = list(tainted)
    while frontier:
        n = frontier.pop()
        for nxt in list(pred.get(n, [])) + list(succ.get(n, [])):
            if nxt not in tainted:
                tainted.add(nxt)
                frontier.append(nxt)
    return tainted


def rank_blockers(schedule, graph, top_n=5):
    """Requirements gating the most downstream work."""
    ranked = []
    for rid, sn in schedule.nodes.items():
        if not sn.blocks:
            continue
        ranked.append({
            "requirement_id": rid,
            "name": graph.nodes[rid].name,
            "blocks": sn.blocks,
            "blocks_transitively": sn.blocks_transitively,
            "downstream_count": len(sn.blocks_transitively),
            "duration_days": sn.duration_days,
            "on_critical_path": sn.on_critical_path,
        })
    ranked.sort(key=lambda r: (-r["downstream_count"], -r["duration_days"],
                               r["requirement_id"]))
    return ranked[:top_n]
