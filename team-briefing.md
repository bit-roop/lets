# TEAM BRIEFING
## Smart India Hackathon 2026 — Problem Statement 26130
### Government of Maharashtra | Maharashtra State Innovation Society | Smart Automation | Software

---

# PART I — UNDERSTANDING THE PROBLEM

## 1.1 The problem in human terms

Meet Ramesh. He has ₹2 crore and wants to open a fruit pulp processing unit near Pune. He knows how to make fruit pulp. He does not know that before he can legally produce a single litre, he needs:

- Permission from the Pollution Control Board **before he pours a foundation** — not after
- A factory licence from a department he has never heard of, called DISH
- Registration of his boiler under a law passed in **1923**
- A food licence whose category depends on his projected turnover
- A fire NOC before he can occupy the building
- Roughly twenty other things

Nobody hands him this list. He finds out one approval at a time, usually by being rejected. Each rejection costs weeks. His typical journey takes **8 to 14 months**, and a large part of that delay isn't government slowness — it's Ramesh submitting incomplete or inconsistent paperwork, and departments sending it back.

Meanwhile the departments have their own problem. They receive applications that are incomplete, internally contradictory, or missing prerequisites. They scrutinise the same PAN card eight times across eight applications. Four different departments each send an inspector to the same factory in the same month, separately. No one can see where applications are actually getting stuck.

**That gap — between what the applicant doesn't know and what the department has to keep re-checking — is our problem statement.**

## 1.2 What the problem statement actually asks for

Read carefully, it asks for nine things:

1. Generate a **customised approval checklist**
2. **Guide applicants** through documentation
3. **Pre-validate** submissions
4. **Reuse verified data**
5. **Coordinate parallel** departmental workflows
6. **Schedule inspections**
7. **Track service-level timelines** and issue alerts
8. A **single dashboard** for applications, approvals, renewals, incentives
9. Optional: regulatory knowledge engine, risk-based scrutiny, common inspection planning, grievance escalation, delay analytics

Note the order. **"Customised approval checklist" comes first**, and "regulatory knowledge engine" is listed as a component. That's the heart of the problem, and it's the part most teams will skip because it's the hardest and least glamorous.

## 1.3 Where most teams will fail

Predict the competition honestly:

- **80% will build a portal.** Login, upload documents, status tracker, a dashboard with pie charts. It will look fine and be indistinguishable from twenty other submissions.
- **Many will bolt on a chatbot** that answers regulatory questions from an LLM. It will hallucinate approvals. A jury member who knows the domain will catch it in one question.
- **Almost nobody will model the regulations as data.** They'll hardcode a list of approvals, which means their system can't explain *why* an approval applies and can't survive a threshold change.
- **Almost nobody will have checked what already exists.** They'll pitch a single-window portal to the government that already built one.

**We win by doing the boring, correct thing very well: modelling regulation as versioned, citable data, and reasoning over it deterministically.**

## 1.4 What already exists — read this before you pitch anything

Maharashtra already runs **MAITRI 2.0**, launched February 2025 by the Chief Minister. It consolidates **119 services from 15 departments** into one portal with real-time tracking. It has statutory backing under the **Maharashtra Industry, Trade and Investment Facilitation Act, 2023**, which makes MAITRI the Nodal Agency for the state's Single Window System and gives its Empowered Committee decisions binding force.

**The evaluators are from Maharashtra's own innovation society. They know this. Pitching "a single window portal" to them is pitching them their own product back.**

But there are real gaps, and we found them by actually using MAITRI's questionnaire:

**Gap 1 — It asks instead of deriving.** MAITRI's "Know Your Approvals" form asks the applicant to pick their pollution category (Red / Orange / Green) from a dropdown. This is the highest-consequence field in the whole form and it's a guess. Wrong category means wrong consent path, wrong fee, wrong documents, rejection weeks later.

**Gap 2 — It accepts contradictions.** We filled the form. We answered "Is your land under MIDC jurisdiction? **Yes**" and then "Select the relevant authority for the factory site: **Municipal Corporation**." Those are mutually exclusive — an MIDC plot is under MIDC's planning authority. The form accepted both without comment.

