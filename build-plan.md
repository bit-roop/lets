# A-to-Z Build Plan
### Unified Approval & Compliance Engine — SIH 2026, PS 26130

---

## 1. WHAT YOU ARE BUILDING, IN ONE PARAGRAPH

A system that takes an entrepreneur's project attributes, **derives** the exact set of approvals they need with a citation for each, **schedules** them as a dependency graph so independent approvals run in parallel, **generates a deduplicated document checklist** across all of them, **validates every document before submission** against format, semantic, cross-document, and temporal rules, and hands officers a **risk-scored queue** with a pooled inspection plan.

It is not a portal that collects applications. It is the reasoning layer that decides what to collect and checks it before anyone wastes a scrutiny cycle on it.

**The one-line pitch:** *MAITRI made the single window statutory. It still asks the applicant which of 119 services applies to them. We answer that question, and we check the paperwork before it's submitted.*

---

## 2. THE END-TO-END JOURNEY

### Applicant side

```
  1  Choose stage         new setup / expansion / renewal / change of product
  2  Progressive intake   12–18 questions (from a bank of ~95, rest suppressed)
  3  Live constraints     contradictions blocked as you type
  4  Derivation           approval set + reasons + citations + suppressed list
  5  Schedule             DAG → critical path → realistic production date
  6  Checklist            ~40 unique docs, deduplicated from ~150 submissions
  7  Collection           fetch (DigiLocker/API) where possible, upload otherwise
  8  Validation           6 layers, findings with plain-language remedies
  9  Readiness            per-approval score; submit only when green
 10  Submission package   per-department bundles, pre-validated
 11  Tracking             SLA clocks, alerts, grievance escalation
 12  Renewal calendar     seeded automatically from issued approvals
```

### Officer side

```
  A  Risk-scored queue     low-risk auto-cleared, high-risk detailed scrutiny
  B  Pre-validated intake  format/consistency already checked
  C  Flagged findings      what to look at and why, with the rule cited
  D  Pooled inspections    MPCB + DISH + Fire + FSSAI in one visit
  E  Bottleneck analytics  where applications actually stall
```

---

## 3. SYSTEM ARCHITECTURE

```
┌──────────────────── FRONTEND (React + Tailwind) ────────────────────┐
│  Intake wizard  │  Checklist  │  Timeline  │  Upload  │  Officer UI │
└─────────────────────────────┬───────────────────────────────────────┘
                              │  REST (JSON)
┌─────────────────────────────┴───────────────────────────────────────┐
│                      API LAYER (FastAPI)                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐   ┌──────────────┐   ┌────────────────────────┐    │
│  │ CONSTRAINT  │   │  DERIVATION  │   │    DAG SCHEDULER       │    │
│  │  ENGINE     │──▶│    ENGINE    │──▶│    (networkx)          │    │
│  │             │   │              │   │                        │    │
│  │ 15 mutual-  │   │ evaluate()   │   │ topo sort              │    │
│  │ exclusion   │   │ over rules   │   │ longest path           │    │
│  │ rules       │   │ .json        │   │ parallel clusters      │    │
│  └─────────────┘   └──────┬───────┘   └────────────────────────┘    │
│                           │                                         │
│                           ▼                                         │
│                  ┌──────────────────┐                               │
│                  │  DOC REQUIREMENT │  union across approvals,      │
│                  │  DEDUPLICATOR    │  then dedupe by doc_id        │
│                  └────────┬─────────┘                               │
│                           ▼                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              DOCUMENT PIPELINE                               │   │
│  │  router → [A: fetch] [B: OCR+regex] [C: local LLM] [D: human]│   │
│  │        → validators (6 layers) → findings                    │   │
│  └────────────────────────┬─────────────────────────────────────┘   │
│                           ▼                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │      CROSS-DOCUMENT CONSISTENCY + RISK SCORING               │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
        │                    │                       │
   rules/*.json         SQLite/Postgres        Ollama (optional)
   (versioned,          (applications,         (Tier C only,
    citable)             findings, docs)        local, free)
```

**Key property:** rules live in JSON files, not code. A teammate who can't write Python can add approvals while you build the engine. This also means your "we handle 40 approvals" claim is checkable by opening a folder.

---

## 4. DATA MODEL

```python
# ─── Rules (versioned, citable — loaded from JSON at boot) ───
Rule:
    rule_id, version, approval_id
    condition          # nested all/any/not tree
    effect             # {requires: [], excludes: [], adds_documents: []}
    authority, sla_days
    legal_basis        # {statute, instrument, url, effective_from, supersedes}
    last_verified, confidence

Approval:
    approval_id, name, authority, department
    depends_on: [approval_id]     # the DAG edges
    documents: [doc_id]
    sla_days, fee_formula
    validity_years, renewal_lead_days

DocumentSpec:
    doc_id, name, tier              # A / B / C / D
    source_system                   # for tier A
    extract_spec                    # anchors + patterns, for tier B
    validators: [validator_name]
    freshness_days

# ─── Runtime ───
Application:
    app_id, applicant_id, stage, created_at
    facts: dict                     # the answer vector from intake

DerivedApproval:
    app_id, approval_id
    reason                          # which rule fired, human-readable
    rule_id, citation
    status                          # not_started/docs_pending/ready/submitted/issued
    earliest_start, earliest_finish # from DAG
    on_critical_path: bool

DocumentRequirement:
    app_id, doc_id
    required_by: [approval_id]      # ← the dedup story lives here
    status

DocumentSubmission:
    submission_id, app_id, doc_id
    source                          # fetched / uploaded
    file_hash, perceptual_hash
    extracted_fields: dict
    extraction_confidence

Finding:
    submission_id (nullable — cross-doc findings span several)
    check_id, severity, message, remedy, legal_basis
    resolved: bool
```

