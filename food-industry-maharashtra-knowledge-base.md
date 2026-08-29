# Regulatory Knowledge Base Seed — Food Processing Unit, Maharashtra

**Purpose:** seed data for the regulatory knowledge engine (SIH 2026, PS 26130).
**Scope:** setting up and operating a food manufacturing / processing unit in Maharashtra.
**Structure:** Part A defines the input variables that cause branching. Part B is the approval catalogue with firing conditions. Part C is the document-level validation ruleset. Part D is cross-document consistency. Part E is dependency ordering. Part F is the machine-readable schema.

---

## PART A — CASE VARIABLES (the input vector)

Everything downstream is a function of these. Your intake wizard collects exactly this, and nothing more.

### A1. Entity attributes
| Variable | Domain |
|---|---|
| `entity_type` | proprietorship \| partnership \| LLP \| private_limited \| public_limited \| OPC \| cooperative_society \| trust \| SHG \| FPO |
| `constitution_date` | date |
| `is_foreign_owned` | bool (triggers FDI / FEMA reporting) |
| `promoter_category` | general \| SC/ST \| women \| differently_abled (drives incentive eligibility) |

### A2. Location attributes — **the single biggest branching driver**
| Variable | Domain | Why it matters |
|---|---|---|
| `land_tenure` | owned \| leased \| MIDC_allotted \| rented \| family_owned |
| `governing_authority` | MIDC \| Municipal_Corporation \| Municipal_Council \| Nagar_Panchayat \| Gram_Panchayat \| MMRDA \| PMRDA \| NMRDA \| SEZ \| Mega_Food_Park |
| `district` + `taluka` + `village/ward` | Maharashtra master | Determines DIC, MPCB regional office, DISH division, Fire jurisdiction |
| `land_classification` | agricultural \| non_agricultural \| deemed_NA \| MIDC_industrial |
| `dp_zone` | I-1 \| I-2 \| R \| C \| Green \| No-Development \| Agriculture \| Public-Semi-public |
| `in_CRZ` | bool — Mumbai, Thane, Raigad, Ratnagiri, Sindhudurg, Palghar coastal belt |
| `near_airport` | bool + distance — AAI height NOC |
| `in_eco_sensitive_zone` | bool — Western Ghats / ESZ around sanctuaries |
| `plot_area_sqm`, `builtup_area_sqm` | number — **≥20,000 sqm built-up triggers Environmental Clearance under EIA 2006 item 8(a)** |
| `building_height_m` | number — fire NOC severity |

**Critical branch:** MIDC plot vs non-MIDC land splits the entire tree. On an MIDC plot, land use, water, drainage, and building permission all come from MIDC — you skip Collector NA permission, skip municipal building plan approval, and use MIDC's own building permission. On private land in a gram panchayat, you need Collector NA + Gram Panchayat NOC + Collector building permission. This one variable removes or adds ~5 approvals.

### A3. Product / process attributes
| Variable | Domain |
|---|---|
| `product_categories` | multi-select from the food taxonomy (see A3.1) |
| `process_types` | washing, cutting, blanching, cooking, frying, baking, fermentation, distillation, pasteurisation, sterilisation/retort, drying/dehydration, milling/grinding, extraction, freezing, packing_only, storage_only |
| `is_packaged_drinking_water` | bool — **mandatory BIS licence, non-negotiable** |
| `has_animal_origin_input` | bool — meat/poultry/fish/egg → slaughterhouse rules, veterinary NOC, Red category |
| `is_alcoholic` | bool — State Excise licensing, entirely separate tree |
| `uses_boiler` | bool + capacity_litres — **>25 litres = Boilers Act registration** |
| `uses_ammonia_refrigeration` | bool — PESO pressure vessel + off-site emergency plan |
| `uses_LPG_bulk` / `uses_solvents` | bool + quantity — PESO explosives licence |
| `daily_production_capacity` | tonnes/day or kL/day — some FSSAI KoBs are capacity-gated regardless of turnover |
| `makes_organic_claim` | bool — NPOP / Jaivik Bharat |
| `is_export_oriented` | bool + destination_countries |

#### A3.1 Product taxonomy → default MPCB category (verify against current CPCB harmonised list)
| Product family | Typical category | Notes |
|---|---|---|
| Atta chakki, flour mill, grain steeping | Green / White | Low water, dust control only |
| Bakery, biscuits, confectionery | Green | |
| Supari, masala grinding | Green | Dust |
| Ice cream, ice making | Green | Ammonia may escalate |
| Mineralised / packaged drinking water | Green–Orange | Reject water disposal |
| Fruit & vegetable processing, pulping | Orange | High BOD effluent |
| Soft drinks / carbonated beverages | Orange | |
| Dairy processing, milk chilling | Orange | High BOD |
| Fish / meat / poultry processing | Red | Very high BOD, odour, animal waste |
| Slaughterhouse | Red | Also EIA schedule |
| Edible oil / vanaspati / solvent extraction | Red | Solvents |
| Distillery, brewery, winery | Red | EIA Schedule 5(g), Excise |
| Sugar | Red | EIA Schedule |
| Starch / glucose / sago | Red | |
| Cold storage (non-ammonia) | White / Green | |

> **Engine note:** never hardcode this table as truth. Model it as `category_rule(product_code, capacity_band, effluent_m3_day) → {R,O,G,W,B}` with a citation field pointing to the specific CPCB/MPCB circular, and a `last_verified` date. The Feb 2025 CPCB harmonisation directions and the MPCB circulars of 16 and 23 June 2025 are your current authority. Categories get re-harmonised every few years — your engine must survive that.

### A4. Scale attributes
| Variable | Thresholds that fire rules |
|---|---|
| `investment_plant_machinery` | Udyam: micro ≤₹2.5 cr, small ≤₹25 cr, medium ≤₹125 cr *(revised limits effective FY 2025-26 — verify)* |
| `annual_turnover` | **FSSAI: ≤₹1.5 cr → Registration; ₹1.5–50 cr → State Licence; >₹50 cr → Central Licence** (order dt. 13 Mar 2026, effective 1 Apr 2026) |
| `worker_count` | Factories Act; ESIC (10+); EPFO (20+); Shops & Est. |
| `uses_power` | bool — changes Factories Act threshold |
| `connected_load_HP` / `kVA` | Electricity connection category, factory licence fee slab |
| `water_consumption_m3_day` | MPCB consent fee slab + category escalation |
| `effluent_m3_day` | ETP requirement, CETP membership if in MIDC |
| `works_night_shift` | bool — women night-work permission under Factories Act |
| `employs_contract_labour` | 20+ contract workers → CLRA registration |