**Gap 3 — Questions that miss the common case.** It asks "Are you a boiler **manufacturer**?" A food unit *uses* a boiler; it doesn't make them. Boiler registration is triggered by *operating* one above 25 litres — which the form never asks. A truthful applicant answers "No" and never learns they need it.

**Gap 4 — No food-specific coverage at all.** The entire questionnaire contains zero questions about FSSAI, product category, turnover, or capacity. For a food unit, FSSAI is the defining licence. It's central (FoSCoS), MAITRI is state, and nothing bridges them.

**Gap 5 — Statutorily permissive.** The MAITRI Act says an applicant **"may"** apply through the Single Window System. Not "shall." So it's a delivery channel, not a gate. Central approvals — FSSAI, BIS, IEC, GST, MCA incorporation — sit entirely outside it.

**Our honest positioning:** *MAITRI made the single window statutory and consolidated the state's services. It still asks the applicant which of the 119 apply to them, and it accepts contradictory answers. We answer that question, we catch the contradictions, and we bridge state and central approvals.*

We **extend** MAITRI. We never say it's broken.

---

# PART II — OUR SOLUTION

## 2.1 The core insight

Everything in this problem statement is CRUD work — uploads, dashboards, status trackers, alerts — **except one thing**:

> Given a specific project's attributes, correctly derive the exact set of approvals it needs, in what order, with the legal citation for each.

That derivation is genuinely hard, genuinely valuable, and genuinely defensible. Everything else is plumbing around it.

So we build the derivation engine first and best, and treat the portal as the wrapper.

## 2.2 The five things we build that others won't

**① A versioned, citable regulatory rule graph**
Every rule carries the notification that created it, an effective date, and a last-verified date. When an officer asks "why does this unit need boiler registration," we point at the Boilers Act 1923 and the 25-litre threshold. When rules change, we version them so an application filed in March is still judged under March's rules.

*Concrete proof this matters:* FSSAI's turnover thresholds changed on **1 April 2026**. Basic Registration went from ₹12 lakh to **₹1.5 crore**; Central Licence from ₹20 crore to **₹50 crore**. Every blog and tutorial still shows the old numbers. Any team that seeds their data from a tutorial is wrong on day one. We caught this and our rules carry effective dates.

**② Intake constraint validation**
Fifteen mutual-exclusion rules that block contradictions as the applicant types. The MIDC-vs-Municipal-Corporation contradiction we found in MAITRI gets caught before submission, with a plain-language explanation.

**③ Pre-submission document validation**
Six layers — format/checksum, semantic, cross-document, temporal, authenticity, tamper detection. Around 28 cross-document consistency checks. Departments reject on exactly these grounds; no portal catches them beforehand.

**④ DAG-based parallel scheduling**
Most systems treat approvals as a queue. Reality is a dependency graph — some approvals block others, many can run concurrently. We compute the critical path and show the time saved.

**⑤ Risk-based scrutiny and pooled inspections**
Score applications on consistency and fraud signals. Auto-clear the clean low-risk ones. Pool MPCB, DISH, Fire, and FSSAI into one site visit instead of four.

## 2.3 The numbers that go on slides

| Metric | Value |
|---|---|
| Approvals for an orange-category food unit | ~25, across 8 departments |
| Unique documents | ~40 |
| Times those documents are submitted | ~150, across 12 applications |
| Deduplication factor | **3.75×** — we ask once |
| Typical journey today | 8–14 months |
| Sequential vs. DAG-scheduled critical path | *compute this from real SLAs — it's your headline* |
| Documents validated without any AI | ~65–70% |

**Discipline rule:** every number we quote must be computed by our own system from our own data. No invented statistics. If a jury asks "where did 3.75 come from," we open the code.

---

# PART III — TECHNOLOGY DECISIONS

## 3.1 Rules engine, not an LLM — and why this is a strength

We deliberately do **not** use a language model to decide which approvals apply. Three reasons, and all three are things a government jury cares about:

