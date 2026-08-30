# Milestone 4 Document Contract

Milestone 4 is a downstream evidence/readiness layer. `engine-v3` remains the sole authority for approval applicability and `backend/workflow` remains the sole M3 workflow implementation. M4 consumes their outputs and never mutates them.

## Scope

The seeded regulatory catalogue covers only F-02 (FSSAI State Licence), S-02 (Maharashtra Factory Licence), and S-03 (Maharashtra Boiler Registration). The remaining thirteen current approvals are explicitly `UNSUPPORTED` because no authoritative checklist was supplied for them.

An evidence item has an `item_kind`: `UPLOAD_DOCUMENT`, `FORM_INPUT`, `FEE`, `INSPECTION_EVENT`, or `DECLARATION`. Boiler details, owner details, fees, and tentative inspection dates are not flattened into PDF requirements.

## Provenance

Every `DocumentRequirement` has `source_id`, checklist item, verification status, and `last_verified`. The registry rejects missing provenance. `VERIFIED_SCOPE_UNCLEAR`, `SECONDARY`, and `UNSUPPORTED` are not promoted to `VERIFIED`.

## Readiness

`READY` means every applicable, supported, blocking mandatory item is supplied. `INCOMPLETE` means a known blocking item is missing or unusable. `INDETERMINATE` means a condition cannot be evaluated, applicability is unknown/conflicting, or reuse/scope is unresolved. `UNSUPPORTED` means no authoritative checklist exists. `UNSUPPORTED` can never be rendered as `READY`.

Supporting items do not block readiness. Provisional M3 requirements do not silently gate committed readiness.

## Submission semantics

M4 records presence, metadata, hash, envelope checks, and structured fields. `PROVIDED_UNVALIDATED` does not mean authentic or government-issued. Typed checks are explicitly `FORMAT_ONLY`; cross-document checks establish consistency only. Full Aadhaar is not persisted.

## API

- `GET /api/documents/requirements` returns the static registry, coverage, provenance, and conditions.
- `POST /api/documents/requirements` accepts `{facts, as_of, approval_ids, include_provisional}` and evaluates conditions against existing facts without changing engine applicability.
- `POST /api/documents/submit` accepts multipart uploads or JSON structured/form items. Uploads are stored in an OS temporary quarantine directory, not in tracked source files.
- `GET /api/documents/readiness?application_id=...&facts=<url-encoded-json>` returns per-approval readiness and submissions.

Unsupported approvals are successful responses with an explicit `UNSUPPORTED` coverage/readiness status, not fabricated checklists.

## M5 boundary

OCR, parsing, classification from file contents, authenticity, issuer/API checks, QR/signature verification, and human-review escalation are intentionally absent. M5 may consume `DocumentSubmission` and attach a separate verification result; it must not turn a checksum or format match into authenticity.
