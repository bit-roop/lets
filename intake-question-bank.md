# Intake Question Bank — Approval Derivation Engine
### Benchmarked against MAITRI "Know Your Approvals" (SIH 2026, PS 26130)

Legend for the **MAITRI** column:
- `✅` — MAITRI asks this, question ID noted
- `⚠️` — MAITRI asks something adjacent but the wording misses the common case
- `❌` — MAITRI does not ask this at all

Legend for **Confidence**: `HIGH` = I'm confident the trigger is real; `VERIFY` = confirm the threshold with the department before coding.

---

## PART 1 — RECONSTRUCTING MAITRI'S QUESTIONNAIRE

What the three screenshots contain, with the branching logic inferred.

### Section 1 — Land
| ID | Question | Options | Inferred purpose |
|---|---|---|---|
| 1 | Does your business require land? | Y/N | Root gate — `No` collapses the entire land branch |
| 1.1 | *(hidden)* | — | Almost certainly fires when 1.2 = No: land acquisition / MIDC plot application assistance |
| 1.2 | Do you possess enough land for business? | Y/N | |
| 1.3 | Specify the nature of land you possess | dropdown (Industrial selected) | Drives NA permission and zoning |
| 1.4 | Does your land fall under MIDC jurisdiction? | Y/N | **Major branch** — switches planning authority |
| 1.5 | *(hidden)* | — | Likely fires when 1.4 = No: Collector / local body sub-questions |
| 1.6 | Electricity requirement | LT / HT / Temporary | HT triggers Electrical Inspector approval |
| 1.7 | Will you install a DG set? | Y/N | MPCB air consent + noise norms |
| 1.8 | Will you deploy a lift? | Y/N | Lift permit, PWD / Electrical Inspector |

### Section 2 — Incorporation
| ID | Question | Options |
|---|---|---|
| 2 | Is your entity registered? | Y/N |
| 2.1 | Type of entity you want to register | Partnership firm / Co-operative Society / Others |
| 2.2 | Nature of your entity | Manufacturing / Services / Trade |
| 2.3 | *(hidden)* | Likely fires when 2 = Yes: existing registration details |
| 2.4 | Type of entity | Micro / Small / Medium *(truncated)* |
| 2.5 | Register the company as | Indian Company / Foreign *(truncated)* |

### Section 3 — Factory Related Clearance
| ID | Question | Options |
|---|---|---|
| 3 | Do you want to set up a Factory / Plant? | Y/N |
| 3.1 | Height of the Factory / Plant | <15 m / >15 m — **fire NOC severity** |
| 3.2 | Relevant authority for the Factory / Plant site | MIDC / Municipal Corporation / Municipal Council |

### Section 4 — Labour Related Approvals
| ID | Question | Options | Triggers |
|---|---|---|---|
| 4 | No. of contract labourers | 20 or more / <20 | CLRA registration at 20+ |
| 4.1 | No. of employees | <10 / 10–20 / 20+ | ESIC at 10+, EPFO at 20+, Factories Act |
| 4.2 | No. of migrant workers | <5 / >5 | Inter-State Migrant Workmen Act |
| 4.3 | No. of motor transport workers | <5 / >5 | Motor Transport Workers Act |

### Section 5 — Boiler
| ID | Question | Options |
|---|---|---|
| 5 | Are you a boiler **manufacturer**? | Y/N |

### Section 6 — Environment
| ID | Question | Options |
|---|---|---|
| 6 | What sector does your business fall under? | dropdown — Red / Orange / Green category |
| 6.1 | Type of waste generated | Hazardous / Bio-medical / Plastic / E-Waste / Solid (multi-select) |
| 6.2 | Will there be tree felling / cutting? | Y/N |

