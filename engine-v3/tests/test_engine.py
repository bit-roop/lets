"""
Engine test suite.

Categories, per your spec:
  positive · negative · missing-fact · boundary · temporal · conflict
plus resolution-precedence tests for the four-state aggregation.

Run: python3 -m tests.test_engine
"""

import json
from datetime import date
from pathlib import Path

from engine.derive import Registry, derive
from engine.resolve import State, Evidence, resolve, classify
from engine.tri import Tri, T, F, U, tri_and, tri_or, tri_not
from engine.evaluator import evaluate, select_version
from engine.quantity import compute

ROOT = Path(__file__).resolve().parent.parent
REG = Registry(ROOT / "regulatory", validate=True)

PASS, FAIL = [], []


def check(name, got, want):
    if got == want:
        PASS.append(name)
    else:
        FAIL.append((name, got, want))


def state_of(result, req_id):
    for bucket in ("applicable", "not_applicable", "unknown", "conflict"):
        for item in result[bucket]:
            if item["requirement_id"] == req_id:
                return item["state"]
    return "ABSENT"


BASE = json.loads((ROOT / "personas" / "persona_b.json").read_text())
BASE = {k: v for k, v in BASE.items() if not k.startswith("_")}
TODAY = date(2026, 8, 29)


def run(overrides=None, as_of=TODAY):
    return derive({**BASE, **(overrides or {})}, REG, as_of)


# ─────────────────────────────────────────────────────────
# 1. Kleene truth tables
# ─────────────────────────────────────────────────────────
def test_kleene():
    check("kleene: NOT UNKNOWN", tri_not(U), U)
    check("kleene: TRUE AND UNKNOWN", tri_and([T, U]), U)
    check("kleene: FALSE AND UNKNOWN", tri_and([F, U]), F)
    check("kleene: TRUE OR UNKNOWN", tri_or([T, U]), T)
    check("kleene: FALSE OR UNKNOWN", tri_or([F, U]), U)
    check("kleene: all TRUE", tri_and([T, T]), T)
    check("kleene: all FALSE", tri_or([F, F]), F)

    try:
        bool(U)
        check("kleene: bool(Tri) raises", False, True)
    except TypeError:
        check("kleene: bool(Tri) raises", True, True)


# ─────────────────────────────────────────────────────────
# 2. FSSAI boundary — threshold-1, threshold, threshold+1
# ─────────────────────────────────────────────────────────
def test_fssai_boundaries():
    cases = [
        (14_900_000, "F-01", "Rs 1.49 cr"),
        (15_000_000, "F-01", "Rs 1.50 cr exactly (<= is inclusive)"),
        (15_000_001, "F-02", "Rs 1.50 cr + Re 1"),
        (499_999_999, "F-02", "Rs 49.99 cr"),
        (500_000_000, "F-02", "Rs 50 cr exactly (<= is inclusive)"),
        (500_000_001, "F-03", "Rs 50 cr + Re 1"),
    ]
    for turnover, expected, label in cases:
        r = run({"annual_turnover": turnover})
        check(f"fssai boundary {label} -> {expected}",
              state_of(r, expected), "APPLICABLE")

    # and the others must be excluded, not merely absent
    r = run({"annual_turnover": 15_000_001})
    check("fssai boundary: F-01 excluded at 1.5cr+1",
          state_of(r, "F-01"), "NOT_APPLICABLE")
    check("fssai boundary: F-03 excluded at 1.5cr+1",
          state_of(r, "F-03"), "NOT_APPLICABLE")