- **Determinism.** Same inputs must always give the same answer. A model that answers differently on Tuesday is disqualifying for compliance.
- **Auditability.** "Rule FSSAI-CAT-001 v3, citing the FSSAI order of 13 March 2026" is an answer. "The model said so" ends the conversation.
- **No hallucinated approvals.** A model will confidently invent a licence that doesn't exist or omit one that does. Both are worse than a list the applicant Googled.

There's also a practical point: **our rules aren't complex.** They're threshold comparisons and set membership — `turnover > 15000000`, `boiler_litres > 25`, `product_code in orange_list`. That's a 25-line evaluator. Using an LLM here would be solving an easy problem with an expensive, unreliable tool.

**Say this in the pitch.** A team that can explain where it chose *not* to use AI reads as more sophisticated than one that used it everywhere.

## 3.2 Where AI does earn its place

Three narrow spots, all advisory, all off the critical path, all free:

1. **Plain-language explanation** of a rejection
2. **Semantic search** over regulation text
3. **Project report consistency** — reading a 40-page DPR and flagging that the stated capacity doesn't match the machinery list. Genuinely hard for rules, genuinely tedious for an officer.

**Cost: zero.** We run **Ollama** locally with Qwen 2.5 7B or Llama 3.2 3B. No API keys, no rate limits, works if venue wifi dies. For semantic search, `sentence-transformers/all-MiniLM-L6-v2` plus FAISS runs on CPU.

**Non-negotiable rule: the model never auto-rejects.** It flags for the officer. The officer decides.

## 3.3 Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python + FastAPI | Fast to write, auto API docs, team knows it |
| Rules storage | JSON files in `rules/` | **A non-coder can add rules while engineers build the engine** |
| Graph | networkx | Topological sort and longest path in ~20 lines |
| Database | SQLite → Postgres | Zero setup for the hackathon |
| OCR | Tesseract (pytesseract) | Free, offline |
| PDF forensics | pypdf | Metadata, incremental saves, signatures |
| Image hashing | imagehash | Cross-application reuse detection |
| Frontend | React + Vite + Tailwind | Fast iteration |
| Graph UI | React Flow | Dependency visualisation |
| LLM (optional) | Ollama, local | Free, offline, no keys |

```bash
pip install fastapi uvicorn networkx pydantic pypdf pytesseract pillow imagehash
npm create vite@latest frontend -- --template react
npm i tailwindcss reactflow lucide-react
```

## 3.4 The whole engine, so nobody is intimidated

```python
def evaluate(condition, facts):
    if "all" in condition:
        return all(evaluate(c, facts) for c in condition["all"])
    if "any" in condition:
        return any(evaluate(c, facts) for c in condition["any"])
    if "not" in condition:
        return not evaluate(condition["not"], facts)
    val = facts.get(condition["fact"])
    if val is None:
        return False
    op, target = condition["op"], condition["value"]
    return {
        ">": lambda: val > target,   ">=": lambda: val >= target,
        "<": lambda: val < target,   "<=": lambda: val <= target,
        "==": lambda: val == target, "in": lambda: val in target,
        "intersects": lambda: bool(set(val) & set(target)),
    }[op]()
```

That's it. **Everything else is data.** This is why the architecture scales: adding approval #41 is a JSON entry, not code.

## 3.5 A rule, in full

```json
{
  "rule_id": "FSSAI-CAT-001",
  "version": 3,
  "approval_id": "F-02",
  "name": "FSSAI State Licence applicability by turnover",
  "condition": {
    "all": [
      {"fact": "annual_turnover", "op": ">",  "value": 15000000},
      {"fact": "annual_turnover", "op": "<=", "value": 500000000}
    ]
  },
  "effect": {"requires": ["F-02"], "excludes": ["F-01", "F-03"]},
  "authority": "Maharashtra FDA",
  "sla_days": 60,
  "legal_basis": {
    "statute": "Food Safety and Standards Act, 2006",
    "instrument": "FSSAI Order dated 13 March 2026",
    "effective_from": "2026-04-01",
    "supersedes": "FSSAI-CAT-001@v2"
  },
  "last_verified": "2026-08-29",
  "confidence": "high"
}
```

Three fields carry disproportionate weight:

