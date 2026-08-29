# Prototypes — NOT part of the engine. Do not wire in as-is.

These two files were written BEFORE the three-valued / four-state hardening
rounds. They are not imported by the engine and must not be until reworked.

## Why they are quarantined

`validators.py` returns two-state results with a boolean `Result.ok`. Wiring
it into the engine as-is would reintroduce the exact collapse bug removed in
v1: a missing fact becoming FALSE instead of UNKNOWN. Any rework must return
the three-valued Tri type from engine/tri.py.

`extraction_router.py` is a document-tier registry for the document pipeline,
which the next agent is explicitly instructed NOT to start.

## What is still useful in them

GSTIN Luhn mod-36 checksum, Aadhaar Verhoeff, PAN 4th-character semantics,
the GSTIN-embeds-PAN cross-check, and the anchored-extraction technique.
The algorithms are sound; the result model is not.

## Known caveat

The GSTIN checksum was validated against one plausible number only. Test it
against a real GSTIN from any invoice before trusting it.