# ─────────────────────────────────────────────────────────
# 3. Factory threshold — Maharashtra 20/40, NOT central 10/20
# ─────────────────────────────────────────────────────────
def test_factory_boundaries():
    for n, want, label in [
        (19, "NOT_APPLICABLE", "19 workers with power"),
        (20, "APPLICABLE", "20 workers with power (threshold)"),
        (21, "APPLICABLE", "21 workers with power"),
    ]:
        r = run({"workers_for_threshold": n, "uses_power": True})
        check(f"factory boundary: {label}", state_of(r, "S-02"), want)

    # the central-threshold trap: 15 workers would trigger under 10/20
    r = run({"workers_for_threshold": 15, "uses_power": True})
    check("factory: 15 workers NOT a factory in Maharashtra",
          state_of(r, "S-02"), "NOT_APPLICABLE")

    for n, want, label in [
        (39, "NOT_APPLICABLE", "39 workers without power"),
        (40, "APPLICABLE", "40 workers without power (threshold)"),
    ]:
        r = run({"workers_for_threshold": n, "uses_power": False})
        check(f"factory boundary: {label}", state_of(r, "S-02"), want)


# ─────────────────────────────────────────────────────────
# 4. Missing facts must yield UNKNOWN, never FALSE
# ─────────────────────────────────────────────────────────
def test_missing_facts():
    r = run({"mpcb_category": None})
    check("missing: mpcb_category -> V-01 UNKNOWN",
          state_of(r, "V-01"), "UNKNOWN")

    r = run({"mpcb_category": "White"})
    check("present: mpcb_category=White -> V-01 NOT_APPLICABLE",
          state_of(r, "V-01"), "NOT_APPLICABLE")

    r = run({"workers_for_threshold": None})
    check("missing: worker count -> S-02 UNKNOWN",
          state_of(r, "S-02"), "UNKNOWN")

    # the case you raised: turnover known but export/multi-state missing
    r = run({"annual_turnover": 80_000_000, "export": None,
             "multi_state_operation": None})
    check("missing: export+multistate -> F-02 UNKNOWN",
          state_of(r, "F-02"), "UNKNOWN")
    check("missing: export+multistate -> F-03 UNKNOWN",
          state_of(r, "F-03"), "UNKNOWN")

    item = next(i for i in r["unknown"] if i["requirement_id"] == "F-02")
    check("missing: F-02 names the missing facts",
          set(item["missing_facts"]), {"export", "multi_state_operation"})

    # UNKNOWN must never be silently dropped
    r = run({"mpcb_category": None})
    check("missing: V-01 not absent", state_of(r, "V-01") != "ABSENT", True)


# ─────────────────────────────────────────────────────────
# 5. Temporal — version in force on the filing date
# ─────────────────────────────────────────────────────────
def test_temporal():
    facts = {"annual_turnover": 10_000_000}   # Rs 1 cr

    r = run(facts, as_of=date(2026, 3, 31))
    check("temporal: Rs1cr on 2026-03-31 -> State Licence (old rule)",
          state_of(r, "F-02"), "APPLICABLE")

    r = run(facts, as_of=date(2026, 4, 1))
    check("temporal: Rs1cr on 2026-04-01 -> Registration (new rule)",
          state_of(r, "F-01"), "APPLICABLE")

    r = run(facts, as_of=date(2026, 3, 31))
    ev = next(i for i in r["applicable"] if i["requirement_id"] == "F-02")
    check("temporal: old date selects v1",
          ev["evidence"][0]["version"], 1)

    r = run(facts, as_of=date(2026, 4, 1))
    ev = next(i for i in r["applicable"] if i["requirement_id"] == "F-01")
    check("temporal: new date selects v2",
          ev["evidence"][0]["version"], 2)

    # select_version directly
    versions = REG.versions_of("FSSAI-CAT-STATE")
    check("temporal: select_version boundary day before",
          select_version(versions, date(2026, 3, 31))["version"], 1)
    check("temporal: select_version boundary day of",
          select_version(versions, date(2026, 4, 1))["version"], 2)
    check("temporal: no version before any effective_from",
          select_version(versions, date(2000, 1, 1)), None)


# ─────────────────────────────────────────────────────────
# 6. Resolution precedence — the four-state semantics
# ─────────────────────────────────────────────────────────
def _ev(kind, rule_id="R", missing=None, status="VERIFIED"):
    trace = [{"fact": f, "result": "UNKNOWN"} for f in (missing or [])]
    return Evidence(kind, {"rule_id": rule_id, "version": 1,
                           "rule_name": rule_id, "result": "?",
                           "facts_used": trace,
                           "verification_status": status})


