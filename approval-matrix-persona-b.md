# APPROVAL MATRIX — PERSONA B
### Sahyadri Foods Pvt Ltd · Fruit pulp processing · MIDC Ranjangaon, Pune
### Human-readable source of truth. JSON is generated from this, not the other way round.

---

## PART 0 — VERIFICATION LOG

Every regulatory fact carries one of three statuses. **Nothing marked UNVERIFIED goes into a demo claim.**

| Status | Meaning |
|---|---|
| **VERIFIED** | Confirmed from the department's own site or the notification itself. Source recorded. |
| **SECONDARY** | Consistent across multiple independent secondary sources. Plausible, not department-confirmed. |
| **UNVERIFIED** | Assumption. Team must confirm before it enters any demo claim. |

### Items closed this round

| # | Item | Finding | Status | Source |
|---|---|---|---|---|
| 1 | **Factories Act threshold, Maharashtra** | **20 workers with power / 40 without.** NOT the central 10/20. State has also extended the Act by notification to power looms, saw mills, and units using hazardous chemicals or flammable solvents even below 10 workers. | **VERIFIED** | DISH Maharashtra FAQ, mahadish.in |
| 2 | **Maharashtra Factories (Second Amendment) Rules, 2025** | Notified 3 Oct 2025, No. FAX-2025/CR-117(Part-I)/Lab-4. Full digitalisation of registration/licensing/renewal, revised fee schedule, mandatory mock drills, women night-shift safeguards. | **VERIFIED** | Notification citation |
| 3 | **Udyam / MSME limits** | Micro ≤₹2.5 cr investment **and** ≤₹10 cr turnover; Small ≤₹25 cr and ≤₹100 cr; Medium ≤₹125 cr and ≤₹500 cr. **Composite — both must hold.** Effective 1 Apr 2025. | **VERIFIED** | MSME Notification S.O. 1364(E) dt. 21 Mar 2025; PIB Year End Review 2025 |
| 4 | **FSSAI turnover thresholds** | Registration ≤₹1.5 cr; State Licence ₹1.5–50 cr; Central >₹50 cr. Effective 1 Apr 2026. | **VERIFIED** | FSSAI Order dt. 13 Mar 2026 r/w FSS (Licensing & Registration) Amendment Regulations, 2026 |
| 5 | **MPCB five-category structure** | Red / Orange / Green / White / **Blue** exists post-harmonisation. | **VERIFIED (existence)** | CPCB Directions dt. 12 Feb 2025; MPCB Circulars dt. 16 & 23 Jun 2025 |

### Items still open — assign to Domain lead

| # | Item | Why it matters | Where to get it |
|---|---|---|---|
| 6 | **MPCB category annexure** — the actual line item for fruit & vegetable processing, and its capacity band | Determines Orange vs Red for Persona B. **Our whole demo assumes Orange.** | mpcb.gov.in → Consent Management → Revised Industry Categorisation. Download the annexure PDF. |
| 7 | **FSSAI KoB eligibility matrix** | Some KoBs force State/Central licence on *capacity* regardless of turnover. Could override our turnover-derived answer. | FoSCoS portal, KoB eligibility matrix |
| 8 | **Fire NOC applicability thresholds** | We assume <15 m industrial needs NOC. Unconfirmed. | Maharashtra Fire Prevention & Life Safety Measures Act 2006 + Rules; Directorate of Maharashtra Fire Services |
| 9 | **Deemed-NA scope** | Determines whether we *suppress* NA permission. Suppression is a headline feature — must be right. | Maharashtra Land Revenue Code amendments; Collector's office |
| 10 | **MIDC building permission process** | Persona B is on MIDC land. Confirm MIDC issues building permission, not PMRDA/Grampanchayat. | permission.midcindia.org |
| 11 | **Boiler threshold** | We use >25 litres. Confirm against Boilers Act 1923 as applied in Maharashtra. | Directorate of Steam Boilers, Maharashtra |
| 12 | **EPR plastic packaging threshold** | Whether 40 TPA triggers registration. | CPCB EPR portal |

**Rule for the team: an UNVERIFIED row can exist in `rules.json` with `"confidence": "low"` and must render in the UI with a visible "unverified" badge. It must not appear in a spoken demo claim.**

