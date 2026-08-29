"""
Derived-fact test suite.

Synthetic rules live here, never in regulatory/. The regulatory dataset
must contain only real, sourced rules.

Run: python3 -m tests.test_derived
"""

import copy
import json
from datetime import date
from pathlib import Path

from engine.derive import Registry, derive, MAX_DERIVATION_PASSES
from engine.derived import (execute, DerivationError, DerivedFact,
                            IndeterminateDerivation, OPERATIONS, VALUE_TYPES)
from engine.validate_data import (_validate_derives, _validate_inference_cycles,
                                  _facts_in_condition)

ROOT = Path(__file__).resolve().parent.parent
BASE_REG = Registry(ROOT / "regulatory", validate=True)
TODAY = date(2026, 8, 29)

PASS, FAIL = [], []


def check(name, got, want):
    if got == want:
        PASS.append(name)
    else:
        FAIL.append((name, got, want))


def reg_with(extra_rules, extra_catalogue=None):
    r = copy.deepcopy(BASE_REG)
    r.rules = list(BASE_REG.rules) + extra_rules
    if extra_catalogue:
        r.catalogue = {**BASE_REG.catalogue, **extra_catalogue}
    return r


def rule(rule_id, condition, effect, version=1, status="SECONDARY", **kw):
    d = {
        "rule_id": rule_id, "version": version,
        "requirement_id": kw.get("requirement_id", "TEST"),
        "name": kw.get("name", rule_id),
        "condition": condition, "effect": effect,
        "source": {"statute": "synthetic test rule",
                   "effective_from": "2020-01-01", "effective_to": None},
        "verification_status": status, "last_verified": "2026-08-29",
    }
    return d


def derives(fact, value, value_type="boolean", **extra):
    return {"fact": fact, "operation": "constant", "value": value,
            "value_type": value_type, **extra}


def when(fact, op, value):
    return {"all": [{"fact": fact, "op": op, "value": value}]}


def state_of(result, req_id):
    for bucket in ("applicable", "not_applicable", "unknown", "conflict"):
        for item in result[bucket]:
            if item["requirement_id"] == req_id:
                return item["state"]
    return "ABSENT"


# ─────────────────────────────────────────────────────────
# 1. Simple derived fact
# ─────────────────────────────────────────────────────────
def test_simple_derivation():
    r = reg_with([rule("T-A", when("x", "==", 1),
                       {"derives": [derives("y", True)]})])
    out = derive({"x": 1}, r, TODAY)
    check("simple: fact derived", "y" in out["derived_facts"], True)
    check("simple: correct value", out["derived_facts"]["y"]["value"], True)
    check("simple: producing rule recorded",
          out["derived_facts"]["y"]["rule_id"], "T-A")
    check("simple: pass recorded",
          out["derived_facts"]["y"]["derived_in_pass"], 1)

    out = derive({"x": 2}, r, TODAY)
    check("simple: condition false -> no derivation",
          "y" in out["derived_facts"], False)


# ─────────────────────────────────────────────────────────
# 2. Chain: derived fact consumed by another rule
# ─────────────────────────────────────────────────────────
def test_derivation_chain():
    r = reg_with(
        [rule("T-CHAIN-1", when("x", "==", 1),
              {"derives": [derives("mid", True)]}),
         rule("T-CHAIN-2", when("mid", "==", True),
              {"requires": ["E-05"]})],
    )
    out = derive({"x": 1}, r, TODAY)
    check("chain: intermediate fact derived",
          out["derived_facts"]["mid"]["value"], True)
    check("chain: downstream requirement applicable",
          state_of(out, "E-05"), "APPLICABLE")

    item = next(i for i in out["applicable"] if i["requirement_id"] == "E-05")
    ev = next(e for e in item["evidence"] if e["rule_id"] == "T-CHAIN-2")
    check("chain: evidence records the derived fact used",
          ev["derived_facts_used"][0]["fact"], "mid")
    check("chain: trace marks fact origin as DERIVED",
          next(t["fact_origin"] for t in ev["facts_used"]
               if t["fact"] == "mid"), "DERIVED")

    out = derive({"x": 2}, r, TODAY)
    check("chain: broken at source -> downstream not applicable",
          state_of(out, "E-05") in ("NOT_APPLICABLE", "UNKNOWN"), True)


