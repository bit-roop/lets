"""
Extraction router — the answer to "does this scale to 40 documents?"

Adding document #41 means adding a dict entry to REGISTRY.
No new code paths. That is the whole architectural claim.
"""

import re
from datetime import datetime


# ── Tier B helper: anchored extraction ────────────────────────
# Government certificates have stable labels. Find the label, take
# what follows. Far more robust than positional or template matching,
# because it survives layout shifts and OCR noise.

def anchored(text: str, anchors: list, pattern: str, flags=re.I):
    """Search for `pattern` in the window following any of `anchors`."""
    for anchor in anchors:
        for m in re.finditer(re.escape(anchor), text, flags):
            window = text[m.end(): m.end() + 220]
            hit = re.search(pattern, window, flags)
            if hit:
                return hit.group(1).strip()
    # Fall back to a document-wide search
    hit = re.search(pattern, text, flags)
    return hit.group(1).strip() if hit else None


def parse_date(s):
    if not s:
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d",
                "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


# ── The registry ──────────────────────────────────────────────
# tier A → fetch, no parsing
# tier B → anchored regex over OCR text
# tier C → semantic (local LLM)
# tier D → route to human

REGISTRY = {

    # ---------- TIER A: fetch, never parse ----------
    "gst_certificate": {
        "tier": "A",
        "source": "GSTN",
        "fields": ["gstin", "legal_name", "principal_place", "status"],
        "validators": ["validate_gstin", "check_name_consistency"],
    },
    "pan_card": {
        "tier": "A",
        "source": "PROTEAN",
        "fields": ["pan", "name", "holder_type"],
        "validators": ["validate_pan"],
    },
    "satbara_7_12": {
        "tier": "A",
        "source": "MAHABHULEKH",
        "fields": ["survey_no", "area_ha", "holders",
                   "other_rights", "tenancy", "classification"],
        "validators": ["check_encumbrance", "check_freshness"],
        "freshness_days": 180,
    },
    "fssai_licence": {
        "tier": "A",
        "source": "FOSCOS",
        "fields": ["licence_no", "kob", "products", "premises", "valid_upto"],
        "validators": ["validate_fssai_category", "check_product_coverage"],
    },

    # ---------- TIER B: anchored regex ----------
    "mpcb_consent": {
        "tier": "B",
        "extract": {
            "consent_no": (["Consent No", "Consent Order No", "Format No"],
                           r"([A-Z0-9\-/]{6,})"),
            "valid_upto": (["Valid up to", "Valid upto", "Validity"],
                           r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})"),
            "category":   (["Category", "Scale & Category"],
                           r"\b(Red|Orange|Green|White|Blue)\b"),
            "water_m3d":  (["Water consumption", "Total water"],
                           r"([\d.]+)\s*(?:CMD|m3|M3|cum)"),
            "capital_inv": (["Capital Investment", "Gross fixed"],
                            r"(?:Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)"),
        },
        "validators": ["check_capacity_chain", "check_product_coverage",
                       "check_sequence"],
    },
    "factory_licence": {
        "tier": "B",
        "extract": {
            "licence_no":  (["Licence No", "License No"], r"([A-Z0-9\-/]{5,})"),
            "max_workers": (["Maximum number of workers", "Max. workers"],
                            r"(\d+)"),
            "max_hp":      (["Maximum horse power", "Max. H.P.", "HP"],
                            r"([\d.]+)"),
            "occupier":    (["Occupier", "Name of Occupier"], r"([A-Za-z .]{4,60})"),
            "valid_upto":  (["Valid up to", "Validity"],
                            r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})"),
        },
        "validators": ["check_load_chain", "check_occupier_is_director",
                       "check_worker_count"],
    },
    "fire_noc": {
        "tier": "B",
        "extract": {
            "noc_no":     (["NOC No", "Reference No"], r"([A-Z0-9\-/]{5,})"),
            "noc_type":   (["Type"], r"\b(Provisional|Final)\b"),
            "occupancy":  (["Occupancy", "Occupancy Class"], r"([A-Za-z ]{3,30})"),
            "height_m":   (["Height"], r"([\d.]+)\s*m"),
            "valid_upto": (["Valid up to"], r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})"),
        },
        "validators": ["check_noc_is_final", "check_occupancy_match"],
    },
    "boiler_certificate": {
        "tier": "B",
        "extract": {
            "reg_no":       (["Registration No", "Boiler No"], r"([A-Z0-9\-/]{4,})"),
            "capacity_l":   (["Capacity", "Volume"], r"([\d.]+)\s*(?:L|litre)"),
            "next_due":     (["Next due", "Due date", "Valid up to"],
                             r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})"),
        },
        "validators": ["check_not_expired", "check_boiler_declared"],
    },
    "water_test_report": {
        "tier": "B",
        "extract": {
            "lab_name":   (["Laboratory", "Lab Name", "Tested at"], r"([A-Za-z ,.&]{5,70})"),
            "nabl_no":    (["NABL", "Accreditation No"], r"([A-Z0-9\-]{4,})"),
            "sample_date":(["Date of Sampling", "Sample Date", "Collected on"],
                           r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})"),
        },
        "validators": ["check_nabl_accredited", "check_freshness",
                       "check_parameters_within_is10500", "check_reuse"],
        "freshness_days": 180,
    },
    "medical_certificate": {
        "tier": "B",
        "multi": True,          # one per food handler
        "extract": {
            "handler_name": (["Name of", "Employee"], r"([A-Za-z .]{4,50})"),
            "doctor_reg":   (["Reg. No", "Registration No", "MCI"], r"([A-Z0-9/]{4,})"),
            "issue_date":   (["Date", "Issued on"],
                             r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})"),
        },
        "validators": ["check_freshness", "check_count_matches_handlers"],
        "freshness_days": 365,
    },
    "electricity_sanction": {
        "tier": "B",
        "extract": {
            "consumer_no":    (["Consumer No", "Consumer Number"], r"([0-9]{8,14})"),
            "sanctioned_load":(["Sanctioned Load", "Contract Demand"],
                               r"([\d.]+)\s*(?:kVA|KVA|HP|kW)"),
            "supply_type":    (["Supply", "Connection"], r"\b(LT|HT)\b"),
        },
        "validators": ["check_load_chain"],
    },

    # ---------- TIER C: semantic, local LLM ----------
    "moa_aoa": {
        "tier": "C",
        "question": ("Do the main objects permit manufacturing and processing "
                     "of food products? Answer YES or NO, then quote the "
                     "clause you relied on."),
        "validators": ["check_object_clause_permits_food"],
    },
    "lease_deed": {
        "tier": "C",
        "question": ("Extract: lease start date, lease end date, whether "
                     "industrial use is permitted, and whether the lessor's "
                     "consent is required for statutory licences. Return JSON."),
        "validators": ["check_lease_covers_licence", "check_permitted_use"],
    },
    "project_report": {
        "tier": "C",
        "question": ("Extract: installed capacity with units, total capital "
                     "investment, process water requirement per day, "
                     "connected electrical load, and total manpower. "
                     "Return JSON with nulls for anything absent."),
        "validators": ["check_capacity_chain", "check_load_chain",
                       "check_water_balance", "check_investment_consistency"],
    },

    # ---------- TIER D: route to a human ----------
    "layout_plan": {
        "tier": "D",
        "reason": ("Hygiene zoning and product-flow separation require "
                   "visual judgement. Present to the officer with a "
                   "structured checklist rather than auto-deciding."),
        "checklist": [
            "Raw material and finished goods areas separated",
            "Unidirectional product flow, no crossing of raw and cooked",
            "Toilets do not open directly into a processing area",
            "Handwash stations at processing entry points",
            "Drainage flows away from clean zones",
            "Total area reconciles with the approved building plan",
        ],
    },
}