---

## PART 1 — FROZEN FACT VECTOR

This is the input. Freeze it now; the whole demo depends on it being stable.

```json
{
  "stage": "new_setup",
  "entity_type": "private_limited",
  "entity_name": "Sahyadri Foods Private Limited",

  "district": "Pune",
  "taluka": "Shirur",
  "location_authority": "MIDC",
  "midc_estate": "Ranjangaon",
  "land_tenure": "midc_allotted",
  "land_classification": "midc_industrial",
  "dp_zone": "I-2",
  "plot_area_sqm": 8000,
  "builtup_area_sqm": 4200,
  "building_height_m": 12,
  "in_crz": false,
  "near_airport": false,
  "tree_felling": false,

  "product_categories": ["fruit_pulp", "fruit_juice_concentrate"],
  "process_types": ["washing","cutting","blanching","pulping",
                    "pasteurisation","aseptic_packing"],
  "installed_capacity_tpd": 12,
  "packaged_drinking_water": false,
  "alcoholic": false,
  "animal_origin_input": false,
  "organic_claim": false,

  "annual_turnover": 80000000,
  "investment_plant_machinery": 60000000,
  "total_project_cost": 95000000,

  "employees_total": 45,
  "uses_power": true,
  "contract_labourers": 22,
  "migrant_workers": 8,
  "motor_transport_workers": 6,
  "food_handlers": 30,
  "women_employed": 18,
  "night_shift": false,

  "electricity_supply": "HT",
  "connected_load_hp": 180,
  "dg_set": true,
  "dg_capacity_kva": 125,
  "lift": true,
  "boiler_operates": true,
  "boiler_capacity_litres": 500,
  "ammonia_refrigeration": true,
  "ammonia_charge_kg": 180,

  "water_source": "midc",
  "water_consumption_m3d": 45,
  "effluent_m3d": 30,
  "cetp_available": true,
  "waste_streams": ["solid","plastic"],
  "plastic_packaging_tpa": 40,

  "pre_packaged": true,
  "weighing_instruments": 6,
  "export": false
}
```

**Derived, not asked:**
- `mpcb_category` → Orange *(pending item 6)*
- `udyam_class` → investment ₹6 cr > ₹2.5 cr, so **Small** (₹6 cr ≤ ₹25 cr and ₹8 cr ≤ ₹100 cr)
- `is_factory` → 45 workers with power ≥ **20** → **true**
- `fssai_category` → ₹8 cr falls in ₹1.5–50 cr → **State Licence**

---

## PART 2 — THE MATRIX

Columns: **ID · Approval · Authority · Legal basis · Trigger · Evaluates to · SLA · Depends on · Status**

### 2.1 Entity & tax

| ID | Approval | Authority | Legal basis | Trigger | Result | SLA | Depends | Status |
|---|---|---|---|---|---|---|---|---|
| E-01 | Name reservation (SPICe+ A) | MCA | Companies Act 2013 | `entity_type in [pvt_ltd, ltd, opc, llp]` | ✅ | 2 d | — | SECONDARY |
| E-02 | Incorporation (CoI) | RoC Pune | Companies Act 2013 s.7 | same | ✅ | 7 d | E-01 | SECONDARY |
| E-03 | PAN + TAN | Income Tax | IT Act 1961 | always | ✅ | auto | E-02 | VERIFIED |
| E-04 | GST Registration | Maharashtra GST | CGST Act 2017 s.22 | manufacturer, inter-state supply | ✅ | 7 d | E-03 | SECONDARY |
| E-05 | Udyam Registration | MoMSME | MSMED Act 2006; S.O. 1364(E) 21.03.2025 | `investment ≤ 125cr AND turnover ≤ 500cr` | ✅ **Small** | instant | E-03,E-04 | **VERIFIED** |
| E-06 | Professional Tax (PTEC+PTRC) | Maharashtra Finance | Mah. State Tax on Professions Act 1975 | PTEC always; PTRC on employing staff | ✅ both | 10 d | E-03 | SECONDARY |
| E-07 | Shops & Establishments | Local body | Mah. Shops & Est. Act 2017 | office/admin premises | ✅ | 7 d | E-02 | SECONDARY |
| E-08 | EPFO registration | EPFO | EPF & MP Act 1952 | `employees ≥ 20` → 45 | ✅ | 3 d | E-02 | SECONDARY |
| E-09 | ESIC registration | ESIC | ESI Act 1948 | `employees ≥ 10` → 45 | ✅ | 3 d | E-02 | SECONDARY |