> **Verify before coding:** the Factories Act s.2(m) threshold is 10 workers with power / 20 without under the central Act, but several states have amended it upward. Confirm Maharashtra's current threshold from the Directorate of Industrial Safety and Health (DISH) directly — do not take it from a blog. This is exactly the kind of state-amendment override your engine must represent as a first-class concept: `central_rule` + `state_override` + `effective_from`.

### A5. Stage attribute
`lifecycle_stage` = pre_incorporation | land_acquisition | pre_construction | construction | pre_operation | operational | expansion | renewal | closure

The same unit needs different things at different stages. Your checklist generator must be stage-aware, not a flat list.

---

## PART B — APPROVAL CATALOGUE

Format: **ID | Approval | Authority | Statute | Fires when | Typical SLA**

### B1. Entity & tax layer (always, varies by entity_type)

| ID | Approval | Authority | Fires when |
|---|---|---|---|
| E-01 | Name reservation (RUN/SPICe+ Part A) | MCA | entity_type ∈ {company, LLP, OPC} |
| E-02 | Incorporation — Certificate of Incorporation | MCA / RoC Mumbai or Pune | same |
| E-03 | PAN + TAN | Income Tax (auto via SPICe+) | always |
| E-04 | GST Registration | CBIC / Maharashtra GST | turnover > threshold, or inter-state supply, or e-commerce sale — **effectively always for a manufacturer** |
| E-05 | Udyam Registration | MoMSME | optional but gates most incentives → treat as required |
| E-06 | Professional Tax (PTEC + PTRC) | Maharashtra Finance Dept | PTEC always; PTRC when employing salaried staff |
| E-07 | Shops & Establishments registration/intimation | Local body, Maharashtra Shops & Establishments Act 2017 | intimation for small; registration at 10+ workers |
| E-08 | EPFO registration | EPFO | 20+ employees |
| E-09 | ESIC registration | ESIC | 10+ employees |
| E-10 | Importer-Exporter Code (IEC) | DGFT | is_export_oriented |
| E-11 | Bank current account | Bank | always |
| E-12 | Trade Mark (optional) | CGPDTM | brand protection |

### B2. Land, siting & construction layer

| ID | Approval | Authority | Fires when |
|---|---|---|---|
| L-01 | MIDC plot allotment + possession | MIDC | governing_authority = MIDC |
| L-02 | Sale deed / lease deed registration | IGR Maharashtra | land purchased or leased |
| L-03 | Non-Agricultural (NA) permission | Collector | land_classification = agricultural AND not in MIDC AND not deemed-NA |
| L-04 | Zoning / Land-use certificate | Planning Authority (MC / MIDC / Collector) | always — confirms food industry permitted in `dp_zone` |
| L-05 | Gram Panchayat NOC | Gram Panchayat | governing_authority = Gram_Panchayat |
| L-06 | Building plan approval + Commencement Certificate | MC / MIDC / Collector | any construction |
| L-07 | Environmental Clearance (building) | SEIAA | builtup_area ≥ 20,000 sqm |
| L-08 | Environmental Clearance (industry) | SEIAA / MoEFCC | product in EIA 2006 Schedule — distillery, sugar, large slaughterhouse |
| L-09 | CRZ Clearance | MCZMA | in_CRZ |
| L-10 | AAI height NOC | Airports Authority of India | near_airport AND height exceeds surface |
| L-11 | Tree cutting permission | Local body / Forest Dept | trees on plot |
| L-12 | Water connection (industrial) | MIDC / MJP / Municipal | always |
| L-13 | Groundwater abstraction NOC | CGWA / State GW Authority | bore well AND notified/over-exploited block |
| L-14 | Electricity load sanction + connection | MSEDCL / MIDC / Adani-Tata (Mumbai) | always |
| L-15 | Drainage / sewerage connection | MIDC / Local body | always |
| L-16 | Occupancy Certificate / Building Completion | MC / MIDC | after construction, **before CTO** |

### B3. Environment layer

| ID | Approval | Authority | Fires when |
|---|---|---|---|
| V-01 | **Consent to Establish (CTE)** — Water Act 1974 + Air Act 1981 | MPCB | category ≠ White. **Must precede construction.** |
| V-02 | **Consent to Operate (CTO)** | MPCB | before commencing production |
| V-03 | White category registration/intimation | MPCB | category = White (no consent, intimation only) |
| V-04 | Hazardous & Other Waste authorisation | MPCB | generates listed hazardous waste (used oil, solvent residue, ETP sludge) |
| V-05 | Bio-medical / E-waste / Plastic Waste EPR registration | CPCB/MPCB | plastic packaging → **EPR registration is commonly missed by food units** |
| V-06 | CETP membership | MIDC CETP operator | in MIDC with common effluent plant |
| V-07 | Environmental Statement (Form V) | MPCB | annually by 30 September, for consent holders |

### B4. Safety & labour layer

| ID | Approval | Authority | Fires when |
|---|---|---|---|
| S-01 | Factory building plan approval (Form 1) | DISH Maharashtra | worker_count ≥ Factories Act threshold |
| S-02 | Factory Licence (Form 2/4) | DISH Maharashtra | same |
| S-03 | Boiler registration + certificate | Directorate of Steam Boilers, Maharashtra | boiler capacity > 25 litres |
| S-04 | Boiler attendant/operator competency certificate | same | boiler present |
| S-05 | Fire NOC — Provisional | Maharashtra Fire Services / local brigade | per Maharashtra Fire Prevention & Life Safety Measures Act 2006 — before construction |
| S-06 | Fire NOC — Final | same | before occupancy |
| S-07 | Half-yearly fire compliance (Form B) | Licensed fire agency → local authority | operational, recurring |
| S-08 | Lift/escalator permit | PWD / Electrical Inspector | lift installed |
| S-09 | Electrical installation safety certificate | Chief Electrical Inspector | HT connection / transformer |
| S-10 | PESO explosives licence | Petroleum & Explosives Safety Organisation | bulk LPG, solvents, or ammonia pressure vessels above threshold |
| S-11 | Contract Labour (CLRA) registration | Labour Dept | 20+ contract workers |
| S-12 | Women night-shift permission | Labour Dept / DISH | works_night_shift with women workers |

### B5. Food-specific layer

