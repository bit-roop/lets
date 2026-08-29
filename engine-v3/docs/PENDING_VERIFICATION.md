# Pending Source Verification

Nothing in this file may be implemented as a rule until the domain lead
records the source in `regulatory/sources/sources.json`.

---

## 1. MSME tier classification — BLOCKS a derived fact

**Status:** infrastructure complete, data insufficient.

`MSME-ELIGIBLE-001` derives `msme_eligible` (boolean) from the outer ceiling
that IS recorded: investment <= Rs 125 cr AND turnover <= Rs 500 cr.

It does NOT derive `msme_classification` (MICRO / SMALL / MEDIUM), because the
repository records only that outer ceiling. Deriving a tier from it would
classify every eligible enterprise as MEDIUM. Persona B (investment Rs 6 cr,
turnover Rs 8 cr) would be labelled MEDIUM when it is not.

### What is missing

The MICRO and SMALL boundaries under S.O. 1364(E) dt. 21.03.2025. Both
criteria are composite: investment AND turnover must both hold.

    MICRO   investment <= ?   AND turnover <= ?
    SMALL   investment <= ?   AND turnover <= ?
    MEDIUM  investment <= Rs 125 cr AND turnover <= Rs 500 cr   [recorded]

### How to close it

1. Obtain S.O. 1364(E) dt. 21.03.2025 from egazette.gov.in or msme.gov.in.
2. Record the micro and small figures in the `SRC-MSME-001` note.
3. Add three mutually exclusive rules to `regulatory/rules/msme.json`, each
   deriving `msme_classification` as an enum with
   `enum_values: ["MICRO","SMALL","MEDIUM"]`.
4. Mutual exclusivity matters: an enterprise inside the micro band is also
   inside the small and medium bands. Without exclusion clauses all three
   rules fire and the engine correctly reports a DERIVED_FACT_CONFLICT
   instead of a classification.
5. Add boundary tests at value-1 / value / value+1 on both axes per tier.

### Where it will be consumed

PMFME eligibility (I-04 in the approval matrix) is restricted to micro
enterprises. That rule cannot be written until the tier exists.

---

## 2. MPCB category — NOT IMPLEMENTED, do not placeholder

**Status:** explicitly deferred. Do not create a rule.

`MPCB-CTE-001` and `MPCB-CTO-001` consume `mpcb_category` as a supplied fact
and are marked UNVERIFIED. When the fact is absent they correctly yield
UNKNOWN.

The category for fruit and vegetable processing has NOT been retrieved. The
five-category structure (Red / Orange / Green / White / Blue) is confirmed to
exist following CPCB harmonisation directions of Feb 2025 and MPCB circulars
of 16 and 23 June 2025, but the line-item annexure has not been obtained.

**Do not write a rule deriving `mpcb_category`.** A placeholder here would be
worse than the current UNKNOWN, because UNKNOWN prompts the applicant while a
wrong category silently routes them down the wrong consent path.

### How to close it

1. Obtain the harmonised categorisation annexure from mpcb.gov.in.
2. Confirm the line item and capacity band for fruit and vegetable processing.
3. Record it as a new source with `verification_status: VERIFIED`.
4. Only then add a rule deriving `mpcb_category` as an enum.

---

## 3. ESIC threshold, Maharashtra — CONTRADICTORY SOURCES

`ESIC-REG-001` is UNVERIFIED and requires an `in_esic_implemented_area` fact
that is normally absent, so it yields UNKNOWN rather than a wrong answer.

Sources conflict between 10 and 20 employees for Maharashtra. Coverage is
district-dependent (partially implemented state) and a separate wage condition
applies. Obtain the state extension notification itself.

---

## 4. Others carried forward from the approval matrix

- Fire NOC applicability thresholds by height and occupancy class
- Deemed-NA scope under Maharashtra Land Revenue Code amendments
- Municipal trade/health licence checklist for the demo city
- MIDC building permission process
- FSSAI KoB eligibility matrix (capacity-based overrides on turnover)
- EPR plastic packaging threshold
- Full list of industries where the Factories Act is extended by notification
  below the normal threshold (DISH-FACTORY-002 records four categories from
  the DISH FAQ; the notified list is not exhaustive)
