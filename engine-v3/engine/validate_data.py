"""
Regulatory data validation.

Runs at boot and in CI. Bad regulatory data must fail loudly here rather
than silently producing a wrong answer for an applicant.
"""

from datetime import date
from .quantity import OPERATIONS
from .derived import OPERATIONS as DERIVE_OPERATIONS, VALUE_TYPES, input_facts_of

VALID_STATUS = {"VERIFIED", "SECONDARY", "UNVERIFIED"}

VALID_REQUIREMENT_TYPE = {
    "APPROVAL", "REGISTRATION", "LICENCE", "NOC", "CONSENT",
    "CERTIFICATE", "INSPECTION", "COMPLIANCE", "RENEWAL",
    "TRAINING", "INCENTIVE",
}

# Only these influence the critical path. RECOMMENDED and UNVERIFIED
# edges are recorded but never scheduled.
VALID_DEPENDENCY_TYPE = {
    "LEGAL",        # statute or rule conditions B on A
    "PROCESS",      # department demands A before B in practice, verified
    "OPERATIONAL",  # physically impossible otherwise (OC after construction)
    "RECOMMENDED",  # sensible ordering, not binding
    "UNVERIFIED",   # asserted but unconfirmed
}

CRITICAL_PATH_TYPES = {"LEGAL", "OPERATIONAL"}

VALID_OPS = {">", ">=", "<", "<=", "==", "!=",
             "in", "not_in", "intersects", "disjoint"}


class Issue:
    def __init__(self, severity, code, message, where=None):
        self.severity = severity
        self.code = code
        self.message = message
        self.where = where

    def __repr__(self):
        loc = f" [{self.where}]" if self.where else ""
        return f"{self.severity.upper()}: {self.code}{loc} — {self.message}"


def validate_registry(registry):
    issues = []
    issues += _validate_catalogue(registry)
    issues += _validate_rules(registry)
    issues += _validate_temporal_overlap(registry)
    issues += _validate_dependencies(registry)
    issues += _validate_sources(registry)
    issues += _validate_inference_cycles(registry)
    return issues


# ── catalogue ──

def _validate_catalogue(reg):
    out = []
    for rid, meta in reg.catalogue.items():
        if "name" not in meta:
            out.append(Issue("error", "CAT_NO_NAME", "missing name", rid))
        rt = meta.get("requirement_type")
        if rt not in VALID_REQUIREMENT_TYPE:
            out.append(Issue("error", "CAT_BAD_TYPE",
                             f"requirement_type {rt!r} not in {sorted(VALID_REQUIREMENT_TYPE)}",
                             rid))
        q = meta.get("quantity")
        if q is not None:
            if not isinstance(q, dict) or "operation" not in q:
                out.append(Issue("error", "CAT_QTY_SHAPE",
                                 "quantity must be a structured object with an 'operation'",
                                 rid))
            elif q["operation"] not in OPERATIONS:
                out.append(Issue("error", "CAT_QTY_OP",
                                 f"unknown quantity operation {q['operation']!r}", rid))
        if "quantity_formula" in meta:
            out.append(Issue("error", "CAT_QTY_STRING",
                             "quantity_formula (string) is forbidden — use structured quantity",
                             rid))
    return out


# ── rules ──