### 2.2 Land & construction — **MIDC branch**

| ID | Approval | Authority | Legal basis | Trigger | Result | SLA | Depends | Status |
|---|---|---|---|---|---|---|---|---|
| L-01 | MIDC plot allotment + possession | MIDC | MID Act 1961 | `location_authority == MIDC` | ✅ | 45 d | — | SECONDARY |
| L-02 | MIDC lease deed execution + registration | MIDC + IGR | MID Act 1961; Registration Act 1908 | after allotment | ✅ | 21 d | L-01 | SECONDARY |
| L-03 | **NA permission** | Collector | MLRC 1966 | `land_classification == agricultural AND authority != MIDC` | ❌ **EXCLUDED** | — | — | UNVERIFIED *(item 9)* |
| L-04 | MIDC building plan approval + CC | MIDC | MID Act; UDCPR | any construction on MIDC land | ✅ | 30 d | L-02, V-01, S-05 | UNVERIFIED *(item 10)* |
| L-05 | Environmental Clearance (building) | SEIAA | EIA Notification 2006 item 8(a) | `builtup_area ≥ 20000 sqm` → 4200 | ❌ **EXCLUDED** | — | — | SECONDARY |
| L-06 | Environmental Clearance (industry) | SEIAA/MoEFCC | EIA Notification 2006 Sch. | product in schedule (distillery/sugar/slaughterhouse) | ❌ **EXCLUDED** | — | — | SECONDARY |
| L-07 | CRZ Clearance | MCZMA | CRZ Notification 2011/2019 | `in_crz == true` | ❌ **EXCLUDED** | — | — | SECONDARY |
| L-08 | AAI height NOC | AAI | Aircraft Act 1934 | `near_airport == true` | ❌ **EXCLUDED** | — | — | SECONDARY |
| L-09 | Tree felling permission | Local/Forest | Mah. Tree Felling Act 1964 | `tree_felling == true` | ❌ **EXCLUDED** | — | — | SECONDARY |
| L-10 | MIDC water connection | MIDC | MID Act 1961 | `water_source == midc` | ✅ 45 m³/d | 21 d | L-02 | SECONDARY |
| L-11 | CGWA groundwater NOC | CGWA | EPA 1986 | `water_source == borewell` | ❌ **EXCLUDED** | — | — | SECONDARY |
| L-12 | HT electricity connection | MSEDCL | Electricity Act 2003 | `electricity_supply == HT` | ✅ 180 HP | 45 d | L-02 | SECONDARY |
| L-13 | Electrical installation safety cert | Chief Electrical Inspector | Electricity Act 2003; CEA Regs 2010 | HT connection / transformer | ✅ | 21 d | L-12 | SECONDARY |
| L-14 | MIDC drainage / CETP membership | MIDC | Water Act 1974 | `cetp_available AND effluent > 0` | ✅ 30 m³/d | 21 d | L-02 | SECONDARY |
| L-15 | Occupancy / Building Completion Cert | MIDC | UDCPR | after construction | ✅ | 30 d | L-04, S-06 | UNVERIFIED *(item 10)* |

### 2.3 Environment

