# Workflow Contract (Milestone 3)

Output shape of the application-layer workflow scheduler.
A live response is in `docs/sample_workflow_persona_b.json`.

This document lives at the repository root, **not** inside `engine-v3/`,
which is a protected read-only subsystem.

---

## What this layer is, and is not

The workflow scheduler is **downstream of** `engine-v3`. It consumes the
requirements the regulatory engine produced and works out how they can be
sequenced.

It **is not** a second regulatory engine. It never evaluates a rule, never
reads `regulatory/rules/`, never changes a requirement's applicability, and
contains no regulatory thresholds. Requirement `state` is copied through
verbatim from the engine and is read-only here.

```
engine-v3 derive()            decides WHAT applies
        ↓
backend/workflow              decides in WHAT ORDER, and HOW LONG
```

---

## Endpoints

### `POST /api/workflow`

```jsonc
{
  "facts": { "annual_turnover": 80000000, "...": "..." },
  "as_of": "2026-08-29",            // optional
  "include_provisional": true,       // optional, default true
  "include_candidate_edges": true    // optional, default true
}
```

### `POST /api/evaluate-with-workflow`

Same request body. Returns `{ "evaluation": ..., "workflow": ... }`.

**Guarantee:** the `evaluation` block is byte-identical to `POST /api/evaluate`
for the same body (modulo the `derived_at` wall-clock timestamp). Asserted by
`test_workflow_regression.TestEndpointInvariance`.

`POST /api/evaluate` is unchanged by this milestone.

---

## Two schedules, never confusable

This is the most important part of the contract.

| | `schedule` | `provisional_schedule` |
|---|---|---|
| `label` | `"COMMITTED"` | `"PROVISIONAL"` |
| Contains | **only APPLICABLE** requirements | APPLICABLE **plus** UNKNOWN |
| Meaning | confirmed to apply on the facts supplied | contingency view; items may prove unnecessary |
| Safe to present as a plan | yes | **no** |

Every schedule carries a `scope_note` stating its meaning in prose, so a UI
cannot render one without the qualification. An UNKNOWN requirement can
**never** appear in `schedule.nodes`.

A UI must never label the provisional schedule as "your timeline", never
show its duration as the headline figure, and never merge the two node sets.

---

## Top-level response

```
workflow_version      contract version
generated_for         as_of, duration_unit, duration_unit_note, engine_summary
nodes                 { requirement_id: WorkflowNode }
edges                 [ WorkflowEdge ]
schedule              Schedule | null   (null when a cycle was detected)
provisional_schedule  Schedule | null
provisional_delta     object   | null
cycles                [[requirement_id, ...]]
graph_diagnostics     coverage and counts
warnings              [ Warning ]
```

## WorkflowNode

```jsonc
{
  "requirement_id": "S-02",
  "name": "Factory Licence",
  "requirement_type": "LICENCE",
  "department": "DISH",
  "authority": "Directorate of Industrial Safety and Health, Maharashtra",
  "statute": "Factories Act, 1948 s.6",
  "state": "APPLICABLE",              // engine-assigned, never mutated
  "confidence": "high",               // engine-assigned, carried through
  "sla": { SlaInfo },
  "inclusion": "SCHEDULED",           // SCHEDULED | PROVISIONAL | EXCLUDED
  "inclusion_reason": "Applicable. Included in the committed schedule.",
  "missing_facts": [],
  "missing_fact_origin": {},
  "quantity": null,
  "document_slots": []                // forward hook, see below
}
```

`document_slots` is an empty list reserved for the document milestone. The
scheduler never reads or writes it; a later layer can attach approval/document
relationships without changing the schedule shape.

## SlaInfo

```jsonc
{
  "kind": "STANDARD",
  "days": 30,
  "raw_value": 30,
  "source": "catalogue.json:sla_days",
  "excluded_from_duration": false,
  "note": null
}
```

| `kind` | condition | duration | scheduled? |
|---|---|---|---|
| `STANDARD` | positive number | `days` | yes |
| `ZERO_DURATION` | exactly `0` | 0 | **yes — a real node** |
| `UNSPECIFIED` | `null` | 0, flagged | yes, flagged |
| `INVALID` | negative / non-numeric | 0, flagged | yes, flagged |

**No SLA is ever invented.** There are no department averages, no
type-based defaults, no interpolation. A `null` stays `null`, the node is
listed in `excluded_from_duration`, and `duration_completeness` becomes
`PARTIAL`, meaning both durations are lower bounds.