def _validate_rules(reg):
    out = []
    seen = set()
    for r in reg.rules:
        rid = r.get("rule_id")
        ver = r.get("version")
        where = f"{rid}@v{ver}"

        for field in ("rule_id", "version", "requirement_id", "name",
                      "condition", "effect", "source", "verification_status"):
            if field not in r:
                out.append(Issue("error", "RULE_MISSING_FIELD",
                                 f"missing required field {field!r}", where))

        key = (rid, ver)
        if key in seen:
            out.append(Issue("error", "RULE_DUP_VERSION",
                             "duplicate rule_id + version", where))
        seen.add(key)

        vs = r.get("verification_status")
        if vs not in VALID_STATUS:
            out.append(Issue("error", "RULE_BAD_STATUS",
                             f"verification_status {vs!r} invalid", where))
        if vs == "VERIFIED" and not r.get("last_verified"):
            out.append(Issue("error", "RULE_VERIFIED_NO_DATE",
                             "VERIFIED rules must carry last_verified", where))

        src = r.get("source", {})
        if not src.get("effective_from"):
            out.append(Issue("error", "RULE_NO_EFFECTIVE_FROM",
                             "source.effective_from is required", where))
        if not (src.get("source_id") or src.get("statute")):
            out.append(Issue("warning", "RULE_WEAK_PROVENANCE",
                             "no source_id and no statute — provenance is weak", where))
        sid = src.get("source_id")
        if sid and sid not in reg.sources:
            out.append(Issue("error", "RULE_BAD_SOURCE_REF",
                             f"source_id {sid!r} not present in sources.json", where))

        effect = r.get("effect", {})
        unknown_keys = set(effect) - {"requires", "excludes", "derives"}
        if unknown_keys:
            out.append(Issue("error", "RULE_UNKNOWN_EFFECT_KEY",
                             f"unknown effect key(s): {sorted(unknown_keys)}", where))
        if not effect:
            out.append(Issue("error", "RULE_EMPTY_EFFECT",
                             "rule has no effect", where))

        out += _validate_derives(r, where)

        # effects must reference known requirements
        for key_ in ("requires", "excludes"):
            for req in r.get("effect", {}).get(key_, []):
                if req not in reg.catalogue:
                    out.append(Issue("error", "RULE_UNKNOWN_REQUIREMENT",
                                     f"effect.{key_} references unknown requirement {req!r}",
                                     where))

        out += _validate_condition(r.get("condition", {}), where)
    return out


def _validate_condition(cond, where, depth=0):
    out = []
    if depth > 10:
        return [Issue("error", "COND_TOO_DEEP", "condition nested beyond depth 10", where)]
    if not isinstance(cond, dict):
        return [Issue("error", "COND_SHAPE", "condition must be an object", where)]

    keys = set(cond)
    if keys & {"all", "any", "not"}:
        if len(keys & {"all", "any", "not"}) > 1:
            out.append(Issue("error", "COND_MIXED",
                             "condition mixes all/any/not at one level", where))
        for k in ("all", "any"):
            if k in cond:
                if not isinstance(cond[k], list) or not cond[k]:
                    out.append(Issue("error", "COND_EMPTY",
                                     f"{k} must be a non-empty list", where))
                else:
                    for c in cond[k]:
                        out += _validate_condition(c, where, depth + 1)
        if "not" in cond:
            out += _validate_condition(cond["not"], where, depth + 1)
        return out

    for f in ("fact", "op", "value"):
        if f not in cond:
            out.append(Issue("error", "COND_LEAF_INCOMPLETE",
                             f"leaf condition missing {f!r}", where))
    if cond.get("op") not in VALID_OPS:
        out.append(Issue("error", "COND_BAD_OP",
                         f"operator {cond.get('op')!r} not in {sorted(VALID_OPS)}", where))
    if cond.get("op") in {"in", "not_in", "intersects", "disjoint"} \
            and not isinstance(cond.get("value"), (list, set, tuple)):
        out.append(Issue("error", "COND_OP_VALUE_MISMATCH",
                         f"operator {cond.get('op')!r} needs a list value", where))
    return out


# ── temporal overlap ──

def _validate_temporal_overlap(reg):
    """
    Two versions of the same rule must not both be in force on the same day
    unless allow_overlap is set explicitly. Ambiguous version selection is
    silent corruption.
    """
    out = []
    by_id = {}
    for r in reg.rules:
        by_id.setdefault(r["rule_id"], []).append(r)

    for rule_id, versions in by_id.items():
        spans = []
        for r in versions:
            src = r.get("source", {})
            try:
                start = date.fromisoformat(src["effective_from"])
            except (KeyError, TypeError, ValueError):
                continue
            end_raw = src.get("effective_to")
            end = date.fromisoformat(end_raw) if end_raw else date.max
            if end < start:
                out.append(Issue("error", "TEMPORAL_INVERTED",
                                 f"effective_to {end} precedes effective_from {start}",
                                 f"{rule_id}@v{r['version']}"))
            spans.append((start, end, r))

        spans.sort(key=lambda s: s[0])
        for i in range(len(spans)):
            for j in range(i + 1, len(spans)):
                a_s, a_e, a = spans[i]
                b_s, b_e, b = spans[j]
                if a_s <= b_e and b_s <= a_e:
                    if a.get("allow_overlap") and b.get("allow_overlap"):
                        continue
                    out.append(Issue(
                        "error", "TEMPORAL_OVERLAP",
                        f"v{a['version']} ({a_s}..{'open' if a_e == date.max else a_e}) "
                        f"overlaps v{b['version']} ({b_s}..{'open' if b_e == date.max else b_e}). "
                        "Version selection would be ambiguous.",
                        rule_id))

        # gap detection — a date with no version in force
        if len(spans) > 1:
            for i in range(len(spans) - 1):
                _, a_e, a = spans[i]
                b_s, _, b = spans[i + 1]
                if a_e != date.max and (b_s - a_e).days > 1:
                    out.append(Issue(
                        "warning", "TEMPORAL_GAP",
                        f"no version in force between {a_e} and {b_s}", rule_id))
    return out


