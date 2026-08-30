# Verification Contract (Milestone 5, slice 1)

This describes what Milestone 5 actually does in this build. It does not
describe planned capability. Anything not implemented is named as such.

## What M5 is for

M4 establishes what evidence an applicant must supply. M5 examines the files
they supplied and answers one question:

> Does this file appear to correspond to the evidence that was asked for, what
> can safely be read from it, what deterministic inconsistencies exist, and
> what needs a person to look at it?

M5 does not decide whether an approval applies, in what order approvals should
be handled, or what evidence is required. Those remain engine-v3, M3 and M4.

## Position in the architecture

```
Applicant facts -> engine-v3 -> M3 workflow -> M4 requirements/readiness -> M5 evidence verification
```

The flow is one-directional, and M5 is **given** M4's decision rather than
causing one.

### How M4 state reaches M5

`POST /api/verification/analyze` and `POST /api/verification/evidence` both
require an `m4_result`: the payload from `POST /api/documents/requirements`,
already computed and already held by the caller. `M4Context`
(`backend/verification/m4_context.py`) indexes that payload. It performs no
evaluation; it reads `condition_state`, `condition_trace`, `engine_state` and
`coverage.status` as strings M4 produced, and never consults `condition` itself.

`m4_gateway.py` retains only genuinely static reads: the document registry
(JSON from `regulatory-documents/`) and the in-memory submission store. It must
never import `backend.documents.service`, because
`requirements_for_application` and `readiness_for_application` call
`evaluate_facts` / `build_workflow_for_facts` and `evaluate_condition`
internally. Calling them would re-run the engine while appearing to read M4 —
which is exactly the defect an earlier revision of this layer shipped.

Re-running usually produces the same answer, which is what makes it dangerous:
M5 could silently diverge from the applicability the applicant was shown (a
different `as_of`, a different workflow-awareness flag, a fact edited between
calls) with nothing to surface the divergence.

Enforced by test:

- **Dynamically** (`backend/tests/test_m5_engine_isolation.py`): every engine,
  workflow and condition entry point is patched to raise, at every binding site,
  and the whole M5 pipeline is then exercised. A negative control first proves
  the sabotage does trip M4 itself, so the other assertions cannot pass
  vacuously. A static grep alone is insufficient and was the reason the original
  violation went undetected.
- **Statically** (`backend/tests/test_m5_isolation.py`): no module under
  `backend/verification/` imports `engine.*`, `backend.workflow.*`, or
  `backend.documents.service`; no module except `m4_gateway.py` imports
  `backend.documents.*`; no module names `evaluate_facts`,
  `build_workflow_for_facts` or `evaluate_condition`.
- `engine-v3/`, `backend/workflow/`, `backend/documents/` and
  `regulatory-documents/` are byte-identical before and after a full analysis
  run.
- Every `DocumentSubmission` field is unchanged after analysis.
- `DocumentSubmission.state` is never set to `VALID`.
- The `/api/documents/readiness` and `/api/documents/requirements` responses are
  byte-identical with M5 mounted and records present.

## Applicability: observed, never computed

M5 copies M4's own `condition_state` and never re-evaluates a condition.

| M4 says | M5 observes | `requirement_match` | Behaviour |
|---|---|---|---|
| `condition_state == "TRUE"` | `APPLICABLE_CONDITION_TRUE` | from classification | full pipeline |
| `condition_state == "FALSE"` | `NOT_APPLICABLE_CONDITION_FALSE` | `NOT_APPLICABLE` | not analysed |
| `condition_state == "UNKNOWN"` | `UNRESOLVED_CONDITION_UNKNOWN` | **`INDETERMINATE`** | not analysed; uncertainty preserved |
| engine state not `APPLICABLE` | `UNRESOLVED_ENGINE_STATE` | `INDETERMINATE` | not analysed |
| approval `UNSUPPORTED` | `UNSUPPORTED_APPROVAL` | `NOT_APPLICABLE` | not analysed |

**Unknown never becomes not-applicable.** "We do not know whether this is
required" and "this is not required" are different claims, and merging them
would quietly drop a requirement the applicant may owe.

This is not an edge case here. Of the twelve facts used by M4 conditions, only
`entity_type` is collectable through the intake wizard, and
`manufacturing_processing` is absent from every persona in the repository. Both
conditional F-02 requirements therefore report `UNKNOWN` on every real run.

## State model

Orthogonal axes with one derived disposition. A single flat status cannot say
that a document is correctly identified *and* readable *and* has no available
authenticity mechanism, which is the normal case here.