- **`legal_basis`** — without a citation, our engine is an opinion.
- **`effective_from` / `supersedes`** — lets us answer "what were the rules when this application was filed?" Applications filed in March 2026 fall under the *old* FSSAI thresholds. Temporal versioning is not optional in compliance software.
- **`excludes`** — telling an applicant they *don't* need NA permission because their plot is already in an industrial zone saves as much time as telling them what they do need.

---

# PART IV — ARCHITECTURE

```
┌───────────────────── FRONTEND (React + Tailwind) ──────────────────┐
│  Wizard  │  Checklist  │  Timeline  │  Upload  │  Officer Console  │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ REST/JSON
┌──────────────────────────────┴─────────────────────────────────────┐
│                       API LAYER (FastAPI)                          │
│                                                                    │
│  CONSTRAINT ──▶ DERIVATION ──▶ DAG SCHEDULER ──▶ DOC DEDUPLICATOR  │
│  ENGINE         ENGINE         (networkx)         (union by doc_id)│
│  15 rules       evaluate()     critical path                       │
│                 over rules                            │            │
│                                                       ▼            │
│  DOCUMENT PIPELINE                                                 │
│    router → [A: fetch] [B: OCR+regex] [C: LLM] [D: human]          │
│           → 6 validation layers → findings                         │
│                          │                                         │
│                          ▼                                         │
│  CROSS-DOCUMENT CONSISTENCY (28 checks) → RISK SCORE               │
└────────────────────────────────────────────────────────────────────┘
       │                    │                        │
   rules/*.json         SQLite              Ollama (optional, local)
```

## 4.1 The document pipeline, explained

This is the part most likely to confuse the team, so here it is plainly.

**Extraction and validation are different problems.** Validation — once you have the fields — is identical for every document and scales for free. **Extraction** is where documents differ, and it splits into four tiers:

| Tier | What | Count | Method | AI? |
|---|---|---|---|---|
| **A** | Fetchable from a source system — PAN, GST, CIN, Udyam, 7/12, FSSAI | ~10 | API / DigiLocker | **No extraction at all** |
| **B** | Fixed-layout certificates — MPCB consent, factory licence, fire NOC, boiler cert, water test | ~18 | OCR + anchored regex | **No** |
| **C** | Free-form — DPR, MoA object clause, lease deed conditions | ~8 | Local LLM | Yes, advisory only |
| **D** | Visual — layout plans, site photos | ~3 | Route to officer | No |

**Roughly 65–70% needs no AI whatsoever.**

**Anchored extraction** is the technique that makes Tier B work. Instead of "the consent number is at pixel (340, 118)," we say "find the label *Consent No*, then take the next token matching this pattern." Layout differences between MPCB regional offices don't break it. OCR noise doesn't break it.

**Honest caveat for the team:** we tested this on clean text and got perfect extraction. Tesseract on a photocopied, skewed, stamped government certificate will realistically hit **60–75%**, worse on Marathi documents. That's fine — our confidence scoring routes low-confidence extractions to manual review. But **use good scans in the demo** and don't claim an accuracy number we haven't measured.

## 4.2 The six validation layers

1. **Format / checksum** — GSTIN Luhn mod-36, Aadhaar Verhoeff, PAN/CIN regex. Microseconds, no network.
2. **Semantic** — does the encoded meaning match the declaration? PAN's 4th character is `P` for individual, `C` for company. A company submitting a director's personal PAN gets caught instantly.
3. **Cross-document** — GSTIN characters 3–12 **are** the PAN. String comparison. Strongest free check we have.
4. **Temporal** — freshness windows, sequencing (CTE before construction), and the lease-versus-licence rule.
5. **Authenticity** — API/DigiLocker verification. **Mocked for the hackathon, labelled as mocked.**
6. **Tamper detection** — PDF producer metadata, incremental save counts, perceptual hashing for cross-application reuse.

## 4.3 Two checks a single-department portal structurally cannot do

Emphasise these — they're the architectural argument for a unified platform:

- **Cross-application file reuse.** The same NABL water test report resubmitted for three years with the date changed. Only a system seeing all applications can detect this.
- **Investment reconciliation.** MPCB fees are slabbed on capital investment. Comparing the MPCB declaration against the Udyam certificate, CA certificate, and incentive application catches under-declaration. No single department sees all four.