# ── dependencies ──

def _validate_dependencies(reg):
    out = []
    graph = {}

    for req_id, spec in reg.dependencies.items():
        if req_id not in reg.catalogue:
            out.append(Issue("error", "DEP_UNKNOWN_REQUIREMENT",
                             f"dependency declared for unknown requirement {req_id!r}"))
        deps = spec.get("depends_on", [])
        graph[req_id] = []

        for d in deps:
            if isinstance(d, str):
                out.append(Issue("error", "DEP_BARE_STRING",
                                 f"dependency on {d!r} must be an object with dependency_type",
                                 req_id))
                continue
            target = d.get("requirement_id")
            dtype = d.get("dependency_type")
            if target not in reg.catalogue:
                out.append(Issue("error", "DEP_UNKNOWN_TARGET",
                                 f"depends on unknown requirement {target!r}", req_id))
            if dtype not in VALID_DEPENDENCY_TYPE:
                out.append(Issue("error", "DEP_BAD_TYPE",
                                 f"dependency_type {dtype!r} not in {sorted(VALID_DEPENDENCY_TYPE)}",
                                 req_id))
            if not d.get("basis"):
                out.append(Issue("warning", "DEP_NO_BASIS",
                                 f"dependency on {target} has no stated basis", req_id))
            if dtype == "UNVERIFIED":
                out.append(Issue("warning", "DEP_UNVERIFIED_IN_GRAPH",
                                 f"UNVERIFIED dependency on {target} is in depends_on. "
                                 "It will not affect the critical path.", req_id))
            if target:
                graph[req_id].append(target)

        for cd in spec.get("candidate_dependencies", []):
            if cd.get("dependency_type") not in VALID_DEPENDENCY_TYPE:
                out.append(Issue("warning", "DEP_CANDIDATE_BAD_TYPE",
                                 f"candidate dependency_type {cd.get('dependency_type')!r} invalid",
                                 req_id))

    out += _detect_cycles(graph)
    return out


def _detect_cycles(graph):
    out, WHITE, GREY, BLACK = [], 0, 1, 2
    colour = {n: WHITE for n in graph}

    def visit(node, path):
        colour[node] = GREY
        for nxt in graph.get(node, []):
            if colour.get(nxt, WHITE) == GREY:
                cycle = " -> ".join(path[path.index(nxt):] + [nxt])
                out.append(Issue("error", "DEP_CYCLE",
                                 f"dependency cycle: {cycle}"))
            elif colour.get(nxt, WHITE) == WHITE and nxt in graph:
                visit(nxt, path + [nxt])
        colour[node] = BLACK

    for n in list(graph):
        if colour[n] == WHITE:
            visit(n, [n])
    return out


# ── sources ──

def _validate_sources(reg):
    out = []
    for sid, s in reg.sources.items():
        vs = s.get("verification_status")
        if vs not in VALID_STATUS:
            out.append(Issue("error", "SRC_BAD_STATUS",
                             f"verification_status {vs!r} invalid", sid))
        if vs == "VERIFIED":
            if not s.get("verified_at"):
                out.append(Issue("error", "SRC_VERIFIED_NO_DATE",
                                 "VERIFIED source needs verified_at", sid))
            if not (s.get("source_url") or s.get("document_number")):
                out.append(Issue("warning", "SRC_VERIFIED_NO_LOCATOR",
                                 "VERIFIED source has neither URL nor document number", sid))
    return out


# ── derived-fact rules ──