| ID | Approval | Authority | Legal basis | Trigger | Result | SLA | Depends | Status |
|---|---|---|---|---|---|---|---|---|
| V-01 | **Consent to Establish (CTE)** | MPCB | Water Act 1974 s.25; Air Act 1981 s.21 | `mpcb_category != White` | ✅ Orange | 60 d | L-02 | **UNVERIFIED category** *(item 6)* |
| V-02 | **Consent to Operate (CTO)** | MPCB | Water Act 1974 s.25; Air Act 1981 s.21 | same, before production | ✅ | 60 d | V-01, L-15 | same |
| V-03 | Hazardous Waste authorisation | MPCB | HOWM Rules 2016 | hazardous waste generated | ❌ **EXCLUDED** | — | — | SECONDARY |
| V-04 | **EPR registration (plastic packaging)** | CPCB | Plastic Waste Mgmt Rules 2016 + EPR Guidelines | `plastic_packaging_tpa > 0` → 40 | ✅ | 30 d | E-04 | UNVERIFIED *(item 12)* |
| V-05 | Environmental Statement Form V | MPCB | EP Rules 1986 r.14 | consent holder, annual by 30 Sept | ✅ recurring | — | V-02 | SECONDARY |

### 2.4 Safety & labour

| ID | Approval | Authority | Legal basis | Trigger | Result | SLA | Depends | Status |
|---|---|---|---|---|---|---|---|---|
| S-01 | Factory plan approval (Form 1) | DISH | Factories Act 1948 s.6; Mah. Factories Rules 1963 | `is_factory` | ✅ | 30 d | L-04 | **VERIFIED trigger** |
| S-02 | **Factory Licence** | DISH | Factories Act 1948 s.6; **Mah. Factories (2nd Amdt) Rules 2025** | `(uses_power AND workers ≥ 20) OR (!uses_power AND workers ≥ 40)` → 45 with power | ✅ | 30 d | S-01, L-15 | **VERIFIED** |
| S-03 | Boiler registration | Dir. of Steam Boilers, Mah. | Boilers Act 1923 | `boiler_capacity_litres > 25` → 500 | ✅ | 30 d | L-04 | UNVERIFIED *(item 11)* |
| S-04 | Boiler attendant competency cert | same | Boiler Operation Engineers Rules | `boiler_operates` | ✅ | 15 d | S-03 | SECONDARY |
| S-05 | Fire NOC — Provisional | Maharashtra Fire Services | Mah. Fire Prevention & Life Safety Measures Act 2006 | industrial occupancy | ✅ | 30 d | L-02 | UNVERIFIED *(item 8)* |
| S-06 | Fire NOC — Final | same | same | before occupancy | ✅ | 30 d | S-05, construction | UNVERIFIED *(item 8)* |
| S-07 | Fire compliance Form B | Licensed agency → local authority | same | half-yearly, recurring | ✅ recurring | — | S-06 | UNVERIFIED |
| S-08 | Lift permit | PWD / Electrical Inspector | Mah. Lifts Act 1939 | `lift == true` | ✅ | 21 d | L-04 | SECONDARY |
| S-09 | PESO — ammonia pressure vessel | PESO | SMPV(U) Rules 2016 | `ammonia_charge_kg` above threshold → 180 | ⚠️ **CHECK** | 45 d | L-04 | UNVERIFIED |
| S-10 | CLRA registration (principal employer) | Labour Dept | CLRA Act 1970 | `contract_labourers ≥ 20` → 22 | ✅ | 15 d | E-02 | SECONDARY |
| S-11 | ISMW registration | Labour Dept | Inter-State Migrant Workmen Act 1979 | `migrant_workers ≥ 5` → 8 | ✅ | 15 d | E-02 | SECONDARY |
| S-12 | Motor Transport Workers registration | Labour Dept | MTW Act 1961 | `motor_transport_workers ≥ 5` → 6 | ✅ | 15 d | E-02 | SECONDARY |
| S-13 | Women night-shift permission | DISH / Labour | Factories Act; Mah. Factories (2nd Amdt) Rules 2025 | `night_shift AND women_employed > 0` → night_shift false | ❌ **EXCLUDED** | — | — | VERIFIED (rule exists) |
| S-14 | POSH Internal Committee | Internal | POSH Act 2013 s.4 | `employees ≥ 10` → 45 | ✅ | — | E-02 | SECONDARY |

### 2.5 Food-specific