The `required_by` array is what powers your headline number. When PAN appears in eight approvals, you show `required_by` has eight entries and you asked once.

---

## 5. BUILD PHASES

### Phase 0 — Foundations (2–3 hours)

```
project/
├── backend/
│   ├── main.py                 FastAPI app
│   ├── engine/
│   │   ├── evaluator.py        the 25-line condition evaluator
│   │   ├── derivation.py       run rules → approval set
│   │   ├── constraints.py      15 intake contradiction rules
│   │   ├── scheduler.py        networkx DAG + critical path
│   │   └── dedup.py            document requirement union
│   ├── documents/
│   │   ├── router.py           ← extraction_router.py
│   │   ├── validators.py       ← validators.py
│   │   ├── consistency.py      cross-document checks
│   │   └── risk.py             scoring
│   ├── rules/
│   │   ├── approvals.json      the catalogue + DAG edges
│   │   ├── rules.json          firing conditions
│   │   └── documents.json      doc specs
│   └── db.py                   SQLite
└── frontend/
    └── src/
        ├── Wizard.jsx
        ├── Checklist.jsx
        ├── Timeline.jsx
        ├── Upload.jsx
        └── Officer.jsx
```

```bash
pip install fastapi uvicorn networkx pydantic pypdf pytesseract pillow imagehash
npm create vite@latest frontend -- --template react
npm i tailwindcss reactflow lucide-react
```

**Seed data target:** 25 approvals, 40 rules, 30 document specs. That covers both demo personas completely. Do not try for all 119 MAITRI services — depth beats breadth in a demo.

### Phase 1 — Derivation (core; nothing works without it)

1. `evaluator.py` — the recursive condition evaluator (already written)
2. `rules.json` — seed 40 rules for the two personas, each with a `legal_basis`
3. `derivation.py` — run every rule against facts, collect requires/excludes, **record which rule fired and why**
4. `constraints.py` — the 15 contradiction rules
5. Wizard with progressive disclosure

**Done when:** entering Persona A's facts yields ~10 approvals with reasons; Persona B yields ~25; and setting MIDC=Yes + authority=Municipal Corporation blocks with an explanation.

### Phase 2 — Scheduling

1. `approvals.json` gains `depends_on` edges
2. `networkx.DiGraph`, `topological_sort`, longest path for the critical path
3. Compute sequential total vs. DAG total → the time-saved number
4. Timeline UI with critical path highlighted

**Done when:** you can state "sequential: 214 days, parallelised: 96 days, saving 118 days" and point at which approvals form the critical path.

### Phase 3 — Documents

1. `dedup.py` — union document requirements across derived approvals, group by `doc_id`, record `required_by`
2. Upload endpoint → router → validators → findings
3. Tier A as clearly-labelled mocks; Tier B for 5–6 real documents
4. Findings UI: severity, plain-language message, remedy, citation
5. Cross-document consistency once ≥2 documents are present

**Done when:** uploading a company application with a director's personal PAN produces "PAN belongs to an individual, but you declared a private limited company" instantly.

### Phase 4 — Officer view (only if time)

Risk score, flagged queue, pooled inspection suggestion, bottleneck chart.

### Phase 5 — Polish (never skip)

Seed both personas as one-click demo buttons. Rehearse the demo four times. Prepare answers to the five hard questions in §8.

---

## 6. HOUR-BY-HOUR (36-hour finale)

| Hours | Work | Owner |
|---|---|---|
| 0–2 | Scaffold, schemas agreed, personas defined | all |
| 2–6 | Evaluator + derivation + first 20 rules | BE1 |
| 2–6 | Wizard UI with progressive disclosure | FE1 |
| 4–8 | Remaining 20 rules + constraints | BE2 |
| 6–10 | Checklist UI + dedup display | FE2 |
| 8–12 | DAG scheduler + critical path | BE1 |
| 10–14 | Timeline visualisation | FE1 |
| 12–16 | Document router + Tier B extractors | BE2 |
| 14–18 | Upload UI + findings display | FE2 |
| 16–20 | Validators wired + cross-doc consistency | BE1 |
| 18–24 | **Integration. Everything talks to everything.** | all |
| 24–28 | Officer dashboard + risk scoring | BE2 + FE1 |
| 28–31 | Seed data, demo personas, sample documents | all |
| 31–34 | **Rehearse ×4. Fix only what breaks on stage.** | all |
| 34–36 | Buffer. Do not add features here. | — |

