"""
Document validation engine — SIH 2026, PS 26130.

Layer 1: Format / checksum   (pure arithmetic, no dependencies)
Layer 2: Semantic            (does the encoded meaning match declared facts?)
Layer 3: Cross-document      (do independent documents agree?)
Layer 4: Temporal            (validity, freshness, sequencing)
Layer 5: Authenticity        (API / DigiLocker — mocked for hackathon)
Layer 6: Tamper detection    (file forensics)
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
import re


class Severity(Enum):
    ERROR = "error"      # blocks submission
    WARNING = "warning"  # flag to officer, allow submission
    INFO = "info"


@dataclass
class Finding:
    check_id: str
    severity: Severity
    message: str
    remedy: str = ""
    legal_basis: str = ""


@dataclass
class Result:
    findings: list = field(default_factory=list)

    def add(self, *a, **kw):
        self.findings.append(Finding(*a, **kw))

    @property
    def ok(self):
        return not any(f.severity == Severity.ERROR for f in self.findings)

    @property
    def errors(self):
        return [f for f in self.findings if f.severity == Severity.ERROR]


# ─────────────────────────────────────────────────────────────
# LAYER 1 — FORMAT AND CHECKSUM
# ─────────────────────────────────────────────────────────────

PAN_RE   = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
CIN_RE   = re.compile(r"^[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$")
IFSC_RE  = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
UDYAM_RE = re.compile(r"^UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}$")

PAN_ENTITY_CHAR = {
    "P": "individual", "C": "company", "F": "firm_or_llp", "H": "huf",
    "A": "aop", "T": "trust", "B": "boi", "G": "government",
    "J": "artificial_juridical", "L": "local_authority",
}

GST_STATE = {"27": "Maharashtra", "29": "Karnataka", "24": "Gujarat",
             "07": "Delhi", "33": "Tamil Nadu", "09": "Uttar Pradesh"}

CIN_OWNERSHIP = {"PLC": "public_limited", "PTC": "private_limited",
                 "OPC": "one_person_company", "FTC": "foreign_subsidiary",
                 "GOI": "government", "SGC": "state_government",
                 "NPL": "section_8", "ULL": "unlimited"}

ALNUM36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin_checksum(first14: str) -> str:
    """Luhn mod-36 over the first 14 characters. Returns the expected 15th."""
    total, factor, mod = 0, 2, 36
    for ch in reversed(first14):
        digit = ALNUM36.index(ch)
        addend = factor * digit
        factor = 1 if factor == 2 else 2
        addend = (addend // mod) + (addend % mod)
        total += addend
    return ALNUM36[(mod - (total % mod)) % mod]


# Verhoeff tables — used by Aadhaar
_D = [
    [0,1,2,3,4,5,6,7,8,9], [1,2,3,4,0,6,7,8,9,5], [2,3,4,0,1,7,8,9,5,6],
    [3,4,0,1,2,8,9,5,6,7], [4,0,1,2,3,9,5,6,7,8], [5,9,8,7,6,0,4,3,2,1],
    [6,5,9,8,7,1,0,4,3,2], [7,6,5,9,8,2,1,0,4,3], [8,7,6,5,9,3,2,1,0,4],
    [9,8,7,6,5,4,3,2,1,0],
]
_P = [
    [0,1,2,3,4,5,6,7,8,9], [1,5,7,6,2,8,3,0,9,4], [5,8,0,3,7,9,6,1,4,2],
    [8,9,1,6,0,4,3,5,2,7], [9,4,5,3,1,2,6,8,7,0], [4,2,8,6,5,7,3,9,0,1],
    [2,7,9,3,8,0,6,4,1,5], [7,0,4,6,9,1,3,2,5,8],
]


def verhoeff_ok(number: str) -> bool:
    if not number.isdigit():
        return False
    c = 0
    for i, ch in enumerate(reversed(number)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def validate_pan(pan: str, declared_entity_type: str = None) -> Result:
    r = Result()
    pan = (pan or "").strip().upper()

    if not PAN_RE.match(pan):
        r.add("PAN-F1", Severity.ERROR,
              "PAN is not in the valid format.",
              "PAN is 10 characters: five letters, four digits, one letter.")
        return r

    # Layer 2 — the 4th character encodes holder type
    kind = PAN_ENTITY_CHAR.get(pan[3])
    if kind is None:
        r.add("PAN-S1", Severity.ERROR,
              f"'{pan[3]}' is not a recognised PAN holder-type character.")
    elif declared_entity_type:
        expected = {
            "proprietorship": "individual", "individual": "individual",
            "partnership": "firm_or_llp", "llp": "firm_or_llp",
            "private_limited": "company", "public_limited": "company",
            "opc": "company", "trust": "trust", "huf": "huf",
            "cooperative_society": "aop",
        }.get(declared_entity_type)
        if expected and kind != expected:
            r.add("PAN-S2", Severity.ERROR,
                  f"PAN belongs to a {kind.replace('_',' ')}, but you declared "
                  f"a {declared_entity_type.replace('_',' ')}.",
                  "A company must apply using the company's own PAN, not a "
                  "director's personal PAN.")
    return r


def validate_gstin(gstin: str, pan: str = None,
                   premises_state_code: str = None) -> Result:
    r = Result()
    gstin = (gstin or "").strip().upper()

    if not GSTIN_RE.match(gstin):
        r.add("GST-F1", Severity.ERROR, "GSTIN is not in the valid format.",
              "GSTIN is 15 characters: 2-digit state code, 10-character PAN, "
              "entity number, the letter Z, and a checksum.")
        return r

    if gstin[14] != gstin_checksum(gstin[:14]):
        r.add("GST-F2", Severity.ERROR,
              "GSTIN checksum failed — this number cannot be genuine.",
              "Check for a typo, or that the document has not been altered.")

    if premises_state_code and gstin[:2] != premises_state_code:
        got = GST_STATE.get(gstin[:2], f"state code {gstin[:2]}")
        want = GST_STATE.get(premises_state_code, premises_state_code)
        r.add("GST-S1", Severity.ERROR,
              f"GSTIN is registered in {got}, but the premises are in {want}.",
              "Register the factory as a place of business in this state.")

    # Layer 3 — the strongest free cross-check available
    if pan and gstin[2:12] != pan.strip().upper():
        r.add("GST-X1", Severity.ERROR,
              "The PAN embedded in the GSTIN does not match the PAN submitted.",
              f"GSTIN contains {gstin[2:12]}; you submitted {pan.upper()}.")
    return r


def validate_cin(cin: str, declared_entity_type: str = None,
                 today: date = None) -> Result:
    r = Result()
    cin = (cin or "").strip().upper()
    today = today or date.today()

    if not CIN_RE.match(cin):
        r.add("CIN-F1", Severity.ERROR, "CIN is not in the valid format.")
        return r

    nic = cin[1:6]
    year = int(cin[8:12])
    ownership = cin[12:15]

    if not (1857 <= year <= today.year):
        r.add("CIN-S1", Severity.ERROR,
              f"CIN encodes incorporation year {year}, which is not plausible.")

    kind = CIN_OWNERSHIP.get(ownership)
    if kind is None:
        r.add("CIN-S2", Severity.WARNING,
              f"'{ownership}' is not a standard CIN ownership code.")
    elif declared_entity_type and kind != declared_entity_type:
        r.add("CIN-S3", Severity.ERROR,
              f"CIN indicates a {kind.replace('_',' ')}, but you declared a "
              f"{declared_entity_type.replace('_',' ')}.")

    # NIC division 10/11 = food and beverage manufacturing
    if not nic.startswith(("10", "11")):
        r.add("CIN-S4", Severity.WARNING,
              f"The industry code in the CIN ({nic}) is not a food "
              "manufacturing code.",
              "Check that the object clause in the MoA permits food "
              "manufacture — a company cannot lawfully manufacture outside "
              "its stated objects.")
    return r


def validate_aadhaar(aadhaar: str) -> Result:
    """Validates structure only. NEVER store the full number."""
    r = Result()
    digits = re.sub(r"\D", "", aadhaar or "")

    if len(digits) != 12:
        r.add("ADH-F1", Severity.ERROR, "Aadhaar must be 12 digits.")
        return r
    if digits[0] in "01":
        r.add("ADH-F2", Severity.ERROR, "Aadhaar cannot begin with 0 or 1.")
    if not verhoeff_ok(digits):
        r.add("ADH-F3", Severity.ERROR,
              "Aadhaar checksum failed — this number is not valid.")
    r.add("ADH-P1", Severity.INFO,
          f"Store only the masked form XXXXXXXX{digits[-4:]}.",
          "Prefer DigiLocker or offline eKYC XML over an uploaded scan.")
    return r


# ─────────────────────────────────────────────────────────────
# LAYER 3 — CROSS-DOCUMENT CONSISTENCY
# ─────────────────────────────────────────────────────────────

_SUFFIXES = [
    "private limited", "pvt ltd", "pvt. ltd.", "pvt limited",
    "public limited", "ltd", "limited", "llp", "and company", "& co",
]


def normalise_name(name: str) -> str:
    s = (name or "").lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for suf in sorted(_SUFFIXES, key=len, reverse=True):
        if s.endswith(suf):
            s = s[: -len(suf)].strip()
            break
    return s


def jaro_winkler(s1: str, s2: str) -> float:
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    window = max(len(s1), len(s2)) // 2 - 1
    window = max(window, 0)
    f1 = [False] * len(s1)
    f2 = [False] * len(s2)
    matches = 0
    for i, c in enumerate(s1):
        for j in range(max(0, i - window), min(len(s2), i + window + 1)):
            if not f2[j] and s2[j] == c:
                f1[i] = f2[j] = True
                matches += 1
                break
    if matches == 0:
        return 0.0
    k = trans = 0
    for i in range(len(s1)):
        if f1[i]:
            while not f2[k]:
                k += 1
            if s1[i] != s2[k]:
                trans += 1
            k += 1
    trans //= 2
    j = (matches / len(s1) + matches / len(s2)
         + (matches - trans) / matches) / 3
    prefix = 0
    for a, b in zip(s1[:4], s2[:4]):
        if a != b:
            break
        prefix += 1
    return j + prefix * 0.1 * (1 - j)


def check_name_consistency(names: dict, threshold: float = 0.95) -> Result:
    """names = {'PAN': 'X', 'GST': 'Y', 'CIN': 'Z', ...}"""
    r = Result()
    items = [(k, normalise_name(v)) for k, v in names.items() if v]
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            (ka, va), (kb, vb) = items[i], items[j]
            score = jaro_winkler(va, vb)
            if score < threshold:
                r.add("X-NAME", Severity.ERROR,
                      f"Entity name differs between {ka} and {kb} "
                      f"(similarity {score:.2f}).",
                      f"{ka}: '{names[ka]}'  vs  {kb}: '{names[kb]}'")
    return r


def check_capacity_chain(dpr_tpd: float, mpcb_tpd: float,
                         factory_tpd: float = None) -> Result:
    r = Result()
    if mpcb_tpd is not None and dpr_tpd is not None and dpr_tpd > mpcb_tpd:
        r.add("X-CAP1", Severity.ERROR,
              f"Planned capacity ({dpr_tpd} TPD) exceeds the capacity "
              f"consented by MPCB ({mpcb_tpd} TPD).",
              "Apply for consent amendment before commissioning.",
              "Water Act 1974 s.25 / Air Act 1981 s.21")
    if factory_tpd is not None and dpr_tpd is not None and dpr_tpd > factory_tpd:
        r.add("X-CAP2", Severity.ERROR,
              f"Planned capacity ({dpr_tpd} TPD) exceeds the factory "
              f"licence capacity ({factory_tpd} TPD).")
    return r


def check_product_coverage(fssai_products: set, mpcb_products: set) -> Result:
    r = Result()
    missing = set(fssai_products) - set(mpcb_products)
    if missing:
        r.add("X-PROD", Severity.ERROR,
              "Products on the FSSAI licence are not covered by the MPCB "
              f"consent: {', '.join(sorted(missing))}.",
              "Manufacturing a product outside your consent is an offence "
              "under the Water and Air Acts.")
    extra = set(mpcb_products) - set(fssai_products)
    if extra:
        r.add("X-PROD2", Severity.WARNING,
              "MPCB consent covers products not on the FSSAI licence: "
              f"{', '.join(sorted(extra))}.")
    return r


def check_load_chain(connected_hp: float, sanctioned_hp: float,
                     factory_max_hp: float) -> Result:
    r = Result()
    if connected_hp > sanctioned_hp:
        r.add("X-LOAD1", Severity.ERROR,
              f"Connected load ({connected_hp} HP) exceeds the sanctioned "
              f"load ({sanctioned_hp} HP).")
    if connected_hp > factory_max_hp:
        r.add("X-LOAD2", Severity.ERROR,
              f"Connected load ({connected_hp} HP) exceeds the maximum HP "
              f"permitted by the factory licence ({factory_max_hp} HP).")
    return r


def check_fostac_ratio(food_handlers: int, trained_supervisors: int) -> Result:
    r = Result()
    import math
    required = math.ceil(food_handlers / 25) if food_handlers else 0
    if trained_supervisors < required:
        r.add("X-FOSTAC", Severity.ERROR,
              f"{food_handlers} food handlers require {required} trained "
              f"supervisor(s); {trained_supervisors} provided.",
              "One FoSTaC-trained Food Safety Supervisor per 25 food handlers.")
    return r


# ─────────────────────────────────────────────────────────────
# LAYER 4 — TEMPORAL
# ─────────────────────────────────────────────────────────────

FRESHNESS_DAYS = {
    "satbara_7_12": 180,
    "property_card": 180,
    "water_test_report": 180,
    "medical_certificate": 365,
    "bank_statement": 90,
    "ca_certificate": 180,
}


def check_freshness(doc_type: str, issued: date, today: date = None) -> Result:
    r = Result()
    today = today or date.today()
    limit = FRESHNESS_DAYS.get(doc_type)

    if issued > today:
        r.add("T-FUT", Severity.ERROR,
              f"Document is dated {issued}, which is in the future.")
        return r
    if limit:
        age = (today - issued).days
        if age > limit:
            r.add("T-STALE", Severity.ERROR,
                  f"{doc_type.replace('_',' ')} is {age} days old; the "
                  f"accepted limit is {limit} days.",
                  "Obtain a fresh copy before submitting.")
        elif age > limit * 0.8:
            r.add("T-SOON", Severity.WARNING,
                  f"This document expires for these purposes in "
                  f"{limit - age} days.")
    return r


def check_lease_covers_licence(lease_end: date, licence_validity_years: int,
                               today: date = None) -> Result:
    """The rule most portals miss entirely."""
    r = Result()
    today = today or date.today()
    needed = today + timedelta(days=365 * licence_validity_years)
    if lease_end < needed:
        months = max(0, (lease_end - today).days // 30)
        r.add("T-LEASE", Severity.ERROR,
              f"The lease expires on {lease_end} ({months} months remaining), "
              f"but you are applying for a {licence_validity_years}-year "
              "licence.",
              "Renew or extend the lease, or apply for a shorter validity.")
    return r


def check_sequence(events: dict) -> Result:
    """events = {'cte_date': ..., 'construction_start': ..., ...}"""
    r = Result()
    order = [
        ("cte_date", "construction_start",
         "Consent to Establish must be obtained before construction begins.",
         "Water Act 1974 s.25"),
        ("commencement_certificate", "construction_start",
         "The Commencement Certificate must precede construction."),
        ("occupancy_certificate", "cto_date",
         "The Occupancy Certificate should precede Consent to Operate."),
        ("cto_date", "production_start",
         "Consent to Operate must be obtained before production begins.",
         "Water Act 1974 s.25 / Air Act 1981 s.21"),
        ("factory_licence_date", "production_start",
         "The factory licence must be in force before manufacturing begins.",
         "Factories Act 1948 s.6"),
        ("fssai_licence_date", "production_start",
         "The FSSAI licence must be in force before food is manufactured.",
         "FSS Act 2006 s.31"),
    ]
    for item in order:
        before, after, msg = item[0], item[1], item[2]
        basis = item[3] if len(item) > 3 else ""
        b, a = events.get(before), events.get(after)
        if b and a and b > a:
            r.add(f"T-SEQ-{before}", Severity.ERROR, msg,
                  f"{before.replace('_',' ')} is dated {b}, but "
                  f"{after.replace('_',' ')} is {a}.", basis)
    return r


# ─────────────────────────────────────────────────────────────
# LAYER 5 — AUTHENTICITY (mock this for the hackathon)
# ─────────────────────────────────────────────────────────────

class VerificationGateway:
    """
    Real integrations need registered access and cannot be obtained in a
    hackathon window. Mock deterministically, label the source clearly in
    the UI, and describe the integration path in the pitch.
    """

    MOCK = {
        "27AAECS1234F1Z5": {"status": "Active",
                            "legal_name": "Sahyadri Foods Private Limited",
                            "pob": "Plot D-42, MIDC Ranjangaon, Pune"},
    }

    def verify_gstin(self, gstin):
        rec = self.MOCK.get(gstin)
        return {"verified": rec is not None, "source": "GSTN (mocked)",
                "data": rec}

    def fetch_digilocker(self, doc_type, consent_token):
        return {"verified": True, "source": "DigiLocker (mocked)",
                "signed": True}


# ─────────────────────────────────────────────────────────────
# LAYER 6 — TAMPER DETECTION
# ─────────────────────────────────────────────────────────────

GOV_PRODUCERS = ["itext", "crystal reports", "jasper", "e-office", "digilocker"]
CONSUMER_EDITORS = ["microsoft word", "photoshop", "canva", "ilovepdf",
                    "smallpdf", "libreoffice"]


def analyse_pdf(path: str) -> Result:
    """Requires: pip install pypdf"""
    r = Result()
    try:
        from pypdf import PdfReader
    except ImportError:
        r.add("PDF-DEP", Severity.INFO, "pypdf not installed; skipped.")
        return r

    try:
        reader = PdfReader(path)
    except Exception as e:
        r.add("PDF-ERR", Severity.ERROR, f"Could not read PDF: {e}")
        return r

    meta = reader.metadata or {}
    producer = str(meta.get("/Producer", "")).lower()
    creator = str(meta.get("/Creator", "")).lower()

    for editor in CONSUMER_EDITORS:
        if editor in producer or editor in creator:
            r.add("PDF-PROD", Severity.WARNING,
                  f"This document was produced using {editor}, which is not "
                  "a government document system.",
                  "Genuine certificates are normally issued as digitally "
                  "signed PDFs. Request the original.")
            break

    # Incremental saves — a signed document modified after signing
    with open(path, "rb") as f:
        eof_count = f.read().count(b"%%EOF")
    if eof_count > 1:
        r.add("PDF-INCR", Severity.WARNING,
              f"The file contains {eof_count} save generations, indicating "
              "it was modified after creation.")

    if "/Encrypt" in reader.trailer:
        r.add("PDF-ENC", Severity.ERROR, "The PDF is password-protected.")

    sig = False
    try:
        fields = reader.get_fields() or {}
        sig = any(str(v.get("/FT")) == "/Sig" for v in fields.values())
    except Exception:
        pass
    r.add("PDF-SIG", Severity.INFO if sig else Severity.WARNING,
          "Digital signature present." if sig
          else "No digital signature found; authenticity cannot be verified "
               "from the file alone.")
    return r


def perceptual_hash(path: str):
    """Requires: pip install imagehash pillow"""
    try:
        import imagehash
        from PIL import Image
        return str(imagehash.phash(Image.open(path)))
    except Exception:
        return None


def check_reuse(phash: str, seen: dict) -> Result:
    """
    A capability a single-department portal structurally cannot have:
    detecting the same file reused across applicants or document slots.
    """
    r = Result()
    if phash and phash in seen:
        r.add("F-REUSE", Severity.WARNING,
              f"This file was previously submitted as "
              f"{seen[phash]['doc_type']} by application "
              f"{seen[phash]['app_id']}.",
              "Route to an officer for manual review.")
    return r
