"""
Graph construction from engine-v3 output.

Read-only with respect to the engine. Requirement applicability is never
recomputed, never overridden, never inferred. Nodes are admitted purely on
the `state` the engine assigned.

Determinism: every collection is sorted by requirement_id, mirroring
engine-v3's sorted(rule_ids), so identical input yields identical output.
"""

from . import policy
from .models import (
    WorkflowNode, WorkflowEdge, classify_sla, warning,
    INCLUSION_SCHEDULED, INCLUSION_PROVISIONAL, INCLUSION_EXCLUDED,
    SLA_UNSPECIFIED, SLA_INVALID,
)

STATE_APPLICABLE = "APPLICABLE"
STATE_UNKNOWN = "UNKNOWN"
STATE_NOT_APPLICABLE = "NOT_APPLICABLE"
STATE_CONFLICT = "CONFLICT"

SPARSE_COVERAGE_THRESHOLD = 0.5


class Graph:
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.warnings = []
        self.diagnostics = {}

    # ── adjacency over admitted, non-dropped edges only ──

    def admitted_edges(self, scope=None):
        return [e for e in self.edges
                if e.admitted and not e.dropped
                and (scope is None or (e.from_id in scope and e.to_id in scope))]

    def predecessors(self, scope=None):
        scope = scope if scope is not None else set(self.nodes)
        pred = {n: [] for n in scope}
        for e in self.admitted_edges(scope):
            pred[e.to_id].append(e.from_id)
        return {k: sorted(set(v)) for k, v in pred.items()}

    def successors(self, scope=None):
        scope = scope if scope is not None else set(self.nodes)
        succ = {n: [] for n in scope}
        for e in self.admitted_edges(scope):
            succ[e.from_id].append(e.to_id)
        return {k: sorted(set(v)) for k, v in succ.items()}

    def scoped_ids(self, inclusions):
        return sorted(n.requirement_id for n in self.nodes.values()
                      if n.inclusion in inclusions)


def _iter_requirements(engine_result):
    """Yield (state, requirement_dict) across all four engine buckets."""
    for bucket, state in (("applicable", STATE_APPLICABLE),
                          ("unknown", STATE_UNKNOWN),
                          ("not_applicable", STATE_NOT_APPLICABLE),
                          ("conflict", STATE_CONFLICT)):
        for req in engine_result.get(bucket, []):
            yield state, req