### Section 7 — Other Approvals
| ID | Question | Options |
|---|---|---|
| 7 | Sale/local consumption or manufacture of liquor on premises | Sale / Manufacture / Both / NA |
| 7.1 | Possess or use rectified spirit for medicinal, industrial, scientific, educational purposes | Y/N |
| 7.2 | Sale or manufacture of drugs | Sale / Manufacture / NA |
| 7.3 | Manufacture, repair or deal with weights & measures | Manufacture / Repair / Dealer / NA |
| 7.4 | Packaging of goods or commodities | Y/N |

**Total: ~24 questions across 7 sections.**

---

## PART 2 — DEFECTS IN THE MAITRI QUESTIONNAIRE

These are your differentiators. Each is a concrete, demonstrable improvement.

### D1. No cross-field consistency validation
`1.4 = Yes (MIDC)` combined with `3.2 = Municipal Corporation` is a logical contradiction — an MIDC plot sits under MIDC's planning authority, not the corporation's. The form accepts it silently.

**Other contradictions the form permits:**
- `1 = No (no land required)` with `3 = Yes (setting up a factory)`
- `1.3 = Industrial` with `1.4 = No` and a location inside MIDC limits
- `4 = 20+ contract labourers` with `4.1 = fewer than 10 employees` (contract labour usually counts toward the factory worker headcount for licensing)
- `2.1 = Partnership firm` with `2.5 = Indian Company` — a partnership is not a company
- `6 = Green Category` with `6.1 = Hazardous Waste` — Green-category units generating hazardous waste is close to a definitional contradiction

**Build:** a constraint layer over the intake with ~15 mutual-exclusion and implication rules. Block advance, explain in plain language, offer the fix.

### D2. Self-declared pollution category
Q6 asks the applicant to pick Red / Orange / Green from a dropdown. Applicants get this wrong constantly, and wrong category cascades into wrong consent path, wrong fee slab, wrong documents, and a rejection weeks later.

**Build:** never ask. Derive from `product_code × capacity_band × effluent_volume` against the CPCB/MPCB harmonised annexure, show the derived category with the citation, and let the applicant contest it rather than guess it.

### D3. Boiler question captures the wrong population
"Are you a boiler manufacturer?" A food unit uses boilers; it doesn't make them. Registration under the Boilers Act 1923 is triggered by **operating** a boiler above 25 litres. Nothing in the form asks that.

**Build:** ask about use *and* manufacture, with capacity in litres.

### D4. Weights & measures has no "user" option
Manufacture / Repair / Dealer / NA. A food unit that weighs product on a platform scale is none of those, but still needs verification and stamping of its instruments under the Legal Metrology Act.

**Build:** add "User of weighing/measuring instruments in trade" with an instrument count.

### D5. No food-specific questions whatsoever
No FSSAI. No product category. No turnover. No capacity. No water source. No cold chain. For a food processing unit, the single most important licence in the entire journey is absent from the questionnaire.

This is the clearest gap and the easiest to justify to a Maharashtra jury: MAITRI is a state single-window, FSSAI is a central licence on FoSCoS, and no one bridges them.

### D6. Binary bands lose information needed downstream
`<15 m / >15 m`, `<5 / >5`, `20 or more / less than 20`. Bands are fine for *triggering* an approval, but the actual number is needed to *fill the application form* later. Capturing "20 or more" means asking again at submission time.

**Build:** capture exact numbers, derive the bands. Never make the applicant enter the same fact twice — that's the "reuse verified data" outcome in your problem statement.

### D7. No stage awareness
The form assumes greenfield setup. It has no path for expansion, renewal, change of product, change of occupier, or closure — which is where most *recurring* government workload actually sits.

---

## PART 3 — THE COMPLETE QUESTION BANK

Target: derive the full approval set for a food processing unit. Ordered so the highest-branching questions come first.

### S0 — Journey framing (ask first, prunes hardest)
| # | Question | Type | MAITRI | Confidence |
|---|---|---|---|---|
| 0.1 | What stage are you at? | new setup / expansion / renewal / change of product / change of occupier / closure | ❌ | HIGH |
| 0.2 | Is the unit already operational? | Y/N | ❌ | HIGH |
| 0.3 | Target date to begin production | date | ❌ | HIGH |
| 0.4 | Do you already hold any approvals? | multi-select from catalogue | ❌ | HIGH |