# ─────────────────────────────────────────────────────────
# 3. Multiple derivation passes
# ─────────────────────────────────────────────────────────
def test_multiple_passes():
    r = reg_with([
        rule("T-P1", when("seed", "==", 1), {"derives": [derives("a", True)]}),
        rule("T-P2", when("a", "==", True), {"derives": [derives("b", True)]}),
        rule("T-P3", when("b", "==", True), {"derives": [derives("c", True)]}),
    ])
    out = derive({"seed": 1}, r, TODAY)
    check("passes: all three facts derived",
          sorted(out["derived_facts"]), ["a", "b", "c"])
    check("passes: a in pass 1", out["derived_facts"]["a"]["derived_in_pass"], 1)
    check("passes: b in pass 2", out["derived_facts"]["b"]["derived_in_pass"], 2)
    check("passes: c in pass 3", out["derived_facts"]["c"]["derived_in_pass"], 3)
    check("passes: reached fixed point",
          out["derivation_diagnostics"]["reached_fixed_point"], True)
    check("passes: ran more than one pass",
          out["summary"]["derivation_passes"] >= 3, True)


# ─────────────────────────────────────────────────────────
# 4. Missing input -> indeterminate, never false
# ─────────────────────────────────────────────────────────
def test_missing_input():
    r = reg_with([rule("T-MISS", when("absent_fact", "==", 1),
                       {"derives": [derives("z", True)]})])
    out = derive({}, r, TODAY)
    check("missing: no derived fact produced", "z" in out["derived_facts"], False)
    mine = [i for i in out["indeterminate_derivations"] if i["rule_id"] == "T-MISS"]
    check("missing: indeterminate recorded", len(mine), 1)
    ind = mine[0]
    check("missing: names the fact", ind["fact"], "z")
    check("missing: names the missing input",
          ind["missing_facts"], ["absent_fact"])
    check("missing: names the rule", ind["rule_id"], "T-MISS")
    check("missing: carries provenance", "source" in ind, True)
    check("missing: gives a reason", bool(ind["reason"]), True)
    check("missing: value not invented", "value" not in ind, True)

    # operation-level missing input (copy_fact with absent source)
    r2 = reg_with([rule("T-MISS2", when("x", "==", 1),
                        {"derives": [{"fact": "copied",
                                      "operation": "copy_fact",
                                      "from_fact": "nope",
                                      "value_type": "number"}]})])
    out = derive({"x": 1}, r2, TODAY)
    mine = [i for i in out["indeterminate_derivations"] if i["rule_id"] == "T-MISS2"]
    check("missing: operation input missing -> indeterminate",
          mine[0]["missing_facts"], ["nope"])


# ─────────────────────────────────────────────────────────
# 5. Conflicting derived facts
# ─────────────────────────────────────────────────────────
def test_conflicting_derivations():
    r = reg_with([
        rule("T-CONF-A", when("x", "==", 1),
             {"derives": [derives("tier", "SMALL", "enum",
                                  enum_values=["SMALL", "MEDIUM"])]}),
        rule("T-CONF-B", when("x", "==", 1),
             {"derives": [derives("tier", "MEDIUM", "enum",
                                  enum_values=["SMALL", "MEDIUM"])]}),
    ])
    out = derive({"x": 1}, r, TODAY)
    check("conflict: one conflict recorded",
          len(out["derived_fact_conflicts"]), 1)
    c = out["derived_fact_conflicts"][0]
    check("conflict: names the fact", c["fact"], "tier")
    check("conflict: both values retained",
          sorted(c["competing_values"]), ["'MEDIUM'", "'SMALL'"])
    check("conflict: both derivations retained with provenance",
          sorted(d["rule_id"] for d in c["competing_derivations"]),
          ["T-CONF-A", "T-CONF-B"])
    check("conflict: no silent selection", c["resolution"], "NONE")
    check("conflict: fact withheld from fact set",
          "tier" in out["derived_facts"], False)
    check("conflict: warning raised",
          any(w["type"] == "DERIVED_FACT_CONFLICT" for w in out["warnings"]), True)