`ZERO_DURATION` is not a no-op. It occupies a real graph position, can gate
dependents, and appears in the checklist — it simply consumes no elapsed time.

## WorkflowEdge

```jsonc
{
  "from_id": "S-01",                  // prerequisite
  "to_id": "S-02",                    // dependent
  "dependency_type": "LEGAL",
  "verification_status": "SECONDARY",
  "basis": "Factories Act 1948 s.6 - previous permission ... is a precondition",
  "admitted": true,
  "admission_reason": "Admitted to scheduling. Statute or rule conditions ...",
  "origin": "depends_on",             // depends_on | candidate_dependencies
  "dropped": false,
  "dropped_reason": null
}
```

### Dependency type policy

| type | admitted? | in `edges`? | affects critical path? |
|---|---|---|---|
| `LEGAL` | **yes** | yes | yes |
| `OPERATIONAL` | **yes** | yes | yes |
| `PROCESS` | no | yes | no |
| `RECOMMENDED` | no | yes | no |
| `UNVERIFIED` | **never** | yes | no |

`SCHEDULING_ADMITTED = {LEGAL, OPERATIONAL}` is pinned to engine-v3's
`CRITICAL_PATH_TYPES` and asserted equal by
`test_workflow_policy.TestEngineAlignment`. The workflow layer cannot widen it.

**`candidate_dependencies` are never admitted**, regardless of their declared
type — even one typed `LEGAL` with status `VERIFIED`. They are relationships
explicitly recorded as retracted or unconfirmed. Promoting one is a regulatory
decision made by editing `dependencies.json` under domain review.

Edges are retained in the response even when dropped, with `dropped_reason`:
`PREREQUISITE_NOT_APPLICABLE`, `PREREQUISITE_IN_CONFLICT`,
`PREREQUISITE_NOT_IN_RESULT`, `MALFORMED_NO_REQUIREMENT_ID`.

## Schedule

```jsonc
{
  "label": "COMMITTED",
  "scope_note": "COMMITTED: contains only requirements the engine resolved ...",
  "topological_order": ["E-05", "E-08", "...", "S-01", "S-02"],
  "parallel_bands": [["E-05","E-08","F-02","..."], ["S-02"]],
  "nodes": { "S-02": { ScheduledNode } },
  "sequential_duration_days": 189,
  "parallel_duration_days": 60,
  "critical_paths": [["F-02"], ["S-01","S-02"]],   // ALWAYS a list of lists
  "critical_path_duration_days": 60,
  "duration_completeness": "COMPLETE",             // COMPLETE | PARTIAL
  "excluded_from_duration": [],
  "schedule_confidence": "medium",
  "confidence_basis": "Weakest admitted scheduling dependency has ...",
  "duration_unit": "sla_days"
}
```

`critical_paths` is **always a list of lists**. Multiple critical paths are
normal — Persona B currently has two. A UI must not assume one.

`schedule_confidence` follows engine-v3's weakest-link pattern: any admitted
edge with `UNVERIFIED` gives `low`, any `SECONDARY` gives `medium`, all
`VERIFIED` gives `high`, and no admitted edges gives `not_applicable`.

## ScheduledNode

```jsonc
{
  "requirement_id": "S-02",
  "earliest_start_day": 30,
  "earliest_finish_day": 60,
  "latest_start_day": 30,
  "latest_finish_day": 60,
  "slack_days": 0,                    // null if any path touches UNSPECIFIED
  "on_critical_path": true,
  "depth": 1,
  "duration_days": 30,
  "duration_is_lower_bound": false,
  "blocks": [],
  "blocks_transitively": [],
  "blocked_by": ["S-01"]
}
```

`slack_days` is `null` whenever the node lies on a path touching an
`UNSPECIFIED` or `INVALID` duration. Slack computed through an unknown
duration would be fiction.

## provisional_delta

```jsonc
{
  "additional_requirements": [
    {
      "requirement_id": "V-01",
      "name": "Consent to Establish",
      "duration_days": 60,
      "on_provisional_critical_path": true,
      "missing_facts": ["mpcb_category"],
      "explanation": "Consent to Establish may add approximately 60 sla_days if mpcb_category confirms that it applies. It would fall on the critical path, so it would extend the overall timeline rather than run alongside other work."
    }
  ],
  "additional_node_count": 3,
  "committed_duration_days": 60,
  "provisional_duration_days": 120,
  "critical_path_change_days": 60,
  "critical_path_changed": true,
  "unlocked_by_facts": ["in_esic_implemented_area", "mpcb_category"],
  "summary_explanation": "Supplying in_esic_implemented_area and mpcb_category could extend the timeline by up to 60 sla_days, from 60 to 120. The critical path would change."
}
```