> 0.4 is the "reuse verified data" hook. If they hold a CTE, don't ask for it again — fetch and validate it.

### S1 — Entity
| # | Question | Type | MAITRI | Triggers |
|---|---|---|---|---|
| 1.1 | Is your entity already registered? | Y/N | ✅ Q2 | |
| 1.2 | Entity type | proprietorship / partnership / LLP / Pvt Ltd / Public Ltd / OPC / co-op society / trust / FPO / SHG | ⚠️ Q2.1 *(incomplete list — no LLP, no Pvt Ltd, no proprietorship)* | MCA route |
| 1.3 | Nature of activity | manufacturing / services / trade / mixed | ✅ Q2.2 | |
| 1.4 | Indian or foreign ownership; FDI % | | ✅ Q2.5 | FEMA/FDI reporting |
| 1.5 | PAN of entity | text | ❌ | Validation anchor |
| 1.6 | Promoter category | general / SC-ST / women / differently-abled | ❌ | Incentive slabs |
| 1.7 | Is this a first-generation entrepreneur? | Y/N | ❌ | Scheme eligibility |

### S2 — Location and land *(highest branching factor in the whole tree)*
| # | Question | Type | MAITRI | Triggers |
|---|---|---|---|---|
| 2.1 | District / taluka / village or ward | cascading dropdown | ❌ | **Routes to correct DIC, MPCB regional office, DISH division, fire jurisdiction** |
| 2.2 | Do you require land? | Y/N | ✅ Q1 | |
| 2.3 | Do you possess it? | Y/N | ✅ Q1.2 | |
| 2.4 | Tenure | owned / leased / rented / MIDC-allotted / family / to-be-acquired | ❌ | Landlord NOC, lease-term rule |
| 2.5 | If leased/rented: lease start and end date | date pair | ❌ | **Unexpired term must exceed licence validity** |
| 2.6 | Planning authority | MIDC / Municipal Corp / Municipal Council / Nagar Panchayat / Gram Panchayat / MMRDA / PMRDA / SEZ / Food Park | ⚠️ Q3.2 *(only 3 of 9 options offered)* | Building permission route |
| 2.7 | Is the land under MIDC? | Y/N | ✅ Q1.4 | **Must be consistent with 2.6** |
| 2.8 | Land classification | agricultural / NA / deemed-NA / MIDC industrial | ⚠️ Q1.3 *(asks "nature", conflates zone with classification)* | NA permission |
| 2.9 | Development Plan zone | I-1 / I-2 / R / C / Green / No-Dev / Agriculture | ❌ | **Zone-vs-category permissibility** |
| 2.10 | Survey / Gat / CTS / Plot number | text | ❌ | Cross-document anchor |
| 2.11 | Plot area | m² | ❌ | FSI, fee slabs |
| 2.12 | Is the plot in CRZ? | Y/N/unknown | ❌ | MCZMA clearance |
| 2.13 | Within 20 km of an airport? | Y/N + distance | ❌ | AAI height NOC |
| 2.14 | In an eco-sensitive zone or within 10 km of a protected area? | Y/N | ❌ | Wildlife clearance |
| 2.15 | Any encumbrance, mortgage, or tenancy on the land? | Y/N | ❌ | **Adds lender NOC dynamically** |
| 2.16 | Is the land tenure restricted (Inam / Watan / Devasthan / Bhogvatdar Varg-2)? | Y/N/unknown | ❌ | Collector sanction; transfer may be void without it |