---

# PART V — WHO DOES WHAT

Assuming six people. Adjust to your actual team.

| Role | Owns | Needs to know |
|---|---|---|
| **BE-1 (Engine)** | evaluator, derivation, constraints | Python. Most important role — start here day one. |
| **BE-2 (Documents)** | router, validators, consistency, OCR | Python, regex. Second most important. |
| **BE-3 (Scheduler + API)** | networkx DAG, FastAPI routes, DB | Python, graphs |
| **FE-1 (Applicant)** | wizard, checklist, timeline | React, Tailwind |
| **FE-2 (Officer + Upload)** | upload UI, findings display, officer console | React, Tailwind |
| **Domain / Content** | seeds `rules.json`, verifies citations, writes demo data | **No coding required.** Reads government sites and fills JSON. |

**The Domain role is not a consolation prize — it's on the critical path.** Without seeded rules, the engine does nothing. This person also prepares the answers to jury questions and verifies every citation. Give it to whoever is most careful and most comfortable reading dense material.

---

# PART VI — THE PATH

## Stage 1 — Before you write any code (do this now)

- [ ] Everyone reads this document and the knowledge base
- [ ] Fix the **two demo personas** (see below) and freeze them
- [ ] Domain lead verifies the **seven open items** in Part VIII
- [ ] Agree the JSON schemas for `rules.json`, `approvals.json`, `documents.json`
- [ ] Scaffold the repo; everyone can run it locally

## Stage 2 — Derivation (nothing works without this)

- [ ] `evaluator.py` — the 25-line function
- [ ] `rules.json` — 40 rules, every one with a citation
- [ ] `derivation.py` — must record **which rule fired and why**, not just the result
- [ ] `constraints.py` — 15 contradiction rules
- [ ] Wizard with progressive disclosure

**Done when:** Persona A yields ~10 approvals, Persona B ~25, and the MIDC contradiction is blocked with an explanation.

## Stage 3 — Scheduling

- [ ] `depends_on` edges in `approvals.json`
- [ ] networkx DAG, topological sort, critical path
- [ ] Sequential vs. parallel comparison computed
- [ ] Timeline UI with critical path highlighted

## Stage 4 — Documents

- [ ] Requirement dedup with `required_by` tracking
- [ ] Router + Tier B extractors for 5–6 documents
- [ ] Validators wired to findings
- [ ] Cross-document consistency once ≥2 documents present

**Done when:** uploading a director's personal PAN on a company application instantly says so.

## Stage 5 — Officer view *(only if time)*

Risk scoring, flagged queue, pooled inspection suggestion, bottleneck chart.

## Stage 6 — Polish *(never skip)*

One-click persona seeding. **Rehearse four times.** Prepare jury answers.

## 6.1 The two personas — freeze these early

**Persona A — Shree Ganesh Bakery, Pune municipal limits**
Proprietorship · 6 workers · no boiler · turnover ₹40 lakh · Green category
→ ~10 approvals. FSSAI **Registration** (not licence). No factory licence — under the worker threshold. No boiler registration. No BIS.

**Persona B — Sahyadri Foods Pvt Ltd, MIDC Ranjangaon**
Private limited · 45 workers · 500-litre boiler · turnover ₹8 crore · Orange category
→ ~25 approvals with a real dependency graph.

**The demo is switching between them and changing one variable live.** Bump turnover from ₹1.4 crore to ₹1.6 crore and watch FSSAI Registration become a State Licence with the March 2026 citation appearing. Add a boiler, watch two approvals and four documents appear. Move the plot from MIDC to gram panchayat, watch NA permission appear and MIDC building permission drop.

**That thirty-second sequence is worth more than a list of thirty approvals**, because it shows the engine *reasoning* rather than displaying.

## 6.2 Hour-by-hour for a 36-hour finale