```
M4_APPLICABILITY_OBSERVED  (copied from M4)
INGESTION                  NOT_ANALYZED | INGESTED | MEDIA_REJECTED | INGEST_FAILED
EXTRACTION                 NOT_ATTEMPTED | NATIVE_TEXT | OCR_TEXT | PARTIAL | UNREADABLE | FAILED
CLASSIFICATION             MATCHES_EXPECTED | DIFFERENT_KNOWN_TYPE | UNKNOWN_TYPE
                           | MULTI_DOCUMENT | INSUFFICIENT_EVIDENCE
REQUIREMENT_MATCH          MATCH | LIKELY_MATCH | MISMATCH | INDETERMINATE | NOT_APPLICABLE
INTERNAL_CONSISTENCY       CONSISTENT | INCONSISTENT | INDETERMINATE
CROSS_CONSISTENCY          CONSISTENT | INCONSISTENT | INDETERMINATE | NO_COMPARANDA
AUTHENTICITY               NOT_ASSESSED | NOT_APPLICABLE_APPLICANT_AUTHORED
                           | NO_MECHANISM_AVAILABLE | UNVERIFIED | SUPPORTED | VERIFIED | FAILED
DISPOSITION (derived)      NOT_ANALYZED | REJECTED_STRUCTURAL | NEEDS_APPLICANT_ACTION
                           | HUMAN_REVIEW_REQUIRED | ACCEPTED_FOR_REVIEW
```

`OCR_TEXT`, `MULTI_DOCUMENT`, `UNVERIFIED`, `SUPPORTED` and `VERIFIED` are
declared but never produced in this build.

### Disposition precedence

1. No profile for the document → `NOT_ANALYZED`
2. M4 says not applicable or unsupported → `NOT_ANALYZED`
3. M4 applicability unresolved → `NOT_ANALYZED`, reason `M4_APPLICABILITY_UNRESOLVED`
4. Guard rejected the media → `REJECTED_STRUCTURAL`
5. Extractor raised → `HUMAN_REVIEW_REQUIRED`, retryable system fault
6. Nothing readable in the document → `HUMAN_REVIEW_REQUIRED`
7. `requirement_match == MISMATCH` → `NEEDS_APPLICANT_ACTION`
8. A blocking finding returned `MISMATCH` → `NEEDS_APPLICANT_ACTION`
9. Any human-review trigger → `HUMAN_REVIEW_REQUIRED`
10. Otherwise → `ACCEPTED_FOR_REVIEW`

Rows 5 and 6 sit above 7 and 8 deliberately. An unreadable or crashed document
has not failed a check; it has failed to be checked.

**Authenticity is not an input to disposition.** `ACCEPTED_FOR_REVIEW` is
reachable — and in this build always is reached — with authenticity
unestablished.

## Semantic rules

- A field that was not found produces `UNKNOWN`, never `MISMATCH`.
- `UNREADABLE` is a property of the document; `FAILED` is a property of the
  system. They route differently.
- A `BLOCKING` finding may only cite `PROFILE_GROUNDED` fields. The profile
  loader rejects any profile that violates this.
- Low confidence routes to review; it never converts a value into a wrong value.
- Filename is never an input to classification. `classifier.classify` has no
  parameter through which one could arrive.

## Authenticity

Five distinct states, kept apart:

| State | Meaning |
|---|---|
| `NOT_APPLICABLE_APPLICANT_AUTHORED` | The applicant fills this form in themselves. There is no issuer to check against. |
| `NO_MECHANISM_AVAILABLE` | The document has an issuer, but no verification service is available to this system. |
| `SUPPORTED` | Machine-checkable evidence exists but the issuer was not consulted. **Not produced in this build.** |
| `VERIFIED` | An authoritative gateway confirmed the document. **Unreachable in this build.** |
| `FAILED` | A cryptographic or issuer check did not pass. **Not produced in this build.** |

`VERIFIED` is guarded in code: `models.assert_authenticity_writable` raises
unless the result came from a gateway reporting `authoritative=True`. No
gateway is configured. A profile cannot declare `VERIFIED` or `SUPPORTED`; the
loader rejects both.

Nothing in this build establishes that a document is genuine, and nothing in
this build establishes that it is not.

## What is implemented in slice 1