| ID | Approval | Authority | Fires when |
|---|---|---|---|
| F-01 | **FSSAI Registration (Form A)** | Designated Officer, local body | turnover ≤ ₹1.5 cr AND KoB eligible |
| F-02 | **FSSAI State Licence (Form B)** | Maharashtra FDA | turnover ₹1.5–50 cr, OR KoB mandates it regardless of turnover, OR capacity above KoB limit |
| F-03 | **FSSAI Central Licence (Form B)** | FSSAI Regional Office | turnover > ₹50 cr, OR import/export, OR multi-state operation, OR 100% EOU, OR central-government-premises FBO |
| F-04 | BIS Licence (ISI mark) | Bureau of Indian Standards | product under mandatory certification — **packaged drinking water (IS 14543), natural mineral water (IS 13428), infant milk food, milk powder, condensed milk** |
| F-05 | Health / Trade Licence | Municipal Corporation health dept | operating in municipal limits |
| F-06 | Legal Metrology — Packaged Commodities registration | Legal Metrology Dept, Maharashtra | pre-packaged goods sold by weight/measure |
| F-07 | Legal Metrology — verification & stamping of weighing instruments | same | any weighing/measuring instrument in trade use |
| F-08 | Veterinary / animal husbandry NOC | Animal Husbandry Dept | has_animal_origin_input |
| F-09 | AGMARK certification | DMI | optional, for graded commodities |
| F-10 | Organic certification (NPOP) | APEDA-accredited certification body | makes_organic_claim |
| F-11 | FoSTaC trained Food Safety Supervisor | FSSAI-approved training partner | **1 trained supervisor per 25 food handlers** |
| F-12 | Food handler medical fitness certificates | Registered medical practitioner | all food handlers, annually |
| F-13 | State Excise licence | Maharashtra State Excise | is_alcoholic — separate tree entirely |

### B6. Export layer (if is_export_oriented)

| ID | Approval | Authority | Fires when |
|---|---|---|---|
| X-01 | APEDA Registration (RCMC) | APEDA | processed food, fruits & vegetables, cereals, meat |
| X-02 | MPEDA Registration | MPEDA | marine products |
| X-03 | Spices Board Registration | Spices Board | spices |
| X-04 | EIC/EIA approved establishment | Export Inspection Council | export to EU/US requiring health certificate |
| X-05 | Health / Sanitary certificate per consignment | EIA | per shipment |
| X-06 | Plant Quarantine / Phytosanitary certificate | DPPQS | plant-origin products |
| X-07 | Destination-country registration (FDA FSVP, EU TRACES) | Foreign regulator | per market |

### B7. Incentives layer (post-approval, high value for your dashboard)

| ID | Scheme | Authority | Eligibility hook |
|---|---|---|---|
| I-01 | PSI / Maharashtra Industrial Policy incentives — Eligibility Certificate | DIC / MIDC | new unit or expansion, investment + employment thresholds, taluka classification (Vidarbha/Marathwada get higher) |
| I-02 | Stamp duty exemption | IGR + DIC | per industrial policy, zone-dependent |
| I-03 | Electricity duty exemption | MSEDCL + DIC | per industrial policy |
| I-04 | PMFME — 35% credit-linked subsidy up to ₹10 lakh | MoFPI via State Nodal Agency | micro food processing enterprise |
| I-05 | PMKSY components (cold chain, food testing labs, unit scheme) | MoFPI | per component |
| I-06 | PLI for Food Processing | MoFPI | large investment, specified product lines |
| I-07 | CGTMSE collateral-free credit guarantee | CGTMSE | MSME |
| I-08 | Maharashtra SMART project | Agriculture Dept | agri value chain |
| I-09 | Agri Infrastructure Fund — 3% interest subvention | NABARD/DAC | post-harvest infrastructure |

### B8. Recurring compliance calendar (feeds your renewal + alert engine)

| Obligation | Frequency | Due |
|---|---|---|
| GSTR-1 / GSTR-3B | Monthly/Quarterly | 11th / 20th |
| GSTR-9 Annual Return | Annual | 31 December |
| EPF ECR + ESIC contribution | Monthly | 15th |
| Professional Tax return | Monthly/Annual | per slab |
| **FSSAI Annual Return Form D-1** | Annual | **31 May** |
| **FSSAI Half-yearly Form D-2** | Half-yearly | dairy/milk units — Apr–Sep, Oct–Mar |
| FSSAI licence renewal | Per validity | 30 days before expiry; late fee ₹100/day |
| **MPCB Environmental Statement Form V** | Annual | **30 September** |
| MPCB CTO renewal / auto-renewal | Per validity | before expiry |
| Factory licence renewal | Annual/periodic | before expiry |
| Boiler inspection & certificate renewal | Annual | before due date |
| Fire compliance Form B | Half-yearly | Jan & Jul |
| Legal metrology re-verification/stamping | Annual | per instrument |
| Food handler medical re-examination | Annual | rolling |
| Water potability test (NABL lab) | Half-yearly | rolling |
| Pest control service | Monthly/Quarterly | rolling |
| Internal food safety audit | Annual | rolling |
| Third-party FSSAI food safety audit | As notified by KoB risk class | rolling |

---

## PART C — DOCUMENT VALIDATION RULESET

This is the core of your pre-validation engine. For each document: **extract → format-validate → authenticity-check → cross-check → temporal-check.**

### C1. Identity & entity documents

#### PAN card
- **Format:** exactly 10 chars, `[A-Z]{5}[0-9]{4}[A-Z]`
- **Semantic:** 4th character encodes holder type — `P`=individual, `C`=company, `F`=firm/LLP, `H`=HUF, `A`=AOP, `T`=trust, `B`=BOI, `G`=government, `J`=artificial juridical person, `L`=local authority.
  → **Rule:** `PAN[3]` must be consistent with declared `entity_type`. A private limited company submitting a PAN with `P` at position 4 is submitting an individual's PAN. This single check catches a large share of proprietor-vs-company confusion.
- **Semantic:** 5th character = first letter of surname (individual) or of entity name (non-individual). Compare with normalised applicant name; flag mismatch.
- **Authenticity:** verify against Income Tax / Protean PAN verification API — must return status *Existing and Valid*, and the returned name must fuzzy-match (≥0.9 Jaro-Winkler after normalisation).
- **Image checks:** presence of IT Dept emblem, hologram region, no visible clone-stamp artefacts.