def test_conflict_propagates_as_unknown():
    r = reg_with([
        rule("T-CP-A", when("x", "==", 1),
             {"derives": [derives("tier", "SMALL", "enum",
                                  enum_values=["SMALL", "MEDIUM"])]}),
        rule("T-CP-B", when("x", "==", 1),
             {"derives": [derives("tier", "MEDIUM", "enum",
                                  enum_values=["SMALL", "MEDIUM"])]}),
        rule("T-CP-C", when("tier", "==", "SMALL"), {"requires": ["E-05"]}),
    ])
    out = derive({"x": 1}, r, TODAY)
    check("conflict: consumer evaluates to UNKNOWN, not a guess",
          state_of(out, "E-05"), "UNKNOWN")
    item = next(i for i in out["unknown"] if i["requirement_id"] == "E-05")
    check("conflict: consumer names the withheld fact",
          "tier" in item["missing_facts"], True)
    check("conflict: origin marked as withheld",
          item["missing_fact_origin"]["tier"], "WITHHELD_DUE_TO_CONFLICT")


# ─────────────────────────────────────────────────────────
# 6. Inference cycles
# ─────────────────────────────────────────────────────────
def test_inference_cycle_static_detection():
    class Fake:
        rules = [
            rule("C1", when("a", "==", True), {"derives": [derives("b", True)]}),
            rule("C2", when("b", "==", True), {"derives": [derives("c", True)]}),
            rule("C3", when("c", "==", True), {"derives": [derives("a", True)]}),
        ]
    issues = _validate_inference_cycles(Fake())
    check("cycle: static detection finds a -> b -> c -> a",
          any(i.code == "INFERENCE_CYCLE" for i in issues), True)

    class Clean:
        rules = [
            rule("L1", when("a", "==", True), {"derives": [derives("b", True)]}),
            rule("L2", when("b", "==", True), {"derives": [derives("c", True)]}),
        ]
    issues = _validate_inference_cycles(Clean())
    check("cycle: linear chain is not a cycle",
          any(i.code == "INFERENCE_CYCLE" for i in issues), False)


def test_inference_cycle_terminates():
    r = reg_with([
        rule("T-CY-1", when("a", "==", True), {"derives": [derives("b", True)]}),
        rule("T-CY-2", when("b", "==", True), {"derives": [derives("c", True)]}),
        rule("T-CY-3", when("c", "==", True), {"derives": [derives("a", True)]}),
    ])
    out = derive({"a": True}, r, TODAY)
    check("cycle: terminates within the bound",
          out["summary"]["derivation_passes"] <= MAX_DERIVATION_PASSES, True)
    check("cycle: reached a fixed point rather than looping",
          out["derivation_diagnostics"]["reached_fixed_point"], True)
    check("cycle: derived b and c",
          all(f in out["derived_facts"] for f in ("b", "c")), True)
    check("cycle: a stayed supplied, not overwritten",
          "a" in out["derived_facts"], False)
    check("cycle: shadowing warned",
          any(w["type"] == "DERIVATION_SHADOWS_SUPPLIED_FACT"
              for w in out["warnings"]), True)


def test_pass_limit_enforced():
    r = reg_with([
        rule("T-L1", when("seed", "==", 1), {"derives": [derives("a", True)]}),
        rule("T-L2", when("a", "==", True), {"derives": [derives("b", True)]}),
        rule("T-L3", when("b", "==", True), {"derives": [derives("c", True)]}),
    ])
    out = derive({"seed": 1}, r, TODAY, max_passes=2)
    check("limit: stopped at the configured bound",
          out["summary"]["derivation_passes"], 2)
    check("limit: reported as not reaching fixed point",
          out["derivation_diagnostics"]["reached_fixed_point"], False)
    check("limit: INFERENCE_LIMIT_EXCEEDED raised",
          any(w["type"] == "INFERENCE_LIMIT_EXCEEDED" for w in out["warnings"]),
          True)
    check("limit: partial results retained",
          "a" in out["derived_facts"], True)
    check("limit: c not reached", "c" in out["derived_facts"], False)


# ─────────────────────────────────────────────────────────
# 7. Repeated identical derivation
# ─────────────────────────────────────────────────────────
def test_repeated_derivation_suppressed():
    r = reg_with([
        rule("T-R1", when("x", "==", 1), {"derives": [derives("y", True)]}),
        rule("T-R2", when("y", "==", True), {"derives": [derives("w", True)]}),
    ])
    out = derive({"x": 1}, r, TODAY)
    check("repeat: converges quickly",
          out["summary"]["derivation_passes"] <= 4, True)
    check("repeat: identical re-derivations suppressed",
          out["derivation_diagnostics"]["repeated_derivations_suppressed"] >= 1,
          True)
    check("repeat: y derived once",
          out["derived_facts"]["y"]["derived_in_pass"], 1)