- Media guard. The controls actually enforced are: byte-signature versus
  declared MIME, a 10 MB ceiling, the requirement's accepted-format list,
  encrypted-PDF rejection, active-content rejection (`/JavaScript`, `/JS`,
  `/Launch`, `/EmbeddedFile`, `/OpenAction`), page-count limit, and storage-path
  confinement under M4's quarantine root. No decompression-ratio control is
  declared or implemented; naming one would misrepresent the guard.
- Native PDF text extraction, page by page, with per-page text-layer detection.
- Deterministic content classification against all loaded profiles.
- Anchored field extraction with character-span and page provenance.
- Deterministic checks: identity anchor presence, date well-formedness, date not
  in the future, integer plausibility.
- SQLite record persistence with a 90-day retention window.
- The M4/M5 two-layer readiness overlay.
- Origin restriction on M5 responses.

## What is not implemented

OCR. Image documents. LLM or semantic extraction. QR decoding. PDF signature
validation. Any authoritative gateway. Cross-document consistency checking.
Asynchronous analysis. The officer review queue.

`GET /api/verification/capabilities` reports each of these as absent, by name,
at runtime.

## Test dependencies

`backend/requirements-dev.txt` declares `pytest` and `httpx`. `httpx` is
required by `fastapi.testclient.TestClient`; it was previously relied on without
being declared, so a clean checkout could not run the suite.

## Profiles

A profile describes how to inspect an evidence item M4 already requires. It
lives in `regulatory-verification/`, separate from `regulatory-documents/`,
which is M4's and is never edited for M5's convenience.

A profile **cannot** declare an obligation, approval, requirement id, blocking
policy, condition, applicability, readiness rule, SLA, dependency, item kind, or
accepted format. The loader rejects each of those keys by name, and rejects any
`document_id` not already present in the M4 registry.

Every anchor and every field records the repository location that grounds it.
Fields are `PROFILE_GROUNDED` or `RESEARCH_REQUIRED`; only the former may
participate in a blocking finding.

### Grounding limitation

The repository contains **no field schema for any evidence item**. The M4 specs
carry `name`, `item_kind`, `description`, `accepted_formats` and `reusable`, and
nothing about what is printed on a form. No specimen of either shipped form was
available.

Consequently the only `PROFILE_GROUNDED` information in both profiles is
document identity and the named authority. Dates, occupier name, applicant name
and worker count are extracted, displayed, and marked `RESEARCH_REQUIRED` — they
cannot block an applicant. Each profile records this in
`provenance.limitations`.

## Storage

SQLite at `M5_STORE_PATH` (default `.m5-data/records.db`, gitignored). Stores
verification records, extracted field metadata, findings, provenance and review
tickets.

### What is stored, and in what form

`ExtractedField.raw_value` and `normalized_value` are **transient**. They exist
so the deterministic checks can run against the real value, and they are
excluded from serialisation, which is the only route to the record store and to
the API. What survives is `display_value`, chosen by the `sensitivity` the
profile declares for that field:

| Sensitivity | Stored as | Example |
|---|---|---|
| `NON_SENSITIVE` | verbatim | `Directorate of Industrial Safety and Health` |
| `DATE` | verbatim | `2026-05-12` |
| `QUANTITY` | verbatim | `67` |
| `PERSONAL_NAME` | initials only | `A**** D*******` |
| `IDENTIFIER` | trailing fragment only | `******234F` |

Every profile field must declare a sensitivity; the loader rejects one that does
not, because a field without a sensitivity has no defined storage rule.
`Finding.observed` is reduced through the same function, so a check cannot
smuggle an unreduced value into the record.

The record therefore still shows that a name was found, which name it roughly
was, and that the extraction succeeded — enough for review and for a later
masked cross-document comparison — without the record holding the name.

Not stored: document bytes, page images, raw extracted text, raw field values,
unmasked names, unmasked identifiers. M5 references M4's stored file by
`submission_id` and `sha256`; it never makes a second permanent copy of an
applicant's document.

`file_identity` is keyed on `sha256` alone, deliberately not on M4's
`(application_id, document_id, sha256)` dedup tuple, so that the same file
submitted into two different evidence slots is visible as reuse.

## CORS

There is no router-level CORS in Starlette or FastAPI. `add_middleware` inserts
at position 0 and `build_middleware_stack` wraps `self.router` in reverse, so
every middleware wraps the whole application.

The app runs `CORSMiddleware` with `allow_origins=["*"]` and
`allow_credentials=True`. In that combination Starlette echoes the caller's
Origin rather than emitting `*`, so any origin gets credentialed access. That is
acceptable for M4 responses, which carry no extracted document content, and not
for M5 responses, which do.