#### Aadhaar (for proprietor / authorised signatory)
- **Format:** 12 digits, must pass **Verhoeff checksum**.
- **Privacy rule (non-negotiable):** never store the full number. Mask the first 8 digits. Prefer **DigiLocker / offline eKYC XML with share-code** or Aadhaar-based e-Sign over a scanned upload. Store only the reference number + verification result, not the image.
- **Cross-check:** name and DOB against PAN.

#### GSTIN
- **Format:** 15 chars — `[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]`
- **Position 1–2:** state code. **Maharashtra = 27.** → Rule: if premises are in Maharashtra, the GSTIN for that place of business must begin `27`. A `29` (Karnataka) GSTIN on a Pune premises means either wrong document or an unregistered additional place of business.
- **Position 3–12:** the PAN. → **Rule: `GSTIN[2:12]` must equal the submitted PAN, character for character.** This is the strongest free cross-check you have.
- **Position 13:** entity number for that PAN in that state.
- **Position 14:** literally `Z`.
- **Position 15:** checksum — mod-36 weighted algorithm over the first 14 characters. Implement it; it costs 15 lines and rejects typos and fabrications instantly.
- **Authenticity:** GSTN public API — status must be `Active`, not `Suspended` / `Cancelled`.
- **Cross-check:** *Principal Place of Business* or one of the *Additional Places of Business* in the GST record must geocode to within ~100 m of the declared premises. Food units very often register the office address and forget to add the factory as an additional place of business — flag it as a warning, not a rejection, with a remediation hint.

#### Certificate of Incorporation / CIN
- **Format:** 21 chars — `[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}`
- **Char 1:** `L` = listed, `U` = unlisted.
- **Char 2–6:** NIC industry code. → **Rule:** should fall in the food manufacturing range (NIC division 10/11). A CIN with a construction or IT industry code, for a food unit, means the object clause probably doesn't cover food manufacture — escalate to MoA check.
- **Char 7–8:** state of registration. `MH` expected for a Maharashtra-registered company (not mandatory — a Delhi-registered company can have a Maharashtra factory — so this is a *soft* flag).
- **Char 9–12:** year of incorporation. → Rule: must be ≤ current year and ≥ 1857.
- **Char 13–15:** `PLC`, `PTC`, `OPC`, `FTC`, `LLP`, `GOI`, `SGC`, `NPL`. → Rule: must match declared `entity_type`.
- **Authenticity:** MCA21 master data — company status must be `Active`, not `Strike Off` / `Under Liquidation` / `Dormant`.
- **Cross-check:** the PAN in MCA records must equal the submitted PAN.

#### MoA / AoA / Partnership Deed / LLP Agreement
- **Object clause must permit food manufacturing.** Extract the main-objects paragraph and semantic-match against food-processing verbs. A company whose objects cover only trading cannot lawfully manufacture — this is a real, common rejection ground that no portal currently catches automatically.
- **Partnership deed:** must be a registered deed (Registrar of Firms number + date) for enforceability; all partners' PANs must appear and match; profit-sharing must total 100%; check for a dissolution or retirement clause affecting a named signatory.
- **Signature page:** all partners signed, witnessed, correct stamp paper value for Maharashtra, stamp paper date ≤ deed date (a deed executed on stamp paper *purchased after* the execution date is a classic forgery tell).

#### Udyam Registration Certificate
- **Format:** `UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}`. State segment should be `MH`.
- **Authenticity:** Udyam portal verification API.
- **Cross-check:** investment and turnover on the Udyam certificate must reconcile with the DPR and the CA certificate. Udyam is self-declared and auto-populated from ITR/GST — **a large gap between Udyam turnover and the FSSAI turnover declaration is a strong fraud/misclassification signal.** Flag when they differ by more than ~20%.

#### Board Resolution / Authorisation Letter
- Must name the authorised signatory explicitly, not just "any director".
- Date must precede the application date.
- Signed by the required quorum; company seal if AoA requires it.
- **Cross-check:** the named signatory must be the same person whose DSC signs the forms and whose PAN/Aadhaar is submitted. Check the DIN against the MCA director list for that CIN.

#### Digital Signature Certificate
- Class 3, currently valid (not expired, not revoked — check CRL/OCSP).
- Issuing CA must be in the CCA India trust chain.
- Subject name must match the authorised signatory.

---

### C2. Land & property documents

#### 7/12 Extract (Satbara Utara)
This is the highest-value document in the whole set and the most commonly mis-read.
- **Extract:** village, survey/gat number, hissa, total area, holder names (Kabjedar), Other Rights column (*Itar Adhikar*), tenancy (*Kul*) entries, crop record, land classification.
- **Rules:**
  - Holder name must match the applicant, OR a valid chain of transfer documents must bridge the gap. Do not accept "my father's name" without a succession/mutation entry.
  - **Other Rights column must be empty of mortgages, charges, and court injunctions.** If a bank charge is recorded, the lender's NOC becomes a required document — your engine should *dynamically add* a document requirement here rather than reject.
  - **Tenancy (Kul) entries are a hard blocker.** Land with a protected tenant cannot be transferred/used without Collector permission under the Bombay Tenancy and Agricultural Lands Act.
  - Area must match the sale deed area within ±2% (survey rounding).
  - Land classification must be consistent with the NA status claimed.
  - **Extract must be dated within the last 3–6 months** — an old 7/12 hides recent mutations.
  - Check for *Ferfar* (mutation) entries pending.
  - **Restricted-tenure flags:** *Inam*, *Watan*, *Devasthan*, *Bhogvatdar Varg-2* land carries transfer restrictions. Detect these keywords and route to a specialist track — a Varg-2 land purchase without Collector sanction is void.
- **Authenticity:** verify against the Maharashtra MahaBhulekh / e-Records system rather than trusting the upload. Digitally signed 7/12 with QR code is now standard — **prefer QR fetch over OCR of a scan.**

#### Property Card (urban land)
- Same logic as 7/12 but for CTS-numbered urban land. Check CTS number, area, holder, and encumbrance entries.