def build_graph(engine_result, catalogue=None):
    """
    Assemble nodes and edges from an engine-v3 derive() result.

    catalogue is optional and used only to detect requirements the engine
    returned that the catalogue does not describe.
    """
    g = Graph()
    catalogue = catalogue or {}

    conflict_ids = set()
    not_applicable_ids = set()
    dependency_records_present = 0

    # ── nodes ──
    for state, req in _iter_requirements(engine_result):
        rid = req.get("requirement_id")
        if rid is None:
            continue

        if state == STATE_NOT_APPLICABLE:
            not_applicable_ids.add(rid)
            continue

        if state == STATE_CONFLICT:
            conflict_ids.add(rid)
            inclusion = INCLUSION_EXCLUDED
            reason = ("Requirement is in CONFLICT: the regulatory rules "
                      "contradict one another. It has no defensible position "
                      "in a timeline and is excluded from both schedules.")
        elif state == STATE_APPLICABLE:
            inclusion = INCLUSION_SCHEDULED
            reason = "Applicable. Included in the committed schedule."
        else:
            inclusion = INCLUSION_PROVISIONAL
            missing = ", ".join(req.get("missing_facts", [])) or "unspecified facts"
            reason = (f"Applicability is UNKNOWN pending {missing}. Included in "
                      "the provisional schedule only; never in the committed "
                      "schedule.")

        sla = classify_sla(req.get("sla_days"))

        g.nodes[rid] = WorkflowNode(
            requirement_id=rid,
            name=req.get("name", rid),
            requirement_type=req.get("requirement_type", "UNKNOWN"),
            department=req.get("department"),
            authority=req.get("authority"),
            statute=req.get("statute"),
            state=state,
            confidence=req.get("confidence", "low"),
            sla=sla,
            inclusion=inclusion,
            inclusion_reason=reason,
            missing_facts=list(req.get("missing_facts", [])),
            missing_fact_origin=dict(req.get("missing_fact_origin", {})),
            quantity=req.get("quantity"),
        )

        if catalogue and rid not in catalogue:
            g.warnings.append(warning(
                "CATALOGUE_ENTRY_MISSING", "error",
                f"{rid} was returned by the engine but has no catalogue entry. "
                "Name, department and SLA may be incomplete.",
                requirement_id=rid))

        if sla.kind == SLA_UNSPECIFIED:
            g.warnings.append(warning(
                "SLA_UNSPECIFIED", "warning",
                f"{rid} has no recorded sla_days. It is excluded from duration "
                "arithmetic; reported durations are lower bounds.",
                requirement_id=rid))
        elif sla.kind == SLA_INVALID:
            g.warnings.append(warning(
                "SLA_INVALID", "error",
                f"{rid} has an unusable sla_days value ({sla.raw_value!r}). "
                "Excluded from duration arithmetic.",
                requirement_id=rid))

        if state == STATE_CONFLICT:
            g.warnings.append(warning(
                "CONFLICT_EXCLUDED_FROM_SCHEDULE", "error",
                f"{rid} is in CONFLICT and has been excluded from scheduling.",
                requirement_id=rid))

    # ── edges ──
    seen_keys = set()
    for state, req in _iter_requirements(engine_result):
        rid = req.get("requirement_id")
        if rid is None or rid not in g.nodes:
            continue

        has_record = bool(req.get("depends_on")) or bool(
            req.get("candidate_dependencies"))
        if has_record:
            dependency_records_present += 1

        for origin_key, origin in (("depends_on", policy.ORIGIN_DEPENDS_ON),
                                   ("candidate_dependencies", policy.ORIGIN_CANDIDATE)):
            for raw in req.get(origin_key, []) or []:
                if not isinstance(raw, dict):
                    g.warnings.append(warning(
                        "MALFORMED_DEPENDENCY", "error",
                        f"{rid} has a non-object entry in {origin_key}; ignored.",
                        requirement_id=rid))
                    continue

                from_id = raw.get("requirement_id")
                dtype = raw.get("dependency_type")
                admitted = policy.is_admitted(dtype, origin)

                edge = WorkflowEdge(
                    from_id=from_id,
                    to_id=rid,
                    dependency_type=dtype,
                    verification_status=raw.get("verification_status", "UNVERIFIED"),
                    basis=raw.get("basis"),
                    admitted=admitted,
                    admission_reason=policy.admission_reason(dtype, origin, admitted),
                    origin=origin,
                )

                if edge.key() in seen_keys:
                    g.warnings.append(warning(
                        "DUPLICATE_EDGE", "info",
                        f"Duplicate dependency {rid} <- {from_id} ignored.",
                        requirement_id=rid))
                    continue
                seen_keys.add(edge.key())

                # dangling / out-of-scope prerequisites
                if from_id is None:
                    edge.dropped = True
                    edge.admitted = False
                    edge.dropped_reason = "MALFORMED_NO_REQUIREMENT_ID"
                    g.warnings.append(warning(
                        "MALFORMED_DEPENDENCY", "error",
                        f"{rid} has a dependency with no requirement_id.",
                        requirement_id=rid))
                elif from_id in conflict_ids:
                    edge.dropped = True
                    edge.admitted = False
                    edge.dropped_reason = "PREREQUISITE_IN_CONFLICT"
                    g.warnings.append(warning(
                        "BLOCKED_BY_CONFLICT", "error",
                        f"{rid} depends on {from_id}, which is in CONFLICT. The "
                        "edge is dropped; the ordering around this point cannot "
                        "be trusted.",
                        requirement_id=rid, prerequisite_id=from_id))
                elif from_id in not_applicable_ids:
                    edge.dropped = True
                    edge.admitted = False
                    edge.dropped_reason = "PREREQUISITE_NOT_APPLICABLE"
                    g.warnings.append(warning(
                        "DEPENDENCY_TARGET_OUT_OF_SCOPE", "info",
                        f"{rid} depends on {from_id}, which is NOT_APPLICABLE "
                        "for this applicant. The edge cannot block anything and "
                        "is dropped from scheduling.",
                        requirement_id=rid, prerequisite_id=from_id))
                elif from_id not in g.nodes:
                    edge.dropped = True
                    edge.admitted = False
                    edge.dropped_reason = "PREREQUISITE_NOT_IN_RESULT"
                    g.warnings.append(warning(
                        "DEPENDENCY_TARGET_UNKNOWN", "error",
                        f"{rid} depends on {from_id}, which the engine did not "
                        "return in any bucket. Likely a data error in "
                        "dependencies.json.",
                        requirement_id=rid, prerequisite_id=from_id))

                if edge.origin == policy.ORIGIN_CANDIDATE and not edge.dropped:
                    g.warnings.append(warning(
                        "UNVERIFIED_EDGE_PRESENT", "info",
                        f"{rid} has a candidate dependency on {from_id} "
                        f"({dtype}). Recorded for transparency; never admitted "
                        "to scheduling.",
                        requirement_id=rid, prerequisite_id=from_id))

                g.edges.append(edge)

    g.edges.sort(key=lambda e: (e.to_id, e.from_id or "", e.origin,
                                e.dependency_type or ""))

    # ── diagnostics ──
    node_count = len(g.nodes)
    admitted = g.admitted_edges()
    coverage = (dependency_records_present / node_count) if node_count else 0.0

    g.diagnostics = {
        "node_count": node_count,
        "scheduled_node_count": len(g.scoped_ids({INCLUSION_SCHEDULED})),
        "provisional_node_count": len(g.scoped_ids({INCLUSION_PROVISIONAL})),
        "excluded_node_count": len(g.scoped_ids({INCLUSION_EXCLUDED})),
        "edge_count_total": len(g.edges),
        "edge_count_admitted": len(admitted),
        "edge_count_dropped": sum(1 for e in g.edges if e.dropped),
        "edge_count_candidate": sum(
            1 for e in g.edges if e.origin == policy.ORIGIN_CANDIDATE),
        "nodes_with_dependency_record": dependency_records_present,
        "nodes_without_dependency_record": node_count - dependency_records_present,
        "dependency_data_coverage": round(coverage, 4),
    }

    if node_count > 1 and not admitted:
        g.warnings.append(warning(
            "NO_SCHEDULING_CONSTRAINTS", "warning",
            f"No admitted scheduling dependencies exist across {node_count} "
            "requirements. Every requirement appears independently startable. "
            "This reflects the dependency data currently recorded, not a "
            "finding that the approvals are genuinely unconstrained."))

    if node_count and coverage < SPARSE_COVERAGE_THRESHOLD:
        g.warnings.append(warning(
            "SPARSE_DEPENDENCY_DATA", "warning",
            f"{g.diagnostics['nodes_without_dependency_record']} of {node_count} "
            "requirements have no dependency record at all. Parallelism and "
            "duration figures are shaped by the absence of dependency data and "
            "must not be presented as a measured reduction in approval time.",
            dependency_data_coverage=round(coverage, 4)))

    return g