| Hours | Work |
|---|---|
| 0–2 | Scaffold, schemas agreed, personas frozen |
| 2–8 | Engine + first 20 rules ‖ wizard UI |
| 4–12 | Remaining rules + constraints ‖ checklist UI |
| 8–14 | DAG scheduler ‖ timeline UI |
| 12–18 | Document router + Tier B ‖ upload UI |
| 16–20 | Validators + cross-document consistency |
| 18–24 | **Integration. Everything talks to everything.** |
| 24–28 | Officer dashboard + risk scoring |
| 28–31 | Seed data, personas, sample documents |
| 31–34 | **Rehearse ×4. Fix only what breaks on stage.** |
| 34–36 | Buffer. **Add nothing.** |

**Feature freeze at hour 28.** Teams lose on broken demos far more often than on thin ones.

---

# PART VII — THE DEMO (7 minutes)

**0:00 — Problem, with a number.**
"A fruit processing unit in Maharashtra needs ~25 approvals from 8 departments, submits ~40 unique documents 150 times, and takes 8–14 months. MAITRI consolidated 119 services — but it still asks the applicant which ones apply, and it accepts contradictory answers."

**0:45 — Intake, and the catch.**
Set MIDC = Yes, authority = Municipal Corporation. System blocks with an explanation.
"MAITRI accepts this. It surfaces as a rejection weeks later."

**1:30 — Derivation with reasons.**
25 approvals with citations. Then the suppressed list: "12 excluded — you don't need NA permission, your plot is already in an industrial zone."

**2:30 — The live change. This is the moment.**
Turnover ₹1.4 cr → ₹1.6 cr. FSSAI Registration becomes State Licence. Citation appears.
"These thresholds changed on 1 April this year. Our rules are versioned by effective date."

**3:15 — The DAG.** Sequential vs. parallel, critical path highlighted.

**4:00 — Deduplication.** PAN with `required_by` showing eight approvals. "We ask once."

**4:45 — Validation, live.** Corrupted GSTIN → checksum failure. Personal PAN on a company application → caught. Lease expiry rule → fires.
"No network call, no model. Pure arithmetic, microseconds."

**5:45 — Officer view.** Risk queue, pooled inspection.

**6:30 — Close.**
"We deliberately did not use an LLM to decide approvals. Compliance decisions must be deterministic, auditable, and citable. The AI we do use is advisory — it reads project reports and flags inconsistencies. The officer decides."

## 7.1 The five questions you will be asked

**"MAITRI already does this."**
> MAITRI is the statutory single window and consolidates 119 state services. Two gaps: it asks applicants to self-declare their category and applicable services — we derive both. And it's state-only; food units also need FSSAI, BIS, and IEC centrally. We're a layer above, not a replacement.

**"How do you know your rules are correct?"**
> Every rule carries a citation, an effective date, and a last-verified date. Rules unverified for 12 months are flagged in the admin view. We're not claiming permanent correctness — we're claiming auditability and maintainability, which is the only honest claim compliance software can make.

**"What happens when the law changes?"**
> A JSON edit, not a deployment. FSSAI thresholds changed on 1 April 2026 — Basic Registration went from ₹12 lakh to ₹1.5 crore. For us that's one file and one new version, with `supersedes` so past applications still resolve correctly.

**"Will your AI approve applications?"**
> No. Derivation and validation are deterministic rules. The model is advisory only, and never auto-rejects.