#### Sale Deed / Lease Deed / Rent Agreement
- **Registration:** must carry an IGR registration number, sub-registrar office, and date. Unregistered lease deeds over 11 months are inadmissible.
- **Stamp duty:** compute expected duty from the Ready Reckoner value for that zone and compare with duty paid. **Under-stamping is the single most common defect** and makes the document inadmissible in evidence.
- **Parties:** seller must match the 7/12 holder; buyer must match the applicant.
- **Property description schedule:** survey/CTS number, area, and boundaries must match the 7/12 / property card.
- **Lease term rule:** for a leased premises, **the unexpired lease term must exceed the validity period of the licence being sought.** A 3-year lease with 8 months remaining cannot support a 5-year FSSAI licence. This is a temporal rule most portals miss entirely and it's a good demo moment.
- **Cross-check:** Index-II from IGR corroborates the deed independently.
- **Landlord NOC** required separately if the premises are rented — must reference the specific business activity, be on the landlord's letterhead, and the landlord must be the recorded owner.

#### MIDC Allotment Letter + Possession Receipt + Lease Deed
- Plot number, sector, area, allotment date, premium paid receipt.
- **Permitted use in the allotment must include food processing.** MIDC allots by broad industry; a plot allotted for engineering use needs a change-of-activity approval.
- Check whether the lease deed has actually been executed (many units operate on an allotment letter for years — this blocks bank finance and some approvals).
- Check transfer/sub-lease conditions if the plot was purchased from a prior allottee.

#### NA (Non-Agricultural) Permission Order
- Collector's order number and date; survey number must match the 7/12.
- **Permitted NA use must be "industrial"**, not residential or commercial.
- **Conditions:** most NA orders carry a time limit for commencing construction and a requirement to pay NA assessment (*akarni*). Check the payment receipt and whether the construction deadline has lapsed.
- **Deemed NA:** land inside a Development Plan industrial zone may be deemed NA under Maharashtra Land Revenue Code amendments — your engine should check `dp_zone` first and *skip* this requirement rather than demand a document that doesn't exist. Suppressing an inapplicable requirement is as valuable as adding a needed one.

#### Zoning / Land Use Certificate
- Issued by the correct planning authority for the location.
- **Zone must permit the specific industry.** Rule table: `dp_zone × mpcb_category → permitted / conditional / prohibited`. A Red-category food unit in a residential zone is prohibited; a Green-category unit may be conditionally permitted.
- Check setback and buffer requirements: distance from residential zone, water body, highway, and (for Red category) from habitation.

#### Building Plan Approval / Commencement Certificate
- Approving authority correct for jurisdiction.
- **Architect's registration number (Council of Architecture) must be valid and current.**
- Plot area on the plan must equal the 7/12 / property card area.
- Built-up area must be within permissible FSI for that zone.
- Setbacks, margins, and internal road width must satisfy DCPR/UDCPR norms.
- **CC validity:** typically 1 year, renewable. Expired CC means construction is unauthorised.
- **Cross-check:** the built-up area on the plan drives the EIA 8(a) rule (≥20,000 sqm) and the fire NOC severity. Extract it as a numeric field, not free text.

#### Occupancy Certificate
- Must reference the same CC number.
- Must be issued after construction and match the as-built plan.
- **Dependency rule:** OC should exist before MPCB CTO and before the FSSAI final inspection. Sequencing violation → warn.

---

### C3. Environment documents

#### MPCB Consent to Establish / Operate
- **Extract:** consent number, issue date, validity date, category (R/O/G/W/B), consented products with quantities, consented water consumption (m³/day), consented effluent, emission limits, and the specific conditions list.
- **Rules:**
  - **Consented product list must cover every product on the FSSAI licence.** A unit that adds a fruit-pulp line to a bakery consent is operating outside consent. Set-difference check between FSSAI product list and MPCB product list, both ways.
  - **Consented capacity must be ≥ declared production capacity** in the DPR and factory licence.
  - **Consented water must be ≥ the sanctioned water connection**, and both ≥ the process water requirement in the DPR.
  - Capital investment declared to MPCB must reconcile with the CA certificate — MPCB fees are slabbed on capital investment, so under-declaration is a revenue leakage the department cares about. This is a strong "risk-based scrutiny" signal.
  - CTE must be dated **before** the construction start date.
  - CTO must be dated **before** the production start date.
  - Check the conditions list for ETP/APC installation requirements and whether the corresponding compliance evidence has been uploaded.
  - **Auto-renewal eligibility:** auto-renewal is generally allowed only where capital investment has not increased beyond ~10% and there is no increase in pollution load. Encode this as a rule that decides renewal path vs fresh application.
- **Authenticity:** MPCB e-consent portal verification by consent number.

#### ETP / Pollution control design documents
- Design flow must be ≥ generated effluent from the water balance.
- Water balance must close: intake = product + evaporation + effluent + losses. **A water balance that doesn't sum is an instant flag** and is trivially machine-checkable.
- Consultant/designer credentials.

#### Environmental Clearance (where applicable)
- EC letter number, validity (typically 7–10 years), conditions, expansion limits.
- Half-yearly compliance report submission evidence.

#### EPR Registration (plastic packaging)
- Registration number, category (producer/importer/brand-owner), annual targets.
- **Commonly missed** by food units that use plastic pouches. Good "you didn't know you needed this" moment for your demo.

---

### C4. Safety documents

#### Fire NOC
- **Provisional vs Final** — check which one is submitted; a provisional NOC does not permit occupancy.
- Issuing authority must have jurisdiction over the location (municipal fire brigade vs Directorate).
- **Occupancy classification stated must match reality** — industrial (Group G) vs storage (Group H) vs mixed. A godown declared as a factory gets the wrong fire requirements.
- Building height and number of floors must match the approved plan.
- **Validity + the half-yearly Form B obligation** — check that Form B certificates from a licensed fire agency have been filed for the elapsed periods.
- Fire-fighting installation schedule (hydrants, sprinklers, extinguishers, tank capacity) must match the building's occupancy class and area per Maharashtra Fire Act rules.

#### Factory Licence (DISH)
- **Extract:** licence number, occupier name, manager name, maximum workers permitted, maximum HP permitted, validity.
- **Rules:**
  - **Maximum workers permitted must be ≥ actual/planned worker count.** Under-declaring workers to reduce fees is common; cross-check against ESIC and EPFO employee counts.
  - **Maximum HP permitted must be ≥ connected load** on the electricity sanction letter.
  - **Occupier rule:** for a company, the occupier must be a director (Factories Act s.2(n) proviso). Verify the named occupier appears in the MCA director list for that CIN. A "manager appointed as occupier" for a company is legally invalid — a genuinely useful automated catch.
  - Manager must hold the prescribed qualification.
  - Factory plan approval (Form 1) must precede the licence.