def test_resolution_precedence():
    s, _, _ = resolve([_ev(Evidence.POSITIVE_DEFINITE, "A"),
                       _ev(Evidence.ACTIVE_EXCLUSION, "B")])
    check("resolve: required + actively excluded -> CONFLICT", s, State.CONFLICT)

    # your veterinary-NOC case: indeterminate requires vs definitive exclusion
    s, _, _ = resolve([_ev(Evidence.POSITIVE_INDETERMINATE, "A", ["animal_origin"]),
                       _ev(Evidence.ACTIVE_EXCLUSION, "B")])
    check("resolve: active exclusion beats indeterminate requires",
          s, State.NOT_APPLICABLE)

    # but absence of trigger must NOT beat indeterminate requires
    s, _, _ = resolve([_ev(Evidence.POSITIVE_INDETERMINATE, "A", ["x"]),
                       _ev(Evidence.ABSENCE_OF_TRIGGER, "B")])
    check("resolve: absence of trigger does NOT beat indeterminate",
          s, State.UNKNOWN)

    s, _, _ = resolve([_ev(Evidence.POSITIVE_DEFINITE, "A"),
                       _ev(Evidence.ABSENCE_OF_TRIGGER, "B")])
    check("resolve: one definite requires wins over absence", s, State.APPLICABLE)

    s, _, w = resolve([_ev(Evidence.POSITIVE_DEFINITE, "A"),
                       _ev(Evidence.EXCLUSION_INDETERMINATE, "B", ["y"])])
    check("resolve: definite requires + indeterminate exclusion -> APPLICABLE",
          s, State.APPLICABLE)
    check("resolve: ...and warns about the indeterminate exclusion",
          any(x["type"] == "INDETERMINATE_EXCLUSION" for x in w), True)

    s, _, _ = resolve([_ev(Evidence.ABSENCE_OF_TRIGGER, "A")])
    check("resolve: only absence -> NOT_APPLICABLE", s, State.NOT_APPLICABLE)

    s, _, _ = resolve([_ev(Evidence.POSITIVE_INDETERMINATE, "A", ["z"])])
    check("resolve: only indeterminate -> UNKNOWN", s, State.UNKNOWN)


def test_classify():
    check("classify: requires+TRUE", classify("requires", "TRUE"),
          Evidence.POSITIVE_DEFINITE)
    check("classify: requires+FALSE", classify("requires", "FALSE"),
          Evidence.ABSENCE_OF_TRIGGER)
    check("classify: requires+UNKNOWN", classify("requires", "UNKNOWN"),
          Evidence.POSITIVE_INDETERMINATE)
    check("classify: excludes+TRUE", classify("excludes", "TRUE"),
          Evidence.ACTIVE_EXCLUSION)
    check("classify: excludes+FALSE says nothing",
          classify("excludes", "FALSE"), None)


# ─────────────────────────────────────────────────────────
# 7. Conflict detection end to end
# ─────────────────────────────────────────────────────────
def test_conflict_end_to_end():
    import copy
    reg = copy.deepcopy(REG)
    reg.rules = list(REG.rules) + [{
        "rule_id": "TEST-CONFLICT", "version": 1, "requirement_id": "S-02",
        "name": "Synthetic contradictory rule",
        "condition": {"all": [{"fact": "uses_power", "op": "==", "value": True}]},
        "effect": {"excludes": ["S-02"]},
        "source": {"statute": "test", "effective_from": "2020-01-01"},
        "verification_status": "SECONDARY", "last_verified": "2026-08-29",
    }]
    r = derive(BASE, reg, TODAY)
    check("conflict: contradictory rules -> CONFLICT state",
          state_of(r, "S-02"), "CONFLICT")
    check("conflict: CONFLICT is not reported as applicable",
          any(i["requirement_id"] == "S-02" for i in r["applicable"]), False)
    check("conflict: raises RULE_CONTRADICTION",
          any(w["type"] == "RULE_CONTRADICTION" for w in r["warnings"]), True)