**Hard rule:** feature freeze at hour 28. Teams lose on a broken demo far more often than on a thin one.

---

## 7. THE DEMO SCRIPT (7 minutes)

**0:00 — The problem, with a number.**
"A fruit processing unit in Maharashtra needs around 25 approvals from 8 departments, submits about 40 unique documents 150 times, and typically takes 8–14 months. MAITRI consolidated 119 services into one portal — but it still asks the applicant which ones apply to them, and it accepts contradictory answers."

**0:45 — Intake, and the catch.**
Fill Persona B. Set MIDC = Yes, then authority = Municipal Corporation.
System blocks: *"An MIDC plot falls under MIDC's planning authority, not the Municipal Corporation. Which is correct?"*
"MAITRI accepts this contradiction. It surfaces weeks later as a rejection."

**1:30 — Derivation with reasons.**
25 approvals appear. Expand one: *"Boiler registration — required because you operate a 500-litre boiler. Boilers Act 1923, threshold 25 litres."*
Then show the suppressed list: *"12 approvals excluded, including NA permission — your plot is already in an MIDC industrial zone."*
"Knowing what you don't need saves as much time as knowing what you do."

**2:30 — The live variable change. This is the moment.**
Change turnover from ₹1.4 crore to ₹1.6 crore.
FSSAI Registration becomes State Licence, document count jumps, the citation to the FSSAI order of 13 March 2026 appears.
"These thresholds changed on 1 April this year. Our rules are versioned with effective dates, so an application filed in March is still judged under the old rule."

**3:15 — The DAG.**
"Sequentially: 214 days. As a dependency graph: 96 days. The critical path runs through CTE, building permission, construction, occupancy, CTO, factory licence, FSSAI."

**4:00 — Deduplication.**
"40 unique documents. Required 150 times across 12 applications. We ask once."
Show PAN with `required_by` listing eight approvals.

**4:45 — Validation, live.**
Paste a GSTIN with one character altered → checksum failure, instantly.
Upload a company application with a director's personal PAN → *"PAN belongs to an individual; you declared a private limited company."*
Show the lease-expiry rule firing.
"None of these require a network call or a model. Pure arithmetic, microseconds."

**5:45 — Officer view.**
Risk-scored queue, pooled inspection: "MPCB, DISH, Fire and FSSAI all need to visit. One slot instead of four."

**6:30 — Close.**
"We deliberately did not use an LLM to decide approvals. Compliance decisions must be deterministic, auditable, and citable. Every rule points at the notification that created it. The AI we do use is advisory — it reads project reports and flags inconsistencies for the officer. The officer decides."

---

## 8. THE FIVE QUESTIONS YOU WILL BE ASKED

**"MAITRI already does this."**
> MAITRI is the statutory single window under the MAITRI Act 2023 and it consolidates 119 state services. Two gaps remain. It asks the applicant to self-declare their pollution category and their applicable services — we derive both. And it covers state departments; a food unit also needs FSSAI, BIS, and IEC from central systems. We're a layer above, not a replacement.

**"How do you know your rules are correct?"**
> Every rule carries a citation, an effective date, and a last-verified date. Rules unverified for 12 months are visibly flagged in the admin view. We're not claiming the rules are permanently right — we're claiming they're auditable and maintainable, which is the only honest claim a compliance system can make.

**"What happens when the law changes?"**
> A JSON edit, not a deployment. FSSAI's thresholds changed on 1 April 2026 — Basic Registration went from ₹12 lakh to ₹1.5 crore. In our system that's one file, one new version, with `supersedes` pointing at the old rule so past applications still resolve correctly.

**"Is your AI going to approve applications?"**
> No. Derivation and validation are deterministic rules. The only model use is advisory — reading a project report and flagging inconsistencies for the officer to look at. We never auto-reject on a model's reading.

**"Can this scale beyond food?"**
> The engine is sector-agnostic; food is data. *(Have 5 textile rules seeded to prove it — takes 20 minutes and it's the strongest possible answer.)*

---

## 9. WHAT NOT TO CLAIM

- **Don't claim live government API integration** unless you have it. Label mocks as simulated. Getting caught here discredits everything else.
- **Don't claim deemed approval** unless you can cite the provision that permits it.
- **Don't say MAITRI is broken.** Say you extend it. The jury is from the same government.
- **Don't quote an accuracy percentage for OCR** unless you measured it on real scanned documents.
- **Don't claim all 119 services.** Say 25 approvals fully modelled, architecture proven to extend.

---

## 10. IF YOU ONLY HAVE TIME FOR THREE THINGS

1. **Derivation with citations and suppression** — the intellectual core
2. **The live variable change** — turnover crossing ₹1.5 crore, rules visibly re-firing
3. **Instant document validation** — the corrupted GSTIN, the wrong PAN type

Those three, working reliably, beat all five phases half-finished. Every time.