| ID | Approval | Authority | Legal basis | Trigger | Result | SLA | Depends | Status |
|---|---|---|---|---|---|---|---|---|
| F-01 | FSSAI Registration | Local DO | FSS Act 2006; Order 13.03.2026 | `turnover ≤ 1.5cr` → ₹8 cr | ❌ **EXCLUDED** | — | — | **VERIFIED** |
| F-02 | **FSSAI State Licence** | Maharashtra FDA | FSS Act 2006; Order 13.03.2026 | `1.5cr < turnover ≤ 50cr` → ₹8 cr | ✅ | 60 d | V-02, L-15, S-02 | **VERIFIED** *(pending KoB override, item 7)* |
| F-03 | FSSAI Central Licence | FSSAI RO | same | `turnover > 50cr OR export OR multi-state` | ❌ **EXCLUDED** | — | — | **VERIFIED** |
| F-04 | BIS Licence | BIS | BIS Act 2016 | `packaged_drinking_water OR mandatory-cert product` | ❌ **EXCLUDED** | — | — | SECONDARY |
| F-05 | Health / Trade Licence | Local body | Mah. Municipal Corp Act | in municipal limits — **MIDC area, may not apply** | ⚠️ **CHECK** | 21 d | L-15 | UNVERIFIED |
| F-06 | Legal Metrology — Packaged Commodities | LM Dept Mah. | LM Act 2009; PC Rules 2011 | `pre_packaged == true` | ✅ | 21 d | E-04 | SECONDARY |
| F-07 | LM — verification & stamping | LM Dept Mah. | LM Act 2009 | `weighing_instruments > 0` → 6 | ✅ recurring | 15 d | — | SECONDARY |
| F-08 | Veterinary NOC | Animal Husbandry | — | `animal_origin_input` | ❌ **EXCLUDED** | — | — | SECONDARY |
| F-09 | FoSTaC trained supervisors | FSSAI training partner | FSS Regs | `ceil(food_handlers/25)` → ceil(30/25) = **2** | ✅ ×2 | 5 d | — | SECONDARY |
| F-10 | Food handler medical certificates | Registered practitioner | FSS Regs Sch.4 | all handlers, annual → **30 certs** | ✅ ×30 | — | — | SECONDARY |
| F-11 | State Excise licence | Mah. State Excise | Bombay Prohibition Act 1949 | `alcoholic == true` | ❌ **EXCLUDED** | — | — | SECONDARY |

### 2.6 Incentives

| ID | Scheme | Authority | Trigger | Result | Status |
|---|---|---|---|---|---|
| I-01 | PSI Eligibility Certificate | DIC Pune / MIDC | new unit + investment thresholds | ✅ | UNVERIFIED |
| I-02 | Stamp duty exemption | IGR + DIC | per industrial policy, taluka class | ⚠️ CHECK | UNVERIFIED |
| I-03 | Electricity duty exemption | MSEDCL + DIC | per industrial policy | ⚠️ CHECK | UNVERIFIED |
| I-04 | PMFME subsidy | MoFPI / SNA | **micro** food enterprise → we are **Small** | ❌ **EXCLUDED** | VERIFIED (class) |
| I-05 | PMKSY unit scheme | MoFPI | food processing unit | ✅ | UNVERIFIED |
| I-06 | CGTMSE guarantee | CGTMSE | micro/small + term loan | ✅ | SECONDARY |

---

## PART 3 — TALLY

| | Count |
|---|---|
| **Applicable** | **38** |
| **Excluded** | **16** |
| Needs verification before demo | 14 |
| Recurring obligations | 6 |

### The excluded list — this is a feature, show it

| Excluded | Because |
|---|---|
| NA permission | Land is already MIDC industrial — no agricultural conversion needed |
| EC (building) | Built-up 4,200 m² < 20,000 m² threshold |
| EC (industry) | Fruit processing is not in the EIA 2006 schedule |
| CRZ | Ranjangaon is inland |
| AAI height NOC | Not near an airport |
| Tree felling | No trees on plot |
| CGWA groundwater | MIDC supply, no borewell |
| Hazardous waste auth. | No hazardous waste stream |
| FSSAI Registration | Turnover ₹8 cr exceeds ₹1.5 cr |
| FSSAI Central | Turnover ₹8 cr below ₹50 cr; no export; single state |
| BIS | Not packaged drinking water; no mandatory-cert product |
| Veterinary NOC | No animal-origin input |
| State Excise | Non-alcoholic |
| Women night-shift permission | No night shift operated |
| PMFME | Classified Small, not Micro |
| Slaughterhouse approvals | Not applicable |

