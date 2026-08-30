"""M4 envelope and typed-field validation.  Results are FORMAT_ONLY."""

import re

GSTIN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
PAN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def validate_structured_fields(fields):
    issues = []
    normalized = dict(fields or {})
    for key, pattern in (("gstin", GSTIN), ("pan", PAN)):
        if key in normalized and normalized[key] is not None:
            value = str(normalized[key]).upper()
            if not pattern.fullmatch(value):
                issues.append({"field": key, "code": "INVALID_FORMAT", "message": "does not match expected format"})
            normalized[key] = value
    if normalized.get("gstin") and normalized.get("pan"):
        if normalized["gstin"][2:12] != normalized["pan"]:
            issues.append({"field": "gstin/pan", "code": "INCONSISTENT", "message": "GSTIN embedded PAN differs from supplied PAN"})
    if "aadhaar" in normalized:
        normalized["aadhaar"] = "********" + str(normalized["aadhaar"])[-4:]
        issues.append({"field": "aadhaar", "code": "PRIVACY_MASKED", "message": "full Aadhaar is not retained"})
    return {"status": "FORMAT_ONLY" if not any(i["code"] == "INVALID_FORMAT" for i in issues) else "FORMAT_INVALID", "issues": issues, "fields": normalized}