### S3 — Construction
| # | Question | Type | MAITRI | Triggers |
|---|---|---|---|---|
| 3.1 | Will you construct, or occupy existing built space? | new / existing / renovation | ❌ | Building permission |
| 3.2 | Proposed built-up area | m² | ❌ | **≥20,000 m² triggers Environmental Clearance under EIA 2006 item 8(a)** |
| 3.3 | Building height | metres | ⚠️ Q3.1 *(band only)* | Fire NOC class |
| 3.4 | Number of floors | integer | ❌ | Fire, lift |
| 3.5 | Will trees be felled? | Y/N + count | ✅ Q6.2 | Tree authority permission |
| 3.6 | Basement or mezzanine? | Y/N | ❌ | Fire requirements |

### S4 — Utilities
| # | Question | Type | MAITRI | Triggers |
|---|---|---|---|---|
| 4.1 | Electricity connection type | LT / HT / temporary | ✅ Q1.6 | HT → Electrical Inspector |
| 4.2 | Connected load | kVA or HP | ❌ | **Must reconcile with factory licence max HP** |
| 4.3 | DG set? | Y/N + capacity kVA | ⚠️ Q1.7 *(no capacity)* | MPCB air consent, noise |
| 4.4 | Lift or escalator? | Y/N + count | ✅ Q1.8 | Lift permit |
| 4.5 | Water source | municipal / MIDC / MJP / borewell / tanker / river | ❌ | **CGWA NOC if borewell** |
| 4.6 | Water consumption | m³/day | ❌ | **MPCB fee slab + category** |
| 4.7 | Effluent generated | m³/day | ❌ | ETP / CETP requirement |
| 4.8 | Will you connect to a CETP? | Y/N | ❌ | MIDC CETP membership |
| 4.9 | Solar rooftop or captive power? | Y/N + kW | ❌ | MEDA / net metering |

### S5 — Product and process *(entirely absent from MAITRI — your biggest gap-fill)*
| # | Question | Type | MAITRI | Triggers |
|---|---|---|---|---|
| 5.1 | Product categories | multi-select from food taxonomy | ❌ | **Derives MPCB category, FSSAI KoB, BIS applicability** |
| 5.2 | Processes used | multi-select: washing, cutting, cooking, frying, baking, fermentation, distillation, pasteurisation, retort, drying, milling, extraction, freezing, packing-only, storage-only | ❌ | FSSAI KoB, safety |
| 5.3 | Installed capacity | tonnes/day or kL/day | ❌ | **Capacity-gated FSSAI category; MPCB consent limit** |
| 5.4 | Any input of animal origin? | Y/N + type | ❌ | Veterinary NOC, Red category |
| 5.5 | Packaged drinking or mineral water? | Y/N | ❌ | **Mandatory BIS — hard blocker** |
| 5.6 | Alcoholic beverages? | Y/N | ⚠️ Q7 *(asks about premises liquor sale, not production)* | State Excise |
| 5.7 | Boiler — will you **operate** one? | Y/N + capacity in litres | ⚠️ Q5 *(asks only about manufacturing)* | **Boilers Act at >25 L** |
| 5.8 | Ammonia refrigeration or cold storage? | Y/N + charge kg | ❌ | PESO, off-site emergency plan |
| 5.9 | Bulk LPG, solvents, or flammables stored? | Y/N + quantity | ❌ | PESO licence |
| 5.10 | Rectified spirit for industrial use? | Y/N | ✅ Q7.1 | Excise |
| 5.11 | Organic claim on labels? | Y/N | ❌ | NPOP certification |
| 5.12 | Pre-packaged goods sold by weight or measure? | Y/N | ✅ Q7.4 | Legal Metrology PC registration |
| 5.13 | Do you use weighing/measuring instruments in trade? | Y/N + count | ❌ *(7.3 has no "user" option)* | **Verification and stamping** |
| 5.14 | Will you manufacture, repair, or deal in weights & measures? | Manufacture / Repair / Dealer / NA | ✅ Q7.3 | LM licence |
| 5.15 | Drugs or nutraceuticals? | Y/N | ✅ Q7.2 | FDA drug licence |