# ─────────────────────────────────────────────────────────
# 8. Temporal overlap detection in data validation
# ─────────────────────────────────────────────────────────
def test_temporal_overlap_detection():
    from engine.validate_data import _validate_temporal_overlap

    class Fake:
        rules = [
            {"rule_id": "X", "version": 1,
             "source": {"effective_from": "2020-01-01", "effective_to": "2026-06-30"}},
            {"rule_id": "X", "version": 2,
             "source": {"effective_from": "2026-01-01", "effective_to": None}},
        ]
    issues = _validate_temporal_overlap(Fake())
    check("validation: overlapping versions detected",
          any(i.code == "TEMPORAL_OVERLAP" for i in issues), True)

    class Clean:
        rules = [
            {"rule_id": "Y", "version": 1,
             "source": {"effective_from": "2020-01-01", "effective_to": "2026-03-31"}},
            {"rule_id": "Y", "version": 2,
             "source": {"effective_from": "2026-04-01", "effective_to": None}},
        ]
    issues = _validate_temporal_overlap(Clean())
    check("validation: adjacent versions do not overlap",
          any(i.code == "TEMPORAL_OVERLAP" for i in issues), False)

    class Inverted:
        rules = [{"rule_id": "Z", "version": 1,
                  "source": {"effective_from": "2026-06-01",
                             "effective_to": "2026-01-01"}}]
    issues = _validate_temporal_overlap(Inverted())
    check("validation: inverted date range detected",
          any(i.code == "TEMPORAL_INVERTED" for i in issues), True)


# ─────────────────────────────────────────────────────────
# 9. Quantity — structured only, no code execution
# ─────────────────────────────────────────────────────────
def test_quantity():
    q = compute({"operation": "ceil_divide", "fact": "food_handlers",
                 "divisor": 25}, {"food_handlers": 30})
    check("quantity: ceil(30/25) = 2", q["value"], 2)

    q = compute({"operation": "ceil_divide", "fact": "food_handlers",
                 "divisor": 25}, {"food_handlers": 25})
    check("quantity: ceil(25/25) = 1", q["value"], 1)

    q = compute({"operation": "ceil_divide", "fact": "food_handlers",
                 "divisor": 25}, {"food_handlers": 26})
    check("quantity: ceil(26/25) = 2", q["value"], 2)

    q = compute({"operation": "ceil_divide", "fact": "food_handlers",
                 "divisor": 25}, {})
    check("quantity: missing fact -> None", q["value"], None)
    check("quantity: missing fact named", q["missing_facts"], ["food_handlers"])

    try:
        compute({"operation": "__import__('os').system", "fact": "x"}, {})
        check("quantity: rejects unknown operation", False, True)
    except ValueError:
        check("quantity: rejects unknown operation", True, True)


# ─────────────────────────────────────────────────────────
# 10. Dependency validation
# ─────────────────────────────────────────────────────────
def test_dependencies():
    from engine.validate_data import _validate_dependencies, _detect_cycles

    check("deps: F-02 has no scheduling dependencies (edge retracted)",
          REG.scheduling_dependencies("F-02"), [])

    deps = REG.dependencies.get("F-02", {})
    check("deps: retracted edge preserved as candidate",
          len(deps.get("candidate_dependencies", [])) > 0, True)

    check("deps: S-02 depends on S-01",
          [d["requirement_id"] for d in REG.dependencies["S-02"]["depends_on"]],
          ["S-01"])

    issues = _detect_cycles({"A": ["B"], "B": ["C"], "C": ["A"]})
    check("deps: cycle detected", any(i.code == "DEP_CYCLE" for i in issues), True)
    issues = _detect_cycles({"A": ["B"], "B": ["C"], "C": []})
    check("deps: acyclic graph clean",
          any(i.code == "DEP_CYCLE" for i in issues), False)

    class Fake:
        catalogue = {"A": {}, "B": {}}
        dependencies = {"A": {"depends_on": [
            {"requirement_id": "B", "dependency_type": "INVENTED", "basis": "x"}]}}
    issues = _validate_dependencies(Fake())
    check("deps: invalid dependency_type rejected",
          any(i.code == "DEP_BAD_TYPE" for i in issues), True)


