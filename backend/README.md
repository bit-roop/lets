# Regulatory Approval & Compliance Engine API (Milestone 1)

This backend service provides a RESTful API wrapper around the protected, deterministic regulatory engine (`engine-v3`). It acts strictly as an adapter and orchestrator, exposing regulatory derivation, catalogue metadata, authoritative sources, and persona data without altering regulatory semantics.

---

## 1. Setup & Installation

The backend requires **Python 3.10+**.

### Required Python Packages
```bash
pip install fastapi uvicorn pydantic requests
```

---

## 2. Running the API Server

From the `regulatory-engine/` directory:

```bash
uvicorn backend.main:app --reload --port 8000
```

The interactive OpenAPI / Swagger documentation is available at:
- **Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`

---

## 3. Endpoints Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check, engine version, verification status breakdown |
| `GET` | `/api/catalogue` | Returns all 16 regulatory requirements from `catalogue.json` |
| `GET` | `/api/sources` | Returns all 11 authoritative sources from `sources.json` |
| `GET` | `/api/personas` | Lists available demo personas (`persona_a`, `persona_b`, `persona_c`) |
| `GET` | `/api/personas/{id}` | Returns the fact vector for a specific persona |
| `POST` | `/api/evaluate` | Evaluates a fact vector against regulatory rules as of a given date |
| `POST` | `/api/workflow` | Builds committed and optional provisional deterministic schedules downstream of evaluation |
| `POST` | `/api/evaluate-with-workflow` | Returns the unchanged evaluation plus its workflow view |

Workflow semantics are documented in docs/WORKFLOW_CONTRACT.md. The workflow layer admits only
LEGAL and OPERATIONAL dependencies, never promotes candidate dependencies, excludes
NOT_APPLICABLE and CONFLICT requirements from schedules, and keeps UNKNOWN requirements
provisional only. Durations are opaque catalogue sla_days values; missing or invalid values
are surfaced rather than invented.

---

## 4. Endpoint Specifications & cURL Examples

### 4.1 Health Check
```bash
curl -X GET http://127.0.0.1:8000/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "engine_version": "3.0.0",
  "requirements_count": 16,
  "rules_count": 18,
  "sources_count": 11,
  "verification_summary": {
    "VERIFIED": 9,
    "SECONDARY": 6,
    "UNVERIFIED": 3
  }
}
```

---

### 4.2 Requirement Catalogue
```bash
curl -X GET http://127.0.0.1:8000/api/catalogue
```

**Sample Item in Response:**
```json
{
  "S-02": {
    "name": "Factory Licence",
    "requirement_type": "LICENCE",
    "authority": "Directorate of Industrial Safety and Health, Maharashtra",
    "department": "DISH",
    "statute": "Factories Act, 1948 s.6",
    "sla_days": 30,
    "validity_years": 1,
    "renewal_lead_days": 60
  }
}
```

---

### 4.3 Authoritative Sources
```bash
curl -X GET http://127.0.0.1:8000/api/sources
```

**Sample Item in Response:**
```json
{
  "SRC-FSSAI-001": {
    "source_type": "REGULATOR_ORDER",
    "authority": "FSSAI",
    "document_title": "Order revising turnover thresholds for licensing categories",
    "document_date": "2026-03-13",
    "section": "FSS (Licensing and Registration) Amendment Regulations, 2026",
    "verification_status": "VERIFIED",
    "verified_at": "2026-08-29",
    "source_url": "https://fssai.gov.in"
  }
}
```

---

### 4.4 Get Persona
```bash
curl -X GET http://127.0.0.1:8000/api/personas/persona_b
```

---

### 4.5 Regulatory Evaluation

```bash
curl -X POST http://127.0.0.1:8000/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "facts": {
      "stage": "new_setup",
      "entity_type": "private_limited",
      "location_authority": "MIDC",
      "land_classification": "midc_industrial",
      "builtup_area_sqm": 4200,
      "is_food_business": true,
      "annual_turnover": 80000000,
      "investment_plant_machinery": 60000000,
      "employees_total": 45,
      "workers_for_threshold": 67,
      "uses_power": true,
      "contract_labourers": 22,
      "food_handlers": 30,
      "boiler_operates": true,
      "boiler_capacity_litres": 500,
      "boiler_pressure_kg_cm2": 7,
      "boiler_water_temp_c": 170,
      "export": false,
      "multi_state_operation": false,
      "mpcb_category": null,
      "notified_industry_category": []
    },
    "as_of": "2026-08-29"
  }'
```

**Response Structure (Preserving Output Contract):**
```json
{
  "as_of": "2026-08-29",
  "summary": {
    "applicable": 10,
    "not_applicable": 2,
    "unknown": 3,
    "conflict": 0,
    "derived_facts": 1,
    "indeterminate_derivations": 0,
    "derived_fact_conflicts": 0,
    "derivation_passes": 2,
    "rules_evaluated": 15,
    "warnings": 6
  },
  "applicable": [ /* S-01, S-02, S-03, S-04, S-10, S-14, F-02, F-09, E-05, E-08 */ ],
  "not_applicable": [ /* F-01, F-03 (actively excluded) */ ],
  "unknown": [ /* E-09 (missing in_esic_implemented_area), V-01 (missing mpcb_category), V-02 (missing mpcb_category) */ ],
  "conflict": [],
  "derived_facts": {
    "msme_eligible": {
      "fact": "msme_eligible",
      "value": true,
      "value_type": "boolean",
      "rule_id": "MSME-ELIGIBLE-001",
      "rule_version": 1,
      "source": { "source_id": "SRC-MSME-001", ... },
      "verification_status": "VERIFIED",
      "input_facts": [],
      "derived_in_pass": 1,
      "operation": "constant"
    }
  },
  "indeterminate_derivations": [],
  "derived_fact_conflicts": [],
  "derivation_diagnostics": {
    "passes_run": 2,
    "max_passes": 10,
    "repeated_derivations_suppressed": 0,
    "reached_fixed_point": true
  },
  "warnings": [ ... ]
}
```

---

## 5. Architectural & Semantic Principles

1. **Three-Valued Logic Preservation:** Missing facts or `null` values are **never** converted to `False`. They evaluate strictly as `UNKNOWN`, surfacing explicit `missing_facts` prompts.
2. **Industry-Agnostic Adapter:** The API has zero hardcoded domain checks (`if industry == 'food'`). All domain logic lives in versioned regulatory JSON files.
3. **Stateless Derivation:** The evaluation endpoint is pure and deterministic. Given identical inputs and `as_of` date, it returns identical outputs.