### S6 — Scale and finance
| # | Question | Type | MAITRI | Triggers |
|---|---|---|---|---|
| 6.1 | Investment in plant & machinery | ₹ | ⚠️ Q2.4 *(band only)* | Udyam class, MPCB fee slab, incentives |
| 6.2 | Total project cost | ₹ | ❌ | Incentives |
| 6.3 | **Projected annual turnover** | ₹ | ❌ | **FSSAI category: ₹1.5 cr / ₹50 cr thresholds** |
| 6.4 | Udyam classification | micro / small / medium / large | ✅ Q2.4 | Should be derived from 6.1, not asked |
| 6.5 | Term loan being availed? | Y/N + lender | ❌ | Lender NOC, CGTMSE, interest subvention |

### S7 — Labour
| # | Question | Type | MAITRI | Triggers |
|---|---|---|---|---|
| 7.1 | Total employees | integer | ⚠️ Q4.1 *(band)* | **ESIC 10+, EPFO 20+, Factories Act** |
| 7.2 | Will power be used in the manufacturing process? | Y/N | ❌ | **Changes the Factories Act threshold** |
| 7.3 | Contract labourers | integer | ⚠️ Q4 *(band)* | CLRA at 20+ |
| 7.4 | Migrant workers | integer | ⚠️ Q4.2 *(band)* | ISMW Act |
| 7.5 | Motor transport workers | integer | ⚠️ Q4.3 *(band)* | MTW Act |
| 7.6 | Women employed? | Y/N + count | ❌ | POSH committee at 10+, crèche at 50+ |
| 7.7 | Night shift operation? | Y/N | ❌ | Women night-work permission |
| 7.8 | Number of food handlers | integer | ❌ | **FoSTaC ratio, medical certificates** |
| 7.9 | Hazardous process as defined in the Factories Act? | Y/N | ❌ | Additional DISH requirements |

### S8 — Environment
| # | Question | Type | MAITRI | Notes |
|---|---|---|---|---|
| 8.1 | Pollution category | **derived, not asked** | ⚠️ Q6 *(self-declared)* | Derive from 5.1 + 5.3 + 4.7 |
| 8.2 | Waste streams generated | hazardous / bio-medical / plastic / e-waste / solid / food waste | ✅ Q6.1 | Authorisations |
| 8.3 | Plastic packaging used? | Y/N + tonnes/yr | ❌ | **EPR registration — commonly missed by food units** |
| 8.4 | Air emission sources | boiler stack / DG / fryer / dryer / none | ❌ | Air Act consent conditions |
| 8.5 | Does the product appear in the EIA 2006 Schedule? | derived | ❌ | Distillery, sugar, large slaughterhouse |

### S9 — Food-specific *(none of this exists in MAITRI)*
| # | Question | Type | Triggers |
|---|---|---|---|
| 9.1 | Number of premises / units | integer | **One FSSAI licence per premises** |
| 9.2 | Will you operate in more than one state? | Y/N | Central licence |
| 9.3 | Import or export food? | Y/N | Central licence + IEC |
| 9.4 | Manufacture for third-party brands, or use a contract manufacturer? | Y/N | Brand-owner NOC |
| 9.5 | Sell through e-commerce? | Y/N | FSSAI e-commerce KoB |
| 9.6 | Nutraceuticals, health supplements, or infant food? | Y/N | Stricter FSSAI schedule |
| 9.7 | Do you have a FoSTaC-trained supervisor? | Y/N + count | Ratio 1 per 25 handlers |
| 9.8 | Water used as an ingredient? | Y/N | Potability test requirement |

### S10 — Export
| # | Question | Type | Triggers |
|---|---|---|---|
| 10.1 | Do you intend to export? | Y/N | IEC |
| 10.2 | Destination markets | multi-select | EIC/EIA, TRACES, FSVP |
| 10.3 | Product category for export | processed food / marine / spices / cereals | APEDA / MPEDA / Spices Board |
| 10.4 | 100% Export Oriented Unit? | Y/N | FSSAI Central + Commerce Ministry certificate |