def find_cycles(graph, scope=None):
    """
    Tarjan strongly-connected components over admitted edges.

    Any component of size > 1 is a cycle; self-loops are cycles too.
    Cycles are never auto-broken: choosing an arbitrary edge to ignore is a
    silent wrong answer, the same failure class as arbitrary conflict
    resolution.
    """
    scope = set(scope) if scope is not None else set(graph.nodes)
    succ = graph.successors(scope)
    nodes = sorted(scope)

    index = {}
    low = {}
    on_stack = {}
    stack = []
    counter = [0]
    components = []

    def strongconnect(v):
        work = [(v, 0)]
        while work:
            node, pi = work[-1]
            if pi == 0:
                index[node] = low[node] = counter[0]
                counter[0] += 1
                stack.append(node)
                on_stack[node] = True
            recursed = False
            children = succ.get(node, [])
            for i in range(pi, len(children)):
                w = children[i]
                if w not in index:
                    work[-1] = (node, i + 1)
                    work.append((w, 0))
                    recursed = True
                    break
                if on_stack.get(w):
                    low[node] = min(low[node], index[w])
            if recursed:
                continue
            if low[node] == index[node]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    comp.append(w)
                    if w == node:
                        break
                components.append(sorted(comp))
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])

    for n in nodes:
        if n not in index:
            strongconnect(n)

    cycles = [c for c in components if len(c) > 1]
    for e in graph.admitted_edges(scope):
        if e.from_id == e.to_id:
            cycles.append([e.from_id])

    return sorted(cycles)