---

## PART 4 — EVIDENCE-FIRST OUTPUT (your format)

```json
{
  "requirement_id": "S-02",
  "name": "Factory Licence",
  "status": "APPLICABLE",
  "authority": "Directorate of Industrial Safety and Health, Maharashtra",
  "triggered_by": [
    {
      "rule_id": "DISH-FACTORY-001",
      "version": 1,
      "facts": {
        "employees_total": 45,
        "uses_power": true,
        "contract_labourers": 22
      },
      "evaluation": "employees_total (45) >= 20 AND uses_power == true",
      "source": {
        "authority": "DISH Maharashtra",
        "statute": "Factories Act, 1948 s.2(m) as applied in Maharashtra",
        "instrument": "Maharashtra Factories Rules 1963; Maharashtra Factories (Second Amendment) Rules 2025, Notification No. FAX-2025/CR-117(Part-I)/Lab-4 dt. 03.10.2025",
        "reference_url": "https://mahadish.in",
        "effective_from": "2025-10-03"
      },
      "note": "Maharashtra applies 20/40, NOT the central 10/20. Contract labourers count toward the threshold."
    }
  ],
  "confidence": "high",
  "last_verified": "2026-08-29",
  "depends_on": ["S-01", "L-15"],
  "documents": ["DOC-FORM1-PLAN", "DOC-COI", "DOC-OC",
                "DOC-MACHINERY-LIST", "DOC-LOAD-SANCTION",
                "DOC-OCCUPIER-DIRECTOR-PROOF"],
  "sla_days": 30
}
```

And for an exclusion — equally structured, because "why not" is as valuable as "why":

```json
{
  "requirement_id": "L-03",
  "name": "Non-Agricultural (NA) Permission",
  "status": "NOT_APPLICABLE",
  "excluded_by": [
    {
      "rule_id": "LAND-NA-001",
      "facts": {
        "land_classification": "midc_industrial",
        "location_authority": "MIDC"
      },
      "evaluation": "land_classification != 'agricultural' → NA permission not required",
      "source": {
        "statute": "Maharashtra Land Revenue Code, 1966",
        "note": "MIDC-allotted industrial land is already non-agricultural."
      }
    }
  ],
  "confidence": "medium",
  "last_verified": null,
  "warning": "Deemed-NA scope not yet verified against MLRC amendments. Flagged in UI."
}
```

---

## PART 5 — FILE LAYOUT (your structure)

```
rules/
├── common.json      E-01..E-09, S-10..S-14      entity, tax, labour
├── land.json        L-01..L-15                  land, construction, utilities
├── mpcb.json        V-01..V-05                  environment
├── dish.json        S-01..S-02                  factory  ← VERIFIED
├── boiler.json      S-03..S-04
├── fire.json        S-05..S-07
├── fssai.json       F-01..F-03, F-09..F-10      ← VERIFIED
├── food_other.json  F-04..F-08, F-11
├── local.json       F-05                        municipal
└── incentives.json  I-01..I-06

approvals.json       catalogue + depends_on edges (the DAG)
documents.json       doc specs, tiers, extractors
```

---

## PART 6 — WHAT TO DO NEXT, IN ORDER

1. **Domain lead:** close items 6–12. Item 6 (MPCB annexure) is the most urgent — our Orange assumption underpins the entire demo.
2. **Domain lead:** build the same matrix for Persona A. It should come out at ~12 applicable, ~25 excluded, and must show `is_factory == false` at 6 workers — the Maharashtra 20/40 threshold makes the exclusion cleaner than the central 10/20 would have.
3. **Engineer:** convert the VERIFIED rows to JSON first. `dish.json` and `fssai.json` are ready now.
4. **Engineer:** build the evaluator and run it against the frozen fact vector. Target output: 38 applicable, 16 excluded, each with `triggered_by` or `excluded_by`.
5. **Only then:** documents, DAG, UI.

**One correction to fold in:** the `verification_status` field must be first-class in the schema, not a comment. The UI renders an unverified badge from it, and the demo script never speaks a claim sourced from an UNVERIFIED row.