`VerificationCorsMiddleware` is registered after `CORSMiddleware`, making it the
outermost layer, and corrects the headers for `/api/verification` paths only.
Allowed origins come from `M5_ALLOWED_ORIGINS`. Every other path, including all
M4 and M3 endpoints, passes through untouched, and the global CORS configuration
is deliberately left unchanged.

## API

All additive under `/api/verification`.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/analyze` | Examine one submitted document against a supplied M4 result. Synchronous. |
| `GET` | `/records?application_id=` | Records for an application. |
| `POST` | `/evidence` | Echoes the supplied M4 readiness verbatim, plus the M5 evidence layer. |

### Why `/evidence` is a POST, and not `GET /readiness`

The route was planned as `GET /api/verification/readiness?application_id=&facts=`.
It became `POST /api/verification/evidence` because the boundary changed, and
the name and verb now both follow from that.

- **A POST, because M5 requires a body it cannot reconstruct.** The caller must
  supply the M4 requirements result, and optionally the M4 readiness result.
  These are full documents, not query parameters. The earlier signature took
  `facts` — and taking facts is precisely what let M5 re-run the engine. There
  is no longer any parameter from which M5 could derive applicability, and that
  is deliberate: the absence of a `facts` argument is what makes the boundary
  structural rather than conventional. A GET whose semantics depend on a
  multi-kilobyte body would be the wrong shape regardless.
- **Named `/evidence`, not `/readiness`, because M5 does not produce readiness.**
  Readiness is M4's word for M4's answer. M5 returns evidence findings, and
  echoes M4's readiness back beside them under a separate key. Naming the route
  `/readiness` would have implied M5 computes one.

The caller must supply:

| Field | Source | Required | Use |
|---|---|---|---|
| `application_id` | the caller | yes | scopes stored records |
| `m4_result` | `POST /api/documents/requirements` | yes | the applicability M5 observes |
| `m4_readiness` | `GET /api/documents/readiness` | no | echoed back verbatim under `m4_readiness` |

M5 does not compute applicability, does not produce M4 readiness, and does not
alter either. `m4_readiness` in the response is the caller's own payload
returned unchanged; when it is omitted the key is `null` rather than filled in
by M5.
| `GET` | `/capabilities` | What this build can and cannot establish. |

### The evidence denominator

An M4 requirement is counted in `m5_supported_applicable_count` only if all six
hold: the approval is `SUPPORTED`; the engine state is `APPLICABLE`; the item is
an `UPLOAD_DOCUMENT`; the requirement is not `UNSUPPORTED`; M4's condition is
strictly `TRUE`; and an M5 profile exists.

Everything excluded is counted on its own line —
`m5_no_profile_count`, `m5_applicability_unresolved_count`,
`m5_not_applicable_count`, `m5_non_upload_excluded_count`,
`m5_unsupported_excluded_count` — so nothing is silently dropped, and
requirements whose applicability M4 reports as unknown are never folded into the
inapplicable count.

The response carries both `m4_readiness` and `m5_evidence` as separate keys.
There is no unqualified `readiness` key at the top level, so the two layers
cannot be confused. `m4_readiness` is the caller's own M4 payload echoed back
unmodified — M5 has no code path that produces a readiness result, so
"unchanged by M5" holds by construction rather than by intent.

### Errors and logging

Unexpected failures return a fixed generic message. Exception text, stack
traces, filesystem paths, document text and extracted values are never returned
to the client.

Server-side logging is sanitised for the same reason. `logger.exception` writes
the exception message and the full traceback, and both can carry things this
layer must not retain — a PDF parser typically embeds the absolute file path in
its error, and an exception raised while handling extracted text can contain the
text. A log line is still a place data comes to rest.

So `backend/verification/logging_safe.py` logs no exception message and no
traceback text. It records the stage, the exception *type*, the basename and
line number of the innermost frame, and the `submission_id` / `application_id`
— and drops any identifier that is not a plain token. Debugging from a type and
a line number is harder than debugging from a traceback; the cost is accepted
deliberately.

## Prompt injection

No language model is used in this build, so there is no injection surface yet.
The boundary that will apply when one is added: document text is data, never
instructions; the adapter gets no tools, no network, no filesystem and no state
writes; output is schema-validated; and no model output may write a favourable
terminal value on any axis. That last property is the load-bearing one, because
it bounds the impact of a successful injection to zero rather than merely
reducing its probability.