# ── The router: one function, all documents ───────────────────

def extract(doc_type: str, payload: dict) -> dict:
    """
    payload carries whichever of these apply:
      text        - OCR output          (tier B)
      fetched     - source system data  (tier A)
      file_path   - original file       (tiers C, D)
    """
    spec = REGISTRY.get(doc_type)
    if not spec:
        return {"error": f"unknown document type: {doc_type}"}

    tier = spec["tier"]

    if tier == "A":
        data = payload.get("fetched") or {}
        return {"tier": "A", "source": spec["source"], "fields": data,
                "confidence": 1.0 if data else 0.0,
                "note": "Fetched from source; no extraction performed."}

    if tier == "B":
        text = payload.get("text", "")
        out, found = {}, 0
        for field, (anchors, pattern) in spec["extract"].items():
            val = anchored(text, anchors, pattern)
            out[field] = val
            found += val is not None
        total = len(spec["extract"])
        conf = found / total if total else 0.0
        return {"tier": "B", "fields": out, "confidence": round(conf, 2),
                "note": ("Extraction confident." if conf >= 0.8 else
                         "Low confidence — route to manual review.")}

    if tier == "C":
        return {"tier": "C", "requires_llm": True,
                "prompt": spec["question"],
                "note": "Send to local model (Ollama). Never auto-reject "
                        "on a model's reading alone — flag for the officer."}

    return {"tier": "D", "requires_human": True,
            "checklist": spec.get("checklist", []),
            "note": spec.get("reason", "")}


def coverage_report():
    from collections import Counter
    tiers = Counter(s["tier"] for s in REGISTRY.values())
    total = sum(tiers.values())
    auto = tiers["A"] + tiers["B"]
    print(f"Documents in registry : {total}")
    for t in "ABCD":
        print(f"  Tier {t}: {tiers[t]:>2}")
    print(f"Fully automatic (A+B) : {auto}/{total} = {auto/total:.0%}")
    print(f"Needs a local LLM     : {tiers['C']}/{total} = {tiers['C']/total:.0%}")
    print(f"Routed to an officer  : {tiers['D']}/{total} = {tiers['D']/total:.0%}")


if __name__ == "__main__":
    coverage_report()
