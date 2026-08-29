# Output Contract

Stable shape of `engine.derive.derive(facts, registry, as_of) -> dict`.
A representative live response is in `docs/sample_response_persona_b.json`.

No UI is implemented. This document exists so a future frontend can be
built against a fixed shape without reading engine internals.

---

## Top level

```
as_of                        ISO date the rules were evaluated against
summary                      counts
applicable                   [Requirement]
not_applicable               [Requirement]
unknown                      [Requirement]
conflict                     [Requirement]
derived_facts                { fact_name: DerivedFact }
indeterminate_derivations    [IndeterminateDerivation]
derived_fact_conflicts       [DerivedFactConflict]
derivation_diagnostics       fixed-point telemetry
warnings                     [Warning]
```

`summary` keys: `applicable`, `not_applicable`, `unknown`, `conflict`,
`derived_facts`, `indeterminate_derivations`, `derived_fact_conflicts`,
`derivation_passes`, `rules_evaluated`, `warnings`.

A requirement appears in exactly one of the four buckets. The four states
are exhaustive and mutually exclusive.

---

## Requirement

```jsonc
{
  "requirement_id": "S-02",
  "name": "Factory Licence",
  "requirement_type": "LICENCE",     // see enum below
  "authority": "Directorate of Industrial Safety and Health, Maharashtra",
  "department": "DISH",
  "statute": "Factories Act, 1948 s.6",
  "sla_days": 30,
  "state": "APPLICABLE",             // APPLICABLE | NOT_APPLICABLE | UNKNOWN | CONFLICT
  "confidence": "high",              // high | medium | low
  "evidence": [ Evidence, ... ],
  "missing_facts": ["mpcb_category"],              // present only when relevant
  "missing_fact_origin": {                          // paired with missing_facts
    "mpcb_category": "NOT_SUPPLIED"                 // NOT_SUPPLIED | WITHHELD_DUE_TO_CONFLICT
  },
  "quantity": { "value": 2, "missing_facts": [], "formula": "ceil(food_handlers / 25)" },
  "depends_on": [ Dependency, ... ],
  "scheduling_depends_on": ["S-01"],               // LEGAL + OPERATIONAL edges only
  "candidate_dependencies": [ Dependency, ... ]    // asserted but not scheduled
}
```

`requirement_type` is one of: `APPROVAL`, `REGISTRATION`, `LICENCE`, `NOC`,
`CONSENT`, `CERTIFICATE`, `INSPECTION`, `COMPLIANCE`, `RENEWAL`, `TRAINING`,
`INCENTIVE`. A UI must not call all of these "approvals".

`confidence` is derived from the verification status of the rules that
produced the result: any UNVERIFIED rule gives `low`, any SECONDARY gives
`medium`, all VERIFIED gives `high`.

---

## Evidence

```jsonc
{
  "rule_id": "DISH-FACTORY-001",
  "version": 1,
  "rule_name": "Factory licence applicability, Maharashtra thresholds",
  "result": "TRUE",                  // TRUE | FALSE | UNKNOWN (condition outcome)
  "evidence_kind": "POSITIVE_DEFINITE",
  "facts_used": [
    { "fact": "workers_for_threshold", "value": 67, "op": ">=", "target": 20,
      "result": "TRUE", "reason": "workers_for_threshold (67) >= 20",
      "fact_origin": "SUPPLIED" }    // SUPPLIED | DERIVED
  ],
  "derived_facts_used": [ DerivedFact, ... ],   // present only if any were consumed
  "source": { "source_id": "...", "statute": "...", "instrument": "...",
              "effective_from": "...", "effective_to": null },
  "source_detail": { ...resolved sources.json entry... },
  "verification_status": "VERIFIED",
  "last_verified": "2026-08-29",
  "note": "Maharashtra uses 20/40, NOT central 10/20."
}
```

`evidence_kind` is one of:

| kind | meaning |
|---|---|
| `POSITIVE_DEFINITE` | a rule fired TRUE requiring this |
| `POSITIVE_INDETERMINATE` | a requiring rule could not be evaluated |
| `ABSENCE_OF_TRIGGER` | a requiring rule returned FALSE — weak negative |
| `ACTIVE_EXCLUSION` | a rule fired TRUE excluding this — strong negative |
| `EXCLUSION_INDETERMINATE` | an excluding rule could not be evaluated |

The distinction between `ACTIVE_EXCLUSION` and `ABSENCE_OF_TRIGGER` is
load-bearing and should surface differently in a UI. "Fruit processing does
not need a veterinary NOC" is not the same statement as "nothing triggered a
veterinary NOC".

---

## DerivedFact