#### Boiler documents
- Boiler registration number, capacity, working pressure, manufacturer, date of last hydraulic test, **next inspection due date**.
- Rule: next-due date must be in the future at the time of application. An expired boiler certificate means the unit cannot legally fire the boiler.
- Boiler attendant/operator certificate — class must match boiler capacity, and validity must be current.
- Cross-check: if `uses_boiler = true` in the intake but no boiler document exists, add the requirement. If a boiler certificate is uploaded but the DPR shows no boiler, flag the inconsistency.

#### Electrical safety / load sanction
- Sanctioned load (kVA/HP), consumer number, connection date.
- Cross-check against factory licence HP and the DPR's machinery list.

---

### C5. Food-specific documents

#### FSSAI Licence / Registration
- **Number format:** 14 digits. Structure: first digit indicates registration vs licence, followed by state code, year, enrolling authority code, and a sequential permit number. Validate the length and the leading digit, then **verify the full number against FoSCoS rather than trying to decode the middle segments** — the enrolling-authority segment is not reliably documented and hardcoding it will produce false rejections.
- **Rules:**
  - **The licence is premises-specific, not business-specific.** Every location needs its own. If the applicant declares 3 units and submits 1 licence, flag the 2 missing ones.
  - **Kind of Business (KoB) must match the actual activity.** A unit doing manufacturing on a "Trade/Retail" KoB is non-compliant. Match `process_types` against the FoSCoS KoB matrix.
  - **Product list must cover all products actually made** — cross-check against the MPCB consent, the DPR, and label artworks.
  - **Declared capacity must be ≥ actual capacity**, and some KoBs are capacity-gated into State/Central licence regardless of turnover — check both criteria and take the higher.
  - Address must match the premises documents exactly.
  - Validity and, where applicable, annual fee payment status.
  - **Category correctness:** recompute the required category from `annual_turnover` using the current thresholds (₹1.5 cr / ₹50 cr from 1 April 2026) plus the KoB overrides, and compare with the category actually held. Mis-categorisation after the April 2026 change is going to be extremely common — **this is a high-value automated check and a great demo scenario for a Maharashtra jury.**

#### Layout / Plant plan (for FSSAI)
- Must show: raw material receipt, storage, processing, packing, finished-goods storage, dispatch, with **unidirectional product flow and no crossing of raw and cooked paths.**
- Separate areas for personnel hygiene (hand wash, change room, toilets — toilets must not open directly into a processing area).
- Drainage direction, pest-proofing, ventilation.
- Areas dimensioned in m² and totalling to the built-up area on the approved building plan.
- Machine-checkable subset: presence of required zones (label detection), total area reconciliation, toilet-adjacency rule.

#### Food handler medical fitness certificates
- Issued by a registered medical practitioner (registration number present and verifiable with the state medical council).
- **Dated within the last 12 months.**
- Count of certificates must equal the declared food-handler headcount. Cross-check against ESIC/muster roll.

#### FoSTaC certificate
- Trainee name, certificate number, training level (must match the KoB — e.g. Advanced for manufacturing), validity.
- **Ratio rule: at least 1 trained Food Safety Supervisor per 25 food handlers.** Compute `ceil(handlers/25)` and compare with the number of valid certificates. Simple, quantitative, and exactly the kind of check officers currently do by hand.

#### Water potability test report
- **Lab must be NABL-accredited** — verify the accreditation number and its scope covers water testing, and that it was valid on the test date.
- Parameters tested must cover IS 10500; check each result against the permissible limit and flag exceedances.
- Sample collection date within the last 6 months; sampling point identified.
- **Common fraud:** the same report resubmitted year after year with the date changed. Hash-compare against previously submitted reports across the whole system — if the parameter values are byte-identical to a report from 2 years ago, that is not a coincidence.

#### BIS Licence (where mandatory)
- Licence number, IS standard number, product covered, validity, marking scheme.
- **Rule:** if `is_packaged_drinking_water = true` and no BIS licence exists, this is a hard blocker, not a warning. Packaged drinking water without BIS is a prosecutable offence.

#### Legal Metrology
- Packaged Commodities registration number.
- Verification/stamping certificates for each weighing instrument, with instrument serial numbers matching the asset list.
- Stamping validity (typically annual).
- Label declaration check: name and address of manufacturer, net quantity, MRP inclusive of all taxes, consumer care details, date of manufacture, best-before — all mandatory under Legal Metrology (Packaged Commodities) Rules 2011 **and** FSSAI Labelling & Display Regulations 2020. Overlapping requirements from two departments on the same artwork — good example for your "common scrutiny" pitch.

---

### C6. Financial documents

#### CA Certificate (net worth / investment / turnover)
- **UDIN is mandatory** — validate the UDIN on the ICAI portal. An unvalidated or absent UDIN on a CA certificate is a red flag and ICAI-verifiable in seconds.
- CA membership number, and the certificate date.
- Figures must reconcile with: ITR, audited financials, GST returns, Udyam declaration, DPR, and the MPCB capital investment declaration.

#### Project Report / DPR
- Internal consistency: capacity × operating days × yield must reconcile with projected turnover; machinery list must support the stated capacity; power requirement must match the electricity sanction; water requirement must match the MPCB consent and water connection.
- **This is where an LLM adds real value** — narrative consistency checking across a 40-page document is genuinely hard for a rules engine and genuinely tedious for an officer.