### S11 — Incentives
| # | Question | Type | Triggers |
|---|---|---|---|
| 11.1 | Do you want to be assessed for incentives? | Y/N | Opens the incentive branch |
| 11.2 | Is this a new unit or an expansion? | new / expansion | PSI eligibility differs |
| 11.3 | Employment to be generated | integer | Employment-linked incentives |
| 11.4 | Taluka classification of the site | derived from 2.1 | **Vidarbha / Marathwada get higher slabs** |
| 11.5 | Interested in PMFME, PMKSY, PLI, or AIF? | multi-select | Scheme-specific documents |

---

## PART 4 — CONSTRAINT RULES FOR THE INTAKE

Encode these as blocking or warning rules over the answers themselves. This is what MAITRI does not do, and it is cheap to build.

| # | Rule | Severity |
|---|---|---|
| C-01 | `2.7 = Yes (MIDC)` → `2.6` must be MIDC | **Block** — this is the contradiction in the uploaded screenshots |
| C-02 | `2.2 = No land required` → `3.1` cannot be "new construction" and `S3` must collapse | Block |
| C-03 | `1.2 = partnership` → `1.4` cannot be "Indian Company" | Block |
| C-04 | `8.1 = Green` and `8.2` includes hazardous waste | Warn and re-derive |
| C-05 | `7.3 ≥ 20 contract labourers` but `7.1 < 10 employees` | Warn — contract labour usually counts toward the factory headcount |
| C-06 | `2.8 = agricultural` and `2.9 = industrial zone` | Warn — likely deemed-NA; **suppress the NA requirement** |
| C-07 | `5.5 = packaged drinking water` and no BIS in `0.4` | Hard blocker on production |
| C-08 | `6.3 turnover > ₹50 cr` and applicant selected State licence | Block — recompute category |
| C-09 | `2.5` unexpired lease term < validity of any licence sought | Block |
| C-10 | `4.2 connected load > 4.1 LT capacity` | Warn — LT connection cannot support the declared load |
| C-11 | `5.7 boiler capacity > 25 L` and no boiler registration path activated | Auto-add requirement |
| C-12 | `3.2 built-up ≥ 20,000 m²` and no EC in the derived set | Auto-add EC |
| C-13 | `7.1 ≥ ESIC/EPFO threshold` and applicant claims no registration needed | Auto-add |
| C-14 | `9.1 premises count > 1` and only one FSSAI licence declared | Warn — one licence per premises |
| C-15 | `0.3 target production date` earlier than the DAG critical path allows | Warn with the realistic date |

---

## PART 5 — HOW TO USE THIS IN THE BUILD

**Question count:** MAITRI asks ~24. This bank has ~95. That is not automatically better — an applicant facing 95 questions leaves.

**The resolution is progressive disclosure.** Ask S0 and S2.1 first (stage and location), then S5.1 (product). Those three answers alone prune 60–70% of the remaining questions. A packing-only unit on an MIDC plot never sees the boiler, effluent, PESO, or excise branches.

**Target: 12–18 questions for a typical applicant**, with the rest suppressed. Then say so in the UI — "we skipped 40 questions that don't apply to you, here's why" is a more compelling demo than a completed form, because it demonstrates the engine *reasoning* rather than just collecting.

**Three metrics for the pitch:**
1. Questions asked vs. questions in the bank (shows pruning)
2. Approvals derived vs. approvals the applicant would have found alone
3. Contradictions caught at intake vs. at departmental scrutiny

**One caution on framing:** MAITRI is a live, funded, statutorily-backed system built by the same government that is judging you. Present these as gaps you can help close, not as failures. "MAITRI covers state services; food units need central approvals too, and we bridge both" lands well. "MAITRI's form is broken" does not.