```jsonc
{
  "fact": "msme_eligible",
  "value": true,
  "value_type": "boolean",           // string | number | boolean | enum | list
  "rule_id": "MSME-ELIGIBLE-001",
  "rule_version": 1,
  "source": { "source_id": "SRC-MSME-001",
              "instrument": "Notification S.O. 1364(E) dt. 21.03.2025",
              "effective_from": "2025-04-01", "effective_to": null },
  "verification_status": "VERIFIED",
  "input_facts": [],                 // facts the operation read (not the condition)
  "derived_in_pass": 1,
  "derived_at": "2026-08-29T12:31:15Z",
  "operation": "constant"            // fixed registry; never an expression
}
```

## IndeterminateDerivation

```jsonc
{
  "fact": "msme_eligible",
  "rule_id": "MSME-ELIGIBLE-001",
  "rule_version": 1,
  "source": { ... },
  "verification_status": "VERIFIED",
  "missing_facts": ["annual_turnover"],
  "reason": "Cannot derive msme_eligible: rule condition is indeterminate. Missing: annual_turnover.",
  "derived_in_pass": 1
}
```

There is deliberately no `value` key. A UI must never render a default.

## DerivedFactConflict

```jsonc
{
  "fact": "tier",
  "derived_in_pass": 1,
  "competing_values": ["'MEDIUM'", "'SMALL'"],
  "competing_derivations": [ DerivedFact, DerivedFact ],
  "resolution": "NONE",
  "note": "The engine does not choose between contradictory derivations..."
}
```

`resolution` is always `NONE`. The engine has no precedence mechanism, by
design. A conflicted fact is withheld from the working fact set, so any rule
consuming it evaluates to UNKNOWN and the consuming requirement carries
`missing_fact_origin: WITHHELD_DUE_TO_CONFLICT`.

## derivation_diagnostics

```jsonc
{
  "passes_run": 2,
  "max_passes": 10,
  "repeated_derivations_suppressed": 0,
  "reached_fixed_point": true
}
```

`reached_fixed_point: false` means results are partial and a banner is
warranted.

## Warning

```jsonc
{ "type": "...", "severity": "error|warning|info", "message": "...", ... }
```

| type | severity | meaning |
|---|---|---|
| `UNVERIFIED_RULE` | warning | an UNVERIFIED rule affected the outcome |
| `INSUFFICIENT_FACTS` | warning | requirement indeterminate; `missing_facts` |
| `RULE_CONTRADICTION` | error | requirement-level CONFLICT |
| `DERIVED_FACT_CONFLICT` | error | contradictory derivations |
| `INDETERMINATE_EXCLUSION` | warning | a possible exclusion could not be evaluated |
| `EXCLUSION_OVERRODE_INDETERMINATE` | info | missing facts turned out not to matter |
| `INFERENCE_LIMIT_EXCEEDED` | error | fixed point not reached |
| `DERIVATION_ERROR` | error | malformed derivation spec |
| `DERIVATION_SHADOWS_SUPPLIED_FACT` | warning | rule derives a fact the applicant supplied; supplied wins |
| `NO_VERSION_IN_FORCE` | warning | no rule version in force on `as_of` |

## Dependency

```jsonc
{
  "requirement_id": "S-01",
  "dependency_type": "LEGAL",   // LEGAL | PROCESS | OPERATIONAL | RECOMMENDED | UNVERIFIED
  "basis": "Factories Act 1948 s.6 — previous permission ... is a precondition",
  "verification_status": "SECONDARY"
}
```

Only `LEGAL` and `OPERATIONAL` appear in `scheduling_depends_on` and may
affect a future critical path.

---

## Answering the required UI questions

| Question | Read from |
|---|---|
| Why is this required? | `evidence[]` where `evidence_kind == POSITIVE_DEFINITE`; render `rule_name`, `facts_used[].reason`, `source_detail` |
| Why is this not applicable? | `evidence[].evidence_kind`. `ACTIVE_EXCLUSION` → "excluded because…"; `ABSENCE_OF_TRIGGER` → "no rule required it" |
| What information is missing? | `missing_facts` + `missing_fact_origin`; also `indeterminate_derivations[].missing_facts` |
| What rule triggered this? | `evidence[].rule_id` + `version` |
| What source supports this? | `evidence[].source_detail` (`document_number`, `document_date`, `source_url`, `verification_status`) |
| What derived fact was used? | `evidence[].derived_facts_used[]`, then `derived_facts[name]` for full provenance |
| Is there a conflict? | `conflict[]` for requirements; `derived_fact_conflicts[]` for facts |
| What should the applicant do next? | union of all `missing_facts` where `origin == NOT_SUPPLIED`, then re-run |

## Rendering rules a UI must honour

1. Never collapse UNKNOWN into NOT_APPLICABLE. They are different answers.
2. Never render a value for an `IndeterminateDerivation`.
3. Never pick a winner from `competing_derivations`.
4. Always surface `verification_status`. `UNVERIFIED` must be visually distinct.
5. `requirement_type` is not always "approval" — use the actual type.
6. `reached_fixed_point: false` means results are partial; say so.