`explanation` is pre-composed prose the UI renders directly. It is generated
from the schedule arithmetic, not by a language model.

## graph_diagnostics

```jsonc
{
  "node_count": 13,
  "scheduled_node_count": 10,
  "provisional_node_count": 3,
  "excluded_node_count": 0,
  "edge_count_total": 4,
  "edge_count_admitted": 2,
  "edge_count_dropped": 0,
  "edge_count_candidate": 2,
  "nodes_with_dependency_record": 3,
  "nodes_without_dependency_record": 10,
  "dependency_data_coverage": 0.2308,
  "critical_path_count": 2,
  "top_blockers": [ ... ]
}
```

## Warnings

| type | severity | meaning |
|---|---|---|
| `WORKFLOW_CYCLE` | error | cycle among admitted edges; no schedule produced |
| `CONFLICT_EXCLUDED_FROM_SCHEDULE` | error | CONFLICT requirement omitted from both schedules |
| `BLOCKED_BY_CONFLICT` | error | a scheduled node depended on a CONFLICT node |
| `DEPENDENCY_TARGET_UNKNOWN` | error | prerequisite absent from every engine bucket |
| `SLA_INVALID` | error | unusable `sla_days` in the catalogue |
| `CATALOGUE_ENTRY_MISSING` | error | requirement returned but not in the catalogue |
| `MALFORMED_DEPENDENCY` | error | dependency entry is not a well-formed object |
| `SLA_UNSPECIFIED` | warning | `sla_days` is null; durations are lower bounds |
| `SPARSE_DEPENDENCY_DATA` | warning | >50% of requirements have no dependency record |
| `NO_SCHEDULING_CONSTRAINTS` | warning | zero admitted edges |
| `PROVISIONAL_SCHEDULE_DIFFERS` | warning | unknown facts would change the timeline |
| `DEPENDENCY_TARGET_OUT_OF_SCOPE` | info | prerequisite is NOT_APPLICABLE; edge dropped |
| `UNVERIFIED_EDGE_PRESENT` | info | candidate edge recorded, never admitted |
| `DUPLICATE_EDGE` | info | duplicate dependency ignored |
| `MANY_CRITICAL_PATHS` | info | enumeration truncated at 20 |

---

## Reading the duration figures honestly

Persona B currently reports `sequential_duration_days: 189` and
`parallel_duration_days: 60`.

**This must not be presented as a 68% reduction in government approval time.**

`dependency_data_coverage` for Persona B is **0.23**: ten of thirteen
requirements have no dependency record at all, and exactly two admitted
scheduling edges exist. The apparent parallelism is produced mainly by the
*absence* of recorded dependency data, not by a finding that these approvals
are genuinely unconstrained.

As `dependencies.json` is populated, this figure will move toward the
sequential total — and that is correct behaviour, not a regression.

`SPARSE_DEPENDENCY_DATA` fires whenever coverage is below 0.5, and its message
says so explicitly. A UI must surface it alongside any duration figure.

The defensible finding for Persona B is the provisional one: **one missing
fact (`mpcb_category`) could double the timeline from 60 to 120 days.** That
is derived from recorded SLAs and a recorded LEGAL dependency, and it does not
depend on the sparse data for its validity.

---

## Calendar days

The catalogue does not state whether `sla_days` are working days or calendar
days. The scheduler therefore treats them as **opaque units**, reports
`duration_unit: "sla_days"`, and performs **no calendar conversion and
produces no dates**. Converting under an assumption would be inventing a
regulatory fact.

This is an open question for the domain lead.

---

## Rendering rules a UI must honour

1. Never present the provisional schedule as confirmed. Show `label` and
   `scope_note`.
2. Never merge committed and provisional node sets.
3. Never assume one critical path.
4. Always surface `SPARSE_DEPENDENCY_DATA` next to any duration figure.
5. Never claim a percentage reduction in approval time from these numbers.
6. When `duration_completeness` is `PARTIAL`, say durations are lower bounds.
7. Show `verification_status` and `basis` on any dependency displayed.
8. Distinguish admitted from non-admitted edges visually.
9. When `schedule` is `null`, show the cycle; do not fabricate an ordering.
10. Render `sla_days` as-is; do not convert to dates.