# ─────────────────────────────────────────────────────────
# 11. Registry integrity
# ─────────────────────────────────────────────────────────
def test_registry():
    check("registry: no data errors", len(REG.errors), 0)
    check("registry: catalogue non-empty", len(REG.catalogue) > 0, True)
    check("registry: no string quantity_formula anywhere",
          any("quantity_formula" in m for m in REG.catalogue.values()), False)


# ─────────────────────────────────────────────────────────
# 12. Persona regression
# ─────────────────────────────────────────────────────────
def test_personas():
    a = json.loads((ROOT / "personas" / "persona_a.json").read_text())
    a = {k: v for k, v in a.items() if not k.startswith("_")}
    ra = derive(a, REG, TODAY)
    check("persona A: FSSAI Registration, not licence",
          state_of(ra, "F-01"), "APPLICABLE")
    check("persona A: not a factory at 6 workers",
          state_of(ra, "S-02"), "NOT_APPLICABLE")
    check("persona A: no boiler registration",
          state_of(ra, "S-03"), "NOT_APPLICABLE")
    check("persona A: no conflicts", ra["summary"]["conflict"], 0)

    rb = run()
    check("persona B: FSSAI State Licence", state_of(rb, "F-02"), "APPLICABLE")
    check("persona B: is a factory", state_of(rb, "S-02"), "APPLICABLE")
    check("persona B: boiler registration", state_of(rb, "S-03"), "APPLICABLE")
    check("persona B: MPCB indeterminate (category not supplied)",
          state_of(rb, "V-01"), "UNKNOWN")
    check("persona B: no conflicts", rb["summary"]["conflict"], 0)

    item = next(i for i in rb["applicable"] if i["requirement_id"] == "F-09")
    check("persona B: FoSTaC quantity = 2 for 30 handlers",
          item["quantity"]["value"], 2)
    check("persona B: boiler rule now high confidence (promoted to VERIFIED)",
          next(i for i in rb["applicable"]
               if i["requirement_id"] == "S-03")["confidence"], "high")


# ─────────────────────────────────────────────────────────
# 13. Boiler — three conditions, all required (VERIFIED)
# ─────────────────────────────────────────────────────────
def test_boiler_positive_negative():
    r = run({"boiler_operates": True, "boiler_capacity_litres": 500,
             "boiler_pressure_kg_cm2": 7, "boiler_water_temp_c": 170})
    check("boiler positive: 500L, 7kg, 170C -> APPLICABLE",
          state_of(r, "S-03"), "APPLICABLE")
    check("boiler positive: also requires attendant certificate",
          state_of(r, "S-04"), "APPLICABLE")

    r = run({"boiler_operates": False, "boiler_capacity_litres": 0,
             "boiler_pressure_kg_cm2": None, "boiler_water_temp_c": None})
    check("boiler negative: no boiler -> NOT_APPLICABLE",
          state_of(r, "S-03"), "NOT_APPLICABLE")

    # FALSE must dominate the conjunction even with siblings missing
    item = next(i for i in r["not_applicable"] if i["requirement_id"] == "S-03")
    check("boiler negative: FALSE dominates missing siblings",
          item["evidence"][0]["evidence_kind"], "ABSENCE_OF_TRIGGER")


def test_boiler_boundaries():
    ok = {"boiler_operates": True, "boiler_pressure_kg_cm2": 7,
          "boiler_water_temp_c": 170}
    for litres, want, label in [
        (24, "NOT_APPLICABLE", "24 litres"),
        (25, "APPLICABLE", "25 litres exactly (>= is inclusive)"),
        (26, "APPLICABLE", "26 litres"),
    ]:
        r = run({**ok, "boiler_capacity_litres": litres})
        check(f"boiler boundary capacity: {label}", state_of(r, "S-03"), want)

    cap = {"boiler_operates": True, "boiler_capacity_litres": 500,
           "boiler_water_temp_c": 170}
    for press, want, label in [
        (0.9, "NOT_APPLICABLE", "0.9 kg/cm2"),
        (1.0, "APPLICABLE", "1.0 kg/cm2 exactly"),
    ]:
        r = run({**cap, "boiler_pressure_kg_cm2": press})
        check(f"boiler boundary pressure: {label}", state_of(r, "S-03"), want)

    temp_base = {"boiler_operates": True, "boiler_capacity_litres": 500,
                 "boiler_pressure_kg_cm2": 7}
    for temp, want, label in [
        (99, "NOT_APPLICABLE", "99C (hot water generator)"),
        (100, "APPLICABLE", "100C exactly"),
        (101, "APPLICABLE", "101C"),
    ]:
        r = run({**temp_base, "boiler_water_temp_c": temp})
        check(f"boiler boundary temperature: {label}", state_of(r, "S-03"), want)