#### Bank documents
- Cancelled cheque / bank statement: account number and IFSC must match; account holder name must match the entity name exactly (not the proprietor's personal name, for a company).

---

### C7. Generic document-quality and authenticity checks (apply to every upload)

**Format & legibility**
- File type in allowlist; size within limits.
- Minimum resolution (≥200 DPI equivalent); reject if OCR confidence < threshold.
- Skew/blur/glare detection — **phone photos of documents are commonly rejected by government portal filters**, so catch them before submission rather than after.
- All pages present (check page-count against expected; detect "page 2 of 3" text with only 2 pages uploaded).
- Not password-protected; text layer extractable or OCR-able.

**Authenticity**
- **Prefer API/DigiLocker fetch over user upload wherever a source system exists.** Every document you fetch instead of accept is a document you never have to validate. This should be a headline principle of your architecture: *verified-source-first, upload-as-fallback.*
- QR code / digital signature present → verify the signature chain, signer identity, and signing timestamp; check that the document hasn't been modified after signing (incremental-update detection in the PDF).
- PDF metadata forensics: `Producer` / `Creator` fields inconsistent with the claimed issuing authority (e.g. a Collector's order whose producer is "Microsoft Word" rather than the department's e-office system); creation date after the stated issue date; multiple incremental saves.
- Image forensics on scans: Error Level Analysis for pasted regions, font mismatch within a line (a changed date usually renders in a different font or at a different baseline), copy-move detection on seals and signatures.
- **Cross-application hash matching:** the same file submitted by two different applicants, or the same file used for two different document slots, is a strong fraud signal. Maintain a perceptual-hash index across the whole system. This is a capability a single-department portal structurally cannot have and a unified platform can — **make this a talking point.**
- Seal/signature presence detection in the expected region.

**Temporal**
- Document date ≤ today (no future-dated documents).
- Document date ≥ entity constitution date (a "GST certificate" predating incorporation is fabricated).
- Freshness window per document type (7/12: 3–6 months; medical certificates: 12 months; water test: 6 months).
- **Expiry-aware:** flag any document that expires before the expected approval date of the application it supports. Officers reject on this constantly and applicants never see it coming.

---

## PART D — CROSS-DOCUMENT CONSISTENCY MATRIX

These are the checks that make your product feel intelligent rather than like a file-upload form. Each one is a rule over ≥2 documents.

| # | Check | Documents involved | Severity |
|---|---|---|---|
| D-01 | Entity name identical (after normalising Pvt Ltd/Private Limited, &/and, punctuation) | PAN, CIN, GSTIN record, Udyam, bank, FSSAI, factory licence | Error |
| D-02 | PAN embedded in GSTIN == submitted PAN | PAN, GSTIN | Error |
| D-03 | PAN in MCA record == submitted PAN | PAN, CIN | Error |
| D-04 | PAN 4th char consistent with entity_type | PAN, CoI/deed | Error |
| D-05 | Premises address consistent (geocode within 100 m) | GST, FSSAI, factory licence, MPCB, electricity bill, property doc | Error |
| D-06 | Survey/Gat/CTS/Plot number identical | 7/12, sale deed, NA order, building plan, MPCB, factory licence | Error |
| D-07 | Plot area consistent within ±2% | 7/12, sale deed, building plan | Warning |
| D-08 | Built-up area on plan == area used for EIA 8(a) test and fire class | Building plan, OC, fire NOC | Error |
| D-09 | Product list: FSSAI ⊆ MPCB consented products (and gaps flagged both ways) | FSSAI, MPCB CTO | Error |
| D-10 | Declared capacity: DPR ≤ MPCB consented ≤/== factory licence | DPR, MPCB, factory licence | Error |
| D-11 | Water: process requirement ≤ sanctioned connection ≤/== MPCB consented | DPR, water connection, MPCB | Error |
| D-12 | Water balance closes (intake == product + evaporation + effluent + losses) | DPR, ETP design, MPCB | Warning |
| D-13 | Connected load ≤ sanctioned load ≤ factory licence max HP | DPR, MSEDCL sanction, factory licence | Error |
| D-14 | Worker count consistent | Factory licence, ESIC, EPFO, Shops & Est., FSSAI handler count | Warning |
| D-15 | FoSTaC supervisors ≥ ceil(food_handlers / 25) | FoSTaC certs, handler list | Error |
| D-16 | Medical certificates count == food handler count, all within 12 months | Medical certs, handler list | Error |
| D-17 | Capital investment consistent | DPR, CA certificate, Udyam, MPCB fee declaration, incentive application | Warning (fraud signal) |
| D-18 | Turnover consistent | ITR, GST returns, CA cert, Udyam, FSSAI category declaration | Warning (fraud signal) |
| D-19 | FSSAI category recomputed from turnover + KoB == category held | Turnover evidence, FSSAI licence | Error |
| D-20 | Occupier named in factory licence is a director in MCA records | Factory licence, MCA | Error |
| D-21 | Authorised signatory consistent across all forms + covered by board resolution + matches DSC | All forms, BR, DSC | Error |
| D-22 | Lease unexpired term > validity sought for every licence | Lease deed, all licences | Error |
| D-23 | Object clause permits food manufacture | MoA / partnership deed | Error |
| D-24 | Zone permits the MPCB category of this unit | Zoning cert, MPCB category | Error |
| D-25 | Sequencing: CTE before construction; CC before construction; OC before CTO; CTO before production; factory licence before production | All, with dates | Error |
| D-26 | No document expires before the dependent approval's expected issue date | All | Warning |
| D-27 | No file hash reused across applicants or across document slots | All | Fraud flag |
| D-28 | Bank account holder name == entity name (not proprietor's personal name for a company) | Cheque, CoI | Warning |

---

## PART E — DEPENDENCY GRAPH (drives your parallelisation claim)

Model approvals as a DAG, not a queue. Edges are hard dependencies.

```
E-01 Name reservation
  └─> E-02 Incorporation
        ├─> E-03 PAN/TAN ──> E-04 GST ──> E-05 Udyam
        ├─> E-06 Professional Tax
        └─> E-11 Bank account

L-02/L-01 Land acquisition
  ├─> L-03 NA permission (if agricultural)
  │     └─> L-04 Zoning certificate
  ├─> L-04 Zoning certificate
  └─> [L-04 + V-01 CTE + S-05 Fire Provisional] ──> L-06 Building plan / CC
                                                       └─> CONSTRUCTION
                                                             ├─> L-16 Occupancy Certificate
                                                             └─> S-06 Fire Final NOC

V-01 CTE ──> (construction) ──> V-02 CTO
L-16 OC + V-02 CTO ──> S-01/S-02 Factory Licence ──> PRODUCTION
V-02 CTO + L-16 OC + S-02 ──> F-02/F-03 FSSAI Licence
F-04 BIS (parallel, long lead — start early)
S-03 Boiler (parallel with construction)
F-05 Trade Licence, F-06 Legal Metrology (parallel, pre-operation)
X-01..X-07 Export registrations (fully parallel — no dependency on any of the above except IEC)
I-01..I-09 Incentives (post-commissioning, depend on EC/commercial production certificate)
```

**Parallelisable clusters** (run concurrently — this is your headline metric):
1. Entity/tax cluster (E-03 → E-12) — independent of land entirely
2. Land/zoning cluster (L-01 → L-05)
3. CTE + Fire Provisional — both feed building permission, neither depends on the other
4. Boiler + Electrical + Water/Drainage — during construction
5. All export registrations — independent
6. BIS — longest lead time of any food approval; **start at day zero, not at the end**

**Critical path** for a typical Orange-category food unit on MIDC land:
`MIDC allotment → CTE → Building permission → Construction → OC → CTO → Factory Licence → FSSAI Licence → Production`

Your demo metric: sequential execution of ~25 approvals vs DAG-scheduled execution. Compute both critical-path lengths from real SLA values and show the delta. **That number is your slide.**

---

## PART F — RULE SCHEMA (make it data, not code)

The whole point is that when a threshold changes — as FSSAI's did on 1 April 2026 — you edit a row, not a codebase.

```json
{
  "rule_id": "FSSAI-CAT-001",
  "version": 3,
  "approval_id": "F-02",
  "name": "FSSAI State Licence applicability by turnover",
  "condition": {
    "all": [
      { "fact": "annual_turnover", "op": ">", "value": 15000000 },
      { "fact": "annual_turnover", "op": "<=", "value": 500000000 }
    ]
  },
  "effect": { "requires": ["F-02"], "excludes": ["F-01", "F-03"] },
  "documents": ["DOC-FORM-B", "DOC-LAYOUT", "DOC-MACHINERY-LIST",
                "DOC-WATER-TEST", "DOC-MEDICAL-CERTS", "DOC-FOSTAC",
                "DOC-ADDRESS-PROOF", "DOC-ID-PROOF", "DOC-FSMS-PLAN"],
  "authority": "Maharashtra FDA",
  "sla_days": 60,
  "legal_basis": {
    "statute": "Food Safety and Standards Act, 2006",
    "instrument": "FSSAI Order dated 13 March 2026 read with FSS (Licensing and Registration of Food Businesses) Amendment Regulations, 2026",
    "url": "https://fssai.gov.in/",
    "effective_from": "2026-04-01",
    "supersedes": "FSSAI-CAT-001@v2"
  },
  "last_verified": "2026-08-29",
  "verified_by": "team",
  "confidence": "high"
}
```

**Non-negotiable schema fields, and why:**
- `legal_basis` with a citation and URL — an officer must be able to click through to the notification. Without this, your engine is an opinion.
- `effective_from` / `supersedes` — you must be able to answer "what were the rules on the date this application was filed?" Applications filed in March 2026 are governed by the old FSSAI thresholds. **Temporal rule versioning is not optional for a compliance system.**
- `last_verified` + `confidence` — surface stale rules to an admin. A rule not verified in 12 months should visibly degrade in the UI.
- `excludes` — suppressing inapplicable requirements is half the value. Telling an applicant they *don't* need NA permission because their plot is deemed-NA saves more time than telling them they do.

**Document rule schema:**
```json
{
  "doc_id": "DOC-GSTIN",
  "extractors": [{"field": "gstin", "method": "regex+ocr", "pattern": "\\d{2}[A-Z]{5}\\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]"}],
  "validations": [
    {"id": "V1", "type": "format", "rule": "checksum_mod36", "severity": "error"},
    {"id": "V2", "type": "semantic", "rule": "state_code == 27 if premises_state == 'MH'", "severity": "error"},
    {"id": "V3", "type": "cross_doc", "rule": "gstin[2:12] == pan", "severity": "error"},
    {"id": "V4", "type": "authenticity", "rule": "gstn_api.status == 'Active'", "severity": "error"},
    {"id": "V5", "type": "cross_doc", "rule": "geo_distance(gst_pob, premises) < 100m", "severity": "warning"}
  ],
  "preferred_source": "GSTN_API",
  "fallback": "upload"
}
```

---

## PART G — WHAT TO VERIFY BEFORE YOU SHIP

Do not take any of the following from a blog. Get them from the department.

1. **Factories Act worker threshold in Maharashtra** — the central Act says 10 with power / 20 without, but state amendments have raised this in several states. Confirm with DISH Maharashtra.
2. **Current MPCB category list post-harmonisation** — pull the actual annexure from the MPCB circulars of Feb/June 2025, including the new Blue category, rather than an older four-category list.
3. **Udyam investment/turnover limits** — revised recently; confirm current figures.
4. **FSSAI KoB eligibility matrix on FoSCoS** — the capacity-based overrides that force a State/Central licence regardless of turnover. This matrix is the authoritative source, not the turnover table alone.
5. **MAITRI 2.0 service catalogue** — the portal consolidates 119 services across 15 departments. Pull the actual list from `maitri.maharashtra.gov.in` "Know Your Approvals", which publishes document checklists and procedures per approval. **This is your single best seed source and it is publicly available.** Scrape it, normalise it, and you have a defensible knowledge base on day one.
6. **Maharashtra Industrial Policy incentive quantum and taluka classification** — incentive rates vary sharply by region (Vidarbha, Marathwada, and other backward talukas get higher slabs).
7. **Whether food processing appears in the EIA 2006 Schedule for your specific product** — most food processing does not require EC, but distilleries, sugar, and large slaughterhouses do, and the 20,000 sqm built-up area rule under item 8(a) catches large plants regardless of product.

---

## PART H — POSITIONING NOTES FOR THE JURY

Maharashtra already runs MAITRI 2.0, live since February 2025, consolidating 119 services from 15 departments with real-time tracking. Your evaluators from MSInS know this. Do not pitch "a single-window portal" — that exists.

Pitch the layer above it:

1. **A versioned, citable regulatory rule graph** that answers "which approvals, in what order, why, and under which notification" — with temporal versioning so an application is judged under the rules in force when it was filed. MAITRI lists approvals; it does not *derive* your personalised set from your project attributes.
2. **Pre-submission validation** — the 28 cross-document checks in Part D. Departments reject on these; no portal catches them before submission. Every one you catch is an avoided rejection cycle.
3. **Verified-source-first data reuse** — fetch from DigiLocker/GSTN/MCA/MahaBhulekh rather than accepting uploads, so a document verified once is never scrutinised again.
4. **DAG-based parallel scheduling** with a computed critical path, versus today's effectively sequential journey.
5. **Risk-based scrutiny + common inspection planning** — score applications on the fraud and inconsistency signals in Part C7 and Part D, auto-clear the clean low-risk ones, and pool MPCB, DISH, Fire, and FSSAI inspections into one visit.
6. **Cross-application fraud detection** — hash-matching across applicants, reused test reports, investment under-declaration. Structurally impossible for a single department; natural for a unified platform.

Frame every AI component as *assistive*: it prepares, validates, and prioritises. The officer decides. Say "deemed approval for low-risk with post-facto audit" only if you can point to the statutory provision that permits it.