# ─────────────────────────────────────────────────────────
# 8. Provenance retained
# ─────────────────────────────────────────────────────────
def test_provenance():
    out = derive({"investment_plant_machinery": 60_000_000,
                  "annual_turnover": 80_000_000}, BASE_REG, TODAY)
    df = out["derived_facts"]["msme_eligible"]
    for field in ("fact", "value", "value_type", "rule_id", "rule_version",
                  "source", "verification_status", "input_facts",
                  "derived_in_pass", "derived_at", "operation"):
        check(f"provenance: {field} present", field in df, True)
    check("provenance: rule_id", df["rule_id"], "MSME-ELIGIBLE-001")
    check("provenance: rule_version", df["rule_version"], 1)
    check("provenance: source_id traceable",
          df["source"]["source_id"], "SRC-MSME-001")
    check("provenance: source resolves in registry",
          BASE_REG.sources[df["source"]["source_id"]]["document_number"],
          "S.O. 1364(E)")
    check("provenance: instrument recorded",
          "S.O. 1364(E)" in df["source"]["instrument"], True)
    check("provenance: timestamp present", df["derived_at"].endswith("Z"), True)


# ─────────────────────────────────────────────────────────
# 9. Verification status cannot be inflated
# ─────────────────────────────────────────────────────────
def test_verification_not_inflated():
    r = reg_with([rule("T-VS", when("x", "==", 1),
                       {"derives": [derives("v", True)]}, status="UNVERIFIED")])
    out = derive({"x": 1}, r, TODAY)
    check("status: derived fact inherits UNVERIFIED",
          out["derived_facts"]["v"]["verification_status"], "UNVERIFIED")

    r = reg_with([rule("T-VS2", when("x", "==", 1),
                       {"derives": [derives("v2", True)]}, status="SECONDARY")])
    out = derive({"x": 1}, r, TODAY)
    check("status: derived fact inherits SECONDARY",
          out["derived_facts"]["v2"]["verification_status"], "SECONDARY")

    for name, df in derive({"investment_plant_machinery": 1,
                            "annual_turnover": 1},
                           BASE_REG, TODAY)["derived_facts"].items():
        producing = [x for x in BASE_REG.rules if x["rule_id"] == df["rule_id"]][0]
        check(f"status: {name} matches its producing rule",
              df["verification_status"], producing["verification_status"])
        sid = df["source"].get("source_id")
        if sid and df["verification_status"] == "VERIFIED":
            check(f"status: {name} not stronger than its source",
                  BASE_REG.sources[sid]["verification_status"], "VERIFIED")


# ─────────────────────────────────────────────────────────
# 10. MSME — only what the repository supports
# ─────────────────────────────────────────────────────────
def test_msme_eligibility_boundaries():
    INV_CEIL, TO_CEIL = 1_250_000_000, 5_000_000_000

    for inv, to, want, label in [
        (INV_CEIL - 1, TO_CEIL - 1, True, "both just under ceiling"),
        (INV_CEIL, TO_CEIL, True, "both exactly at ceiling"),
        (INV_CEIL + 1, TO_CEIL, False, "investment 1 over"),
        (INV_CEIL, TO_CEIL + 1, False, "turnover 1 over"),
        (INV_CEIL + 1, TO_CEIL + 1, False, "both over"),
    ]:
        out = derive({"investment_plant_machinery": inv, "annual_turnover": to},
                     BASE_REG, TODAY)
        check(f"msme boundary: {label}",
              out["derived_facts"].get("msme_eligible", {}).get("value") is True,
              want)

    # composite: one criterion alone is not enough
    out = derive({"investment_plant_machinery": 1000, "annual_turnover": TO_CEIL + 1},
                 BASE_REG, TODAY)
    check("msme composite: tiny investment but turnover over ceiling -> ineligible",
          "msme_eligible" in out["derived_facts"], False)


def test_msme_missing_inputs():
    out = derive({"investment_plant_machinery": 60_000_000}, BASE_REG, TODAY)
    check("msme missing: turnover absent -> no derived fact",
          "msme_eligible" in out["derived_facts"], False)
    ind = [i for i in out["indeterminate_derivations"]
           if i["fact"] == "msme_eligible"]
    check("msme missing: indeterminate recorded", len(ind), 1)
    check("msme missing: names annual_turnover",
          ind[0]["missing_facts"], ["annual_turnover"])

    out = derive({}, BASE_REG, TODAY)
    ind = [i for i in out["indeterminate_derivations"]
           if i["fact"] == "msme_eligible"]
    check("msme missing: both inputs absent -> both named",
          sorted(ind[0]["missing_facts"]),
          ["annual_turnover", "investment_plant_machinery"])