**"Does this work beyond food?"**
> The engine is sector-agnostic; food is data. *(Seed 5 textile rules — 20 minutes, and it's the strongest possible answer.)*

## 7.2 What we never claim

- **No fake API integrations.** Label mocks as simulated. Getting caught here discredits everything.
- **No deemed approval** unless we cite the provision permitting it.
- **Never say MAITRI is broken.** We extend it. The jury is from the same government.
- **No OCR accuracy percentage** we haven't measured on real scans.
- **Not all 119 services.** Say: 25 approvals fully modelled, architecture proven to extend.

---

# PART VIII — OPEN ITEMS (Domain lead owns these)

Verify from the department, **not from a blog**:

1. **Factories Act worker threshold in Maharashtra.** Central Act says 10 with power / 20 without. Several states amended it upward. This single number decides whether an entire approval branch fires. → DISH Maharashtra.
2. **Current MPCB category annexure**, including the new **Blue** category from the 2025 CPCB harmonisation. Most references still show only four categories.
3. **FSSAI KoB eligibility matrix on FoSCoS** — some businesses need a State or Central licence on *capacity*, regardless of turnover. The turnover table alone will mis-categorise them.
4. **Udyam investment and turnover limits** — revised recently.
5. **Municipal trade/health licence checklist** for our demo city. No state-wide standard exists.
6. **Fire NOC applicability thresholds** by height and occupancy class.
7. **Deemed-NA scope** under the Land Revenue Code amendments.

**Best seed source:** MAITRI's own "Know Your Approvals" section publishes per-approval document checklists and procedures, publicly. Scrape it and Tier 3 stops being guesswork.

---

# PART IX — RISKS

| Risk | Mitigation |
|---|---|
| Rules not seeded in time | Domain lead starts **before** engine code. Rules are just JSON. |
| OCR fails on real documents | Confidence routing to manual review. Use clean scans in the demo. |
| Scope creep | Feature freeze hour 28. Phases 1 + 4 beat all six half-done. |
| Jury says "MAITRI exists" | Rehearse the answer in §7.1. Never disparage it. |
| Demo breaks on stage | Rehearse ×4. Seed personas as one-click. Have a recorded backup. |
| Someone claims a fake integration | Agree now: **all mocks labelled in the UI.** |
| Wrong threshold in a rule | Every rule has `last_verified`. Domain lead signs off before the demo. |

---

# PART X — GLOSSARY

Nobody is expected to know these. Learn them before you talk to a jury.

| Term | Meaning |
|---|---|
| **MAITRI** | Maharashtra Industry, Trade and Investment Facilitation Cell — the state single window. Statutory since 2023. |
| **MIDC** | Maharashtra Industrial Development Corporation — runs industrial estates. On MIDC land, MIDC is the planning authority, not the municipality. |
| **MPCB** | Maharashtra Pollution Control Board. |
| **CTE / CTO** | Consent to Establish / Consent to Operate. CTE comes **before construction**; CTO before production. |
| **R/O/G/W/B** | Pollution categories: Red, Orange, Green, White, and now Blue. Drives fees, documents, and inspection frequency. |
| **DISH** | Directorate of Industrial Safety and Health — issues factory licences under the Factories Act 1948. |
| **FSSAI** | Food Safety and Standards Authority of India. Central regulator. |
| **FoSCoS** | FSSAI's online licensing portal. |
| **KoB** | Kind of Business — FSSAI's activity classification. Some KoBs force a higher licence category regardless of turnover. |
| **FoSTaC** | FSSAI training programme. One trained supervisor per 25 food handlers. |
| **7/12 (Satbara)** | Maharashtra land record extract. Shows owner, area, encumbrances, tenancy. The most important land document. |
| **NA permission** | Non-Agricultural permission from the Collector, to use agricultural land industrially. |
| **Deemed NA** | Land already in a Development Plan industrial zone may not need NA permission. **Suppressing this requirement is a feature.** |
| **CC / OC** | Commencement Certificate (before construction) / Occupancy Certificate (after). |
| **Udyam** | MSME registration. Gates most incentives. |
| **PESO** | Petroleum & Explosives Safety Organisation — LPG, solvents, ammonia vessels. |
| **CRZ** | Coastal Regulation Zone — extra clearance in coastal districts. |
| **EPR** | Extended Producer Responsibility — plastic packaging registration. **Commonly missed by food units.** |
| **DPR** | Detailed Project Report. |
| **UDIN** | Unique Document Identification Number on CA certificates. Verifiable on the ICAI portal. |
| **DAG** | Directed Acyclic Graph — how we model approval dependencies. |
| **Critical path** | The longest dependency chain. Determines the minimum possible duration. |

---

# PART XI — THE THREE THINGS THAT MATTER MOST

If everything else falls apart, these three win:

1. **Derivation with citations and a visible suppressed list** — proves the engine reasons
2. **The live turnover change re-firing the FSSAI rule** — proves temporal rule versioning
3. **The corrupted GSTIN caught instantly** — proves pre-validation

Nobody else in the room will have all three.

**Start with `rules.json`. Everything depends on it.**