def _validate_derives(rule, where):
    out = []
    specs = rule.get("effect", {}).get("derives", [])
    if not specs:
        return out
    if not isinstance(specs, list):
        return [Issue("error", "DERIVE_SHAPE",
                      "effect.derives must be a list", where)]

    seen_names = set()
    for spec in specs:
        if not isinstance(spec, dict):
            out.append(Issue("error", "DERIVE_SHAPE",
                             "each derives entry must be an object", where))
            continue

        name = spec.get("fact")
        if not name:
            out.append(Issue("error", "DERIVE_NO_FACT_NAME",
                             "derives entry has no 'fact' name", where))
            continue
        if name in seen_names:
            out.append(Issue("error", "DERIVE_DUP_FACT",
                             f"rule derives {name!r} more than once", where))
        seen_names.add(name)

        op = spec.get("operation")
        if op not in DERIVE_OPERATIONS:
            out.append(Issue("error", "DERIVE_BAD_OPERATION",
                             f"unsupported derivation operation {op!r}. "
                             f"Permitted: {sorted(DERIVE_OPERATIONS)}", where))
            continue

        _fn, required = DERIVE_OPERATIONS[op]
        missing = required - set(spec)
        if missing:
            out.append(Issue("error", "DERIVE_MISSING_KEYS",
                             f"operation {op!r} missing key(s) {sorted(missing)}",
                             where))

        vt = spec.get("value_type")
        if vt not in VALUE_TYPES:
            out.append(Issue("error", "DERIVE_BAD_VALUE_TYPE",
                             f"invalid value_type {vt!r}. "
                             f"Permitted: {sorted(VALUE_TYPES)}", where))
        elif vt == "enum":
            allowed = spec.get("enum_values")
            if not isinstance(allowed, list) or not allowed:
                out.append(Issue("error", "DERIVE_ENUM_NO_VALUES",
                                 f"enum derivation of {name!r} must declare a "
                                 "non-empty enum_values list", where))
            elif op == "constant" and spec.get("value") not in allowed:
                out.append(Issue("error", "DERIVE_ENUM_VALUE_INVALID",
                                 f"constant value {spec.get('value')!r} is not "
                                 f"in enum_values {allowed}", where))
        elif op == "constant":
            if not VALUE_TYPES[vt](spec.get("value")):
                out.append(Issue("error", "DERIVE_VALUE_TYPE_MISMATCH",
                                 f"constant value {spec.get('value')!r} does not "
                                 f"match value_type {vt!r}", where))

        # self-reference: a rule whose condition reads the fact it derives
        consumed = _facts_in_condition(rule.get("condition", {}))
        if name in consumed:
            out.append(Issue("error", "DERIVE_SELF_REFERENCE",
                             f"rule condition reads {name!r}, which it also "
                             "derives", where))
        for src in input_facts_of(spec):
            if src == name:
                out.append(Issue("error", "DERIVE_SELF_REFERENCE",
                                 f"derivation of {name!r} takes {name!r} as input",
                                 where))
    return out


def _facts_in_condition(cond, acc=None):
    if acc is None:
        acc = set()
    if not isinstance(cond, dict):
        return acc
    for k in ("all", "any"):
        if k in cond:
            for c in cond[k]:
                _facts_in_condition(c, acc)
    if "not" in cond:
        _facts_in_condition(cond["not"], acc)
    if "fact" in cond:
        acc.add(cond["fact"])
    return acc


def _validate_inference_cycles(reg):
    """
    Static fact-level cycle detection.

    Edge: fact consumed by a rule -> fact derived by that rule.
    A cycle here means derivation could churn at runtime.
    """
    out = []
    graph = {}
    for r in reg.rules:
        derived = [s.get("fact") for s in r.get("effect", {}).get("derives", [])
                   if s.get("fact")]
        if not derived:
            continue
        consumed = set(_facts_in_condition(r.get("condition", {})))
        for s in r.get("effect", {}).get("derives", []):
            consumed |= set(input_facts_of(s))
        for c in consumed:
            graph.setdefault(c, set()).update(derived)

    WHITE, GREY, BLACK = 0, 1, 2
    colour = {n: WHITE for n in graph}

    def visit(node, path):
        colour[node] = GREY
        for nxt in sorted(graph.get(node, ())):
            if colour.get(nxt, WHITE) == GREY:
                cycle = " -> ".join(path[path.index(nxt):] + [nxt])
                out.append(Issue("error", "INFERENCE_CYCLE",
                                 f"derived-fact inference cycle: {cycle}"))
            elif colour.get(nxt, WHITE) == WHITE and nxt in graph:
                visit(nxt, path + [nxt])
        colour[node] = BLACK

    for n in sorted(graph):
        if colour[n] == WHITE:
            visit(n, [n])
    return out