def test_msme_tier_not_derived():
    """Tier classification is blocked. Assert we do NOT emit one."""
    out = derive({"investment_plant_machinery": 60_000_000,
                  "annual_turnover": 80_000_000}, BASE_REG, TODAY)
    check("msme tier: no msme_classification fact emitted",
          "msme_classification" in out["derived_facts"], False)
    check("msme tier: no rule claims to derive a tier",
          any(s.get("fact") == "msme_classification"
              for r in BASE_REG.rules
              for s in r.get("effect", {}).get("derives", [])), False)


# ─────────────────────────────────────────────────────────
# 11. Operation registry safety
# ─────────────────────────────────────────────────────────
def test_operation_safety():
    dummy = {"rule_id": "X", "version": 1, "source": {},
             "verification_status": "SECONDARY"}

    for bad_op in ["eval", "__import__", "exec", "lambda", None, "unknown_op"]:
        try:
            execute({"fact": "f", "operation": bad_op, "value_type": "boolean"},
                    {}, dummy, 1)
            check(f"safety: rejects operation {bad_op!r}", False, True)
        except DerivationError:
            check(f"safety: rejects operation {bad_op!r}", True, True)

    try:
        execute({"operation": "constant", "value": 1, "value_type": "number"},
                {}, dummy, 1)
        check("safety: rejects missing fact name", False, True)
    except DerivationError:
        check("safety: rejects missing fact name", True, True)

    try:
        execute({"fact": "f", "operation": "constant", "value": "text",
                 "value_type": "number"}, {}, dummy, 1)
        check("safety: rejects value/type mismatch", False, True)
    except DerivationError:
        check("safety: rejects value/type mismatch", True, True)

    try:
        execute({"fact": "f", "operation": "constant", "value": "X",
                 "value_type": "enum", "enum_values": ["A", "B"]},
                {}, dummy, 1)
        check("safety: rejects value outside enum", False, True)
    except DerivationError:
        check("safety: rejects value outside enum", True, True)

    try:
        execute({"fact": "f", "operation": "ceil_divide", "value_type": "number"},
                {}, dummy, 1)
        check("safety: rejects missing operation keys", False, True)
    except DerivationError:
        check("safety: rejects missing operation keys", True, True)

    out = execute({"fact": "f", "operation": "constant", "value": True,
                   "value_type": "boolean"}, {}, dummy, 1)
    check("safety: valid spec produces a DerivedFact",
          isinstance(out, DerivedFact), True)


# ─────────────────────────────────────────────────────────
# 12. Validation of derives rules
# ─────────────────────────────────────────────────────────
def test_derives_validation():
    def codes(r):
        return {i.code for i in _validate_derives(r, "test")}

    check("validate: unsupported operation",
          "DERIVE_BAD_OPERATION" in codes(
              rule("V1", when("x", "==", 1),
                   {"derives": [{"fact": "f", "operation": "eval",
                                 "value_type": "boolean"}]})), True)
    check("validate: missing fact name",
          "DERIVE_NO_FACT_NAME" in codes(
              rule("V2", when("x", "==", 1),
                   {"derives": [{"operation": "constant", "value": 1,
                                 "value_type": "number"}]})), True)
    check("validate: bad value_type",
          "DERIVE_BAD_VALUE_TYPE" in codes(
              rule("V3", when("x", "==", 1),
                   {"derives": [{"fact": "f", "operation": "constant",
                                 "value": 1, "value_type": "octet"}]})), True)
    check("validate: value/type mismatch",
          "DERIVE_VALUE_TYPE_MISMATCH" in codes(
              rule("V4", when("x", "==", 1),
                   {"derives": [{"fact": "f", "operation": "constant",
                                 "value": "s", "value_type": "number"}]})), True)
    check("validate: enum without enum_values",
          "DERIVE_ENUM_NO_VALUES" in codes(
              rule("V5", when("x", "==", 1),
                   {"derives": [{"fact": "f", "operation": "constant",
                                 "value": "A", "value_type": "enum"}]})), True)
    check("validate: enum value outside declared set",
          "DERIVE_ENUM_VALUE_INVALID" in codes(
              rule("V6", when("x", "==", 1),
                   {"derives": [{"fact": "f", "operation": "constant",
                                 "value": "Z", "value_type": "enum",
                                 "enum_values": ["A", "B"]}]})), True)
    check("validate: self-reference in condition",
          "DERIVE_SELF_REFERENCE" in codes(
              rule("V7", when("f", "==", 1),
                   {"derives": [{"fact": "f", "operation": "constant",
                                 "value": True, "value_type": "boolean"}]})), True)
    check("validate: self-reference as operation input",
          "DERIVE_SELF_REFERENCE" in codes(
              rule("V8", when("x", "==", 1),
                   {"derives": [{"fact": "f", "operation": "copy_fact",
                                 "from_fact": "f", "value_type": "number"}]})), True)
    check("validate: duplicate derived fact in one rule",
          "DERIVE_DUP_FACT" in codes(
              rule("V9", when("x", "==", 1),
                   {"derives": [derives("f", True), derives("f", False)]})), True)
    check("validate: missing operation keys",
          "DERIVE_MISSING_KEYS" in codes(
              rule("V10", when("x", "==", 1),
                   {"derives": [{"fact": "f", "operation": "ceil_divide",
                                 "value_type": "number"}]})), True)
    check("validate: well-formed derives passes",
          codes(rule("V11", when("x", "==", 1),
                     {"derives": [derives("f", True)]})), set())

    check("validate: condition fact extraction",
          _facts_in_condition({"all": [{"fact": "a", "op": "==", "value": 1},
                                       {"any": [{"fact": "b", "op": ">", "value": 2}]}]}),
          {"a", "b"})


