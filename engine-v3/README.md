# Regulatory Engine v3 — derived facts

Deterministic, auditable derivation of regulatory requirements from a fact
vector. No LLM. Every result traces to a rule, a version, and a source.

    python3 validate.py                 # regulatory data validation
    python3 status.py                   # verification status inventory
    python3 -m tests.test_engine        # core suite
    python3 -m tests.test_derived       # derived-fact suite
    python3 demo_derived.py             # four derived-fact behaviours
    python3 run.py personas/persona_b.json [YYYY-MM-DD]

Docs: `docs/OUTPUT_CONTRACT.md`, `docs/PENDING_VERIFICATION.md`,
`docs/sample_response_persona_b.json`.

---

## Three kinds of thing

| | Origin | Example | Where in output |
|---|---|---|---|
| **Supplied fact** | the applicant | `annual_turnover = 80000000` | input only |
| **Derived fact** | a rule | `msme_eligible = true` | `derived_facts` |
| **Requirement** | a rule | `S-02 Factory Licence` | one of four buckets |

A requirement is something the applicant must obtain. A derived fact is an
intermediate conclusion that other rules consume. They are not interchangeable:
MSME classification is a derived fact, not a requirement, because no one
applies for it — it follows from investment and turnover.

Supplied facts win over derived ones. If a rule derives a fact the applicant
also supplied, the supplied value is retained and
`DERIVATION_SHADOWS_SUPPLIED_FACT` is warned.

## Three layers, deliberately distinct

    CONDITION     three-valued Kleene logic      engine/tri.py, evaluator.py
    DERIVATION    typed ops, fixed registry      engine/derived.py
    REQUIREMENT   four-state resolution          engine/resolve.py

## `derives`

A rule effect may contain `requires`, `excludes`, and/or `derives`.

```json
{
  "effect": {
    "derives": [
      { "fact": "msme_eligible", "operation": "constant",
        "value": true, "value_type": "boolean" }
    ]
  }
}
```

Operations come from a fixed registry in `engine/derived.py`: `constant`,
`copy_fact`, `ceil_divide`, `floor_divide`, `sum`, `max`, `min`. Regulatory
JSON never contains executable expressions. An unsupported operation raises
`DerivationError`; it is never evaluated.

Value types: `string`, `number`, `boolean`, `enum`, `list`. `enum` must declare
`enum_values` and the produced value is checked against it.

## Fixed-point evaluation

    supplied facts
      -> evaluate every rule with a derives effect
      -> collect derived facts
      -> merge newly derived facts
      -> repeat until no new derivation is produced
      -> then evaluate requirement rules ONCE against the settled fact set

Bounded by `MAX_DERIVATION_PASSES = 10` (overridable per call). Rule
evaluation order is `sorted(rule_ids)`, so runs are deterministic.

Reaching a fixed point costs one extra pass: the loop must run once more to
observe that nothing new was produced. A single-step derivation therefore
reports `derivation_passes: 2`.

## Inference cycles

Two independent protections.

**Static** — `_validate_inference_cycles` builds a fact-level graph (facts
consumed by a rule -> facts it derives) and reports `INFERENCE_CYCLE` at
validation time. `a -> b -> c -> a` is detected before the engine runs.

**Runtime** — identical re-derivations are suppressed by signature
`(rule_id, version, fact, value)`, so a cycle over stable values quiesces
naturally. If the pass bound is reached, `INFERENCE_LIMIT_EXCEEDED` is raised,
`reached_fixed_point` is `false`, and partial results are returned. The engine
never loops forever.

## Conflicting derived facts

Two rules deriving different values for the same fact produce a
`DerivedFactConflict` with `resolution: "NONE"`. Both derivations are retained
with full provenance. The fact is **withheld** from the working fact set, so
consumers evaluate to UNKNOWN and carry
`missing_fact_origin: WITHHELD_DUE_TO_CONFLICT`.

The engine has no precedence mechanism. Resolving a regulatory contradiction
by arbitrary precedence would be a silent wrong answer.

## Missing inputs

A missing input never becomes `false`. It produces an
`IndeterminateDerivation` carrying the fact name, missing inputs, rule id,
provenance, and a reason — and deliberately no `value` key.

## Provenance

Every derived fact retains `rule_id`, `rule_version`, `source`,
`verification_status`, `input_facts`, `derived_in_pass`, `derived_at`, and
`operation`. Requirement evidence that consumed a derived fact carries
`derived_facts_used`, and each entry in `facts_used` is tagged
`fact_origin: SUPPLIED | DERIVED`.

"Why does the system believe this?" is answered by reading the output. No LLM.

## Verification discipline

    VERIFIED    department source or the notification itself
    SECONDARY   consistent across independent secondary sources
    UNVERIFIED  asserted, unconfirmed, or sources conflict

A derived fact inherits the status of the rule producing it and can never
claim stronger verification than its source. Run `status.py` before any demo;
only VERIFIED rules may be spoken as claims.

## MSME: implemented as far as the data allows

`MSME-ELIGIBLE-001` derives `msme_eligible` (boolean) from the outer ceiling
recorded in the repository. It does **not** derive a MICRO/SMALL/MEDIUM tier —
only the outer ceiling is recorded, and deriving a tier from it would label
every eligible enterprise MEDIUM. See `docs/PENDING_VERIFICATION.md`.

## MPCB: deliberately not implemented

No rule derives `mpcb_category`. The line-item annexure has not been obtained.
`MPCB-CTE-001` and `MPCB-CTO-001` consume the fact as supplied and yield
UNKNOWN when it is absent, which is the correct behaviour.

## Not built (deliberate)

DAG scheduler · document extraction/OCR/validation · frontend · LLM ·
API integrations. `Registry.scheduling_dependencies()` exists and filters to
LEGAL and OPERATIONAL edges, ready for a future scheduler.