def test_boiler_v1_regression():
    """The defect v1 had: capacity alone would wrongly require registration."""
    r = run({"boiler_operates": True, "boiler_capacity_litres": 500,
             "boiler_pressure_kg_cm2": 0.5, "boiler_water_temp_c": 80})
    check("boiler regression: 500L at 80C is NOT a boiler",
          state_of(r, "S-03"), "NOT_APPLICABLE")
    item = next(i for i in r["not_applicable"] if i["requirement_id"] == "S-03")
    check("boiler regression: excluded actively by the HWG rule",
          any(e["evidence_kind"] == "ACTIVE_EXCLUSION" for e in item["evidence"]),
          True)


def test_boiler_missing_facts():
    r = run({"boiler_operates": True, "boiler_capacity_litres": 500,
             "boiler_pressure_kg_cm2": None, "boiler_water_temp_c": None})
    check("boiler missing: pressure and temp -> UNKNOWN",
          state_of(r, "S-03"), "UNKNOWN")
    item = next(i for i in r["unknown"] if i["requirement_id"] == "S-03")
    check("boiler missing: names both missing facts",
          set(item["missing_facts"]) >= {"boiler_pressure_kg_cm2",
                                         "boiler_water_temp_c"}, True)

    # temperature known and low -> active exclusion beats the indeterminate
    r = run({"boiler_operates": True, "boiler_capacity_litres": 500,
             "boiler_pressure_kg_cm2": None, "boiler_water_temp_c": 80})
    check("boiler missing: known low temp resolves despite missing pressure",
          state_of(r, "S-03"), "NOT_APPLICABLE")


# ─────────────────────────────────────────────────────────
# 14. Factories Act extension by notification (VERIFIED)
# ─────────────────────────────────────────────────────────
def test_factory_notified_extension():
    r = run({"workers_for_threshold": 5, "uses_power": True,
             "notified_industry_category": ["saw_mill"]})
    check("factory extension: saw mill at 5 workers -> APPLICABLE",
          state_of(r, "S-02"), "APPLICABLE")

    r = run({"workers_for_threshold": 5, "uses_power": True,
             "notified_industry_category": []})
    check("factory extension: 5 workers, no notified category -> NOT_APPLICABLE",
          state_of(r, "S-02"), "NOT_APPLICABLE")

    r = run({"workers_for_threshold": 5, "uses_power": True,
             "notified_industry_category": None})
    check("factory extension: missing category -> UNKNOWN",
          state_of(r, "S-02"), "UNKNOWN")

    r = run({"workers_for_threshold": 5, "uses_power": True,
             "notified_industry_category": ["power_loom",
                                            "flammable_solvent_process"]})
    check("factory extension: multiple notified categories -> APPLICABLE",
          state_of(r, "S-02"), "APPLICABLE")


# ─────────────────────────────────────────────────────────
# 15. EPFO — SECONDARY, must be medium confidence
# ─────────────────────────────────────────────────────────
def test_epf():
    for n, want, label in [
        (19, "NOT_APPLICABLE", "19 employees"),
        (20, "APPLICABLE", "20 employees exactly"),
        (21, "APPLICABLE", "21 employees"),
    ]:
        r = run({"employees_total": n})
        check(f"epf boundary: {label}", state_of(r, "E-08"), want)

    r = run({"employees_total": None})
    check("epf missing: headcount -> UNKNOWN", state_of(r, "E-08"), "UNKNOWN")

    r = run({"employees_total": 45})
    item = next(i for i in r["applicable"] if i["requirement_id"] == "E-08")
    check("epf: SECONDARY rule yields medium confidence",
          item["confidence"], "medium")