# ─────────────────────────────────────────────────────────
# 13. Registry-level integrity with derives present
# ─────────────────────────────────────────────────────────
def test_registry_clean():
    check("registry: no validation errors", len(BASE_REG.errors), 0)
    check("registry: no inference cycles in real data",
          any(i.code == "INFERENCE_CYCLE" for i in BASE_REG.issues), False)

    derive_rules = [r for r in BASE_REG.rules
                    if r.get("effect", {}).get("derives")]
    check("registry: exactly one derives rule seeded", len(derive_rules), 1)
    check("registry: it is MSME-ELIGIBLE-001",
          derive_rules[0]["rule_id"], "MSME-ELIGIBLE-001")


# ─────────────────────────────────────────────────────────
# 14. Persona regression with derived facts present
# ─────────────────────────────────────────────────────────
def test_persona_regression():
    for name, expect_eligible in [("persona_a", True), ("persona_b", True),
                                  ("persona_c", True)]:
        p = json.loads((ROOT / "personas" / f"{name}.json").read_text())
        facts = {k: v for k, v in p.items() if not k.startswith("_")}
        out = derive(facts, BASE_REG, TODAY)
        check(f"regression: {name} msme_eligible derived",
              out["derived_facts"].get("msme_eligible", {}).get("value"),
              expect_eligible)
        check(f"regression: {name} no derived-fact conflicts",
              len(out["derived_fact_conflicts"]), 0)
        check(f"regression: {name} reached fixed point",
              out["derivation_diagnostics"]["reached_fixed_point"], True)
        check(f"regression: {name} derived in pass 1",
              out["derived_facts"]["msme_eligible"]["derived_in_pass"], 1)
        check(f"regression: {name} quiesces by pass 2",
              out["summary"]["derivation_passes"], 2)


if __name__ == "__main__":
    for fn in [test_simple_derivation, test_derivation_chain,
               test_multiple_passes, test_missing_input,
               test_conflicting_derivations, test_conflict_propagates_as_unknown,
               test_inference_cycle_static_detection,
               test_inference_cycle_terminates, test_pass_limit_enforced,
               test_repeated_derivation_suppressed, test_provenance,
               test_verification_not_inflated, test_msme_eligibility_boundaries,
               test_msme_missing_inputs, test_msme_tier_not_derived,
               test_operation_safety, test_derives_validation,
               test_registry_clean, test_persona_regression]:
        fn()

    print("=" * 70)
    print(f"  DERIVED-FACT SUITE: {len(PASS)} passed   {len(FAIL)} failed")
    print("=" * 70)
    if FAIL:
        for name, got, want in FAIL:
            print(f"  FAIL {name}\n       got {got!r}, want {want!r}")
    else:
        for name in PASS:
            print(f"  ok   {name}")
    raise SystemExit(1 if FAIL else 0)