# ─────────────────────────────────────────────────────────
# 16. ESIC — UNVERIFIED, must stay UNKNOWN and be flagged
# ─────────────────────────────────────────────────────────
def test_esic_stays_unverified():
    r = run({"employees_total": 45})
    check("esic: no implemented-area fact -> UNKNOWN",
          state_of(r, "E-09"), "UNKNOWN")

    r = run({"employees_total": 45, "in_esic_implemented_area": True})
    check("esic: with the fact supplied -> APPLICABLE",
          state_of(r, "E-09"), "APPLICABLE")
    item = next(i for i in r["applicable"] if i["requirement_id"] == "E-09")
    check("esic: UNVERIFIED rule yields low confidence",
          item["confidence"], "low")
    check("esic: raises UNVERIFIED_RULE warning",
          any(w["type"] == "UNVERIFIED_RULE" and w["rule_id"] == "ESIC-REG-001"
              for w in r["warnings"]), True)


# ─────────────────────────────────────────────────────────
# 17. Verification-status discipline
# ─────────────────────────────────────────────────────────
def test_verification_discipline():
    verified = [r for r in REG.rules if r["verification_status"] == "VERIFIED"]
    check("discipline: every VERIFIED rule carries last_verified",
          all(r.get("last_verified") for r in verified), True)
    check("discipline: every VERIFIED rule cites a source_id or statute",
          all(r["source"].get("source_id") or r["source"].get("statute")
              for r in verified), True)

    for r in REG.rules:
        sid = r["source"].get("source_id")
        if sid and r["verification_status"] == "VERIFIED":
            src_status = REG.sources[sid]["verification_status"]
            check(f"discipline: {r['rule_id']}@v{r['version']} not stronger "
                  f"than its source",
                  src_status == "VERIFIED", True)

    r = run()
    for bucket in ("applicable", "unknown"):
        for item in r[bucket]:
            statuses = {e["verification_status"] for e in item["evidence"]}
            if "UNVERIFIED" in statuses:
                check(f"discipline: {item['requirement_id']} flagged low",
                      item["confidence"], "low")


# ─────────────────────────────────────────────────────────
# 18. Persona C — hot water generator edge case
# ─────────────────────────────────────────────────────────
def test_persona_c():
    c = json.loads((ROOT / "personas" / "persona_c.json").read_text())
    c = {k: v for k, v in c.items() if not k.startswith("_")}
    rc = derive(c, REG, TODAY)
    check("persona C: hot water generator needs no boiler registration",
          state_of(rc, "S-03"), "NOT_APPLICABLE")
    check("persona C: nor an attendant certificate",
          state_of(rc, "S-04"), "NOT_APPLICABLE")
    check("persona C: no conflicts", rc["summary"]["conflict"], 0)


if __name__ == "__main__":
    for fn in [test_kleene, test_fssai_boundaries, test_factory_boundaries,
               test_missing_facts, test_temporal, test_resolution_precedence,
               test_classify, test_conflict_end_to_end,
               test_temporal_overlap_detection, test_quantity,
               test_dependencies, test_registry, test_personas,
               test_boiler_positive_negative, test_boiler_boundaries,
               test_boiler_v1_regression, test_boiler_missing_facts,
               test_factory_notified_extension, test_epf,
               test_esic_stays_unverified, test_verification_discipline,
               test_persona_c]:
        fn()

    print("=" * 70)
    print(f"  {len(PASS)} passed   {len(FAIL)} failed")
    print("=" * 70)
    if FAIL:
        for name, got, want in FAIL:
            print(f"  FAIL {name}\n       got {got!r}, want {want!r}")
    else:
        for name in PASS:
            print(f"  ok   {name}")
    raise SystemExit(1 if FAIL else 0)
