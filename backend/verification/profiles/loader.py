"""Profile loading and validation.

A profile says how to inspect an evidence item M4 already requires.  It cannot
create a requirement, an approval, an obligation, an applicability condition, a
blocking policy, a readiness rule, or a workflow edge.  That is enforced here,
at load time, by rejecting the keys that could express those concepts -- not by
convention and not by code review.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from .. import privacy, states

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROFILE_ROOT = PROJECT_ROOT / "regulatory-verification" / "profiles"

#: Keys a profile may carry.  Anything else is rejected.
ALLOWED_TOP_LEVEL = frozenset({
    "profile_id", "version", "supersedes", "document_id", "display_name",
    "applicant_summary", "expected_identity", "fields", "checks",
    "thresholds", "authenticity", "human_review", "provenance",
})

#: Keys that would let a profile restate or contradict M4/M3/engine-v3.
#: Listed explicitly so the error message can name the concept, not just the key.
FORBIDDEN_TOP_LEVEL = {
    "obligation": "M4 owns whether evidence is mandatory/conditional/supporting",
    "approval_id": "M4 owns approval membership",
    "requirement_id": "M4 owns requirement identity",
    "blocking": "M4 owns blocking policy",
    "condition": "engine-v3 and M4 own applicability conditions",
    "condition_description": "M4 owns condition descriptions",
    "applicability": "M5 observes applicability and never declares it",
    "verification_status": "M4 owns requirement verification status",
    "coverage": "M4 owns approval coverage",
    "readiness": "M4 owns readiness semantics",
    "sla_days": "the catalogue and M3 own durations",
    "depends_on": "M3 owns dependencies and ordering",
    "item_kind": "M4's DocumentSpec owns item_kind",
    "accepted_formats": "M4's DocumentSpec owns accepted formats",
}


class ProfileError(ValueError):
    pass


class VerificationProfile:
    def __init__(self, raw: Dict[str, Any], path: Path = None):
        self.raw = raw
        self.path = path
        self.profile_id = raw["profile_id"]
        self.version = raw["version"]
        self.document_id = raw["document_id"]
        self.display_name = raw.get("display_name", "")
        self.applicant_summary = raw.get("applicant_summary", "")
        self.expected_identity = raw["expected_identity"]
        self.fields = raw.get("fields", [])
        self.checks = raw.get("checks", [])
        self.thresholds = raw.get("thresholds", {})
        self.authenticity = raw["authenticity"]
        self.human_review = raw.get("human_review", {})
        self.provenance = raw["provenance"]

    @property
    def anchors_required(self) -> List[Dict[str, Any]]:
        return self.expected_identity.get("anchors_required", [])

    @property
    def anchors_forbidden(self) -> List[Dict[str, Any]]:
        return self.expected_identity.get("anchors_forbidden", [])

    def field(self, field_id: str):
        for f in self.fields:
            if f["field_id"] == field_id:
                return f
        return None

    def grounded_field_ids(self) -> List[str]:
        return [f["field_id"] for f in self.fields
                if f["field_source"] == states.PROFILE_GROUNDED]

    def as_dict(self):
        return json.loads(json.dumps(self.raw))


def validate(raw: Dict[str, Any], known_document_ids, spec_lookup, unsupported_document_ids):
    """Validate one profile against the M4 registry.  Raises ProfileError."""
    if not isinstance(raw, dict):
        raise ProfileError("profile must be a JSON object")

    for key in FORBIDDEN_TOP_LEVEL:
        if key in raw:
            raise ProfileError(
                f"profile {raw.get('profile_id', '<unknown>')!r} declares forbidden key "
                f"{key!r}: {FORBIDDEN_TOP_LEVEL[key]}. A verification profile cannot "
                f"create or restate a regulatory requirement.")

    unknown = set(raw) - ALLOWED_TOP_LEVEL
    if unknown:
        raise ProfileError(
            f"profile {raw.get('profile_id', '<unknown>')!r} has unrecognised keys: "
            f"{sorted(unknown)}")

    for required in ("profile_id", "version", "document_id", "expected_identity",
                     "authenticity", "provenance"):
        if not raw.get(required):
            raise ProfileError(f"profile is missing required key {required!r}")

    document_id = raw["document_id"]
    if document_id not in known_document_ids:
        raise ProfileError(
            f"profile {raw['profile_id']!r} references unknown document_id "
            f"{document_id!r}. A profile cannot introduce a document requirement "
            f"that does not exist in the M4 registry.")

    spec = spec_lookup(document_id)
    if spec.item_kind != "UPLOAD_DOCUMENT":
        raise ProfileError(
            f"profile {raw['profile_id']!r} targets {document_id!r} whose M4 item_kind "
            f"is {spec.item_kind}; M5 only inspects UPLOAD_DOCUMENT items.")

    if document_id in unsupported_document_ids:
        raise ProfileError(
            f"profile {raw['profile_id']!r} targets {document_id!r}, which M4 marks "
            f"UNSUPPORTED; unsupported evidence cannot be submitted or verified.")

    # Provenance discipline
    prov = raw["provenance"]
    for key in ("author", "created", "basis"):
        if not prov.get(key):
            raise ProfileError(f"profile {raw['profile_id']!r} provenance is missing {key!r}")

    # Authenticity may not be self-declared as established.
    capability = raw["authenticity"].get("capability")
    if capability not in states.DECLARABLE_AUTHENTICITY:
        raise ProfileError(
            f"profile {raw['profile_id']!r} declares authenticity capability "
            f"{capability!r}. Only {sorted(states.DECLARABLE_AUTHENTICITY)} are "
            f"declarable; VERIFIED and SUPPORTED require an authoritative gateway.")
    if not raw["authenticity"].get("explanation"):
        raise ProfileError(f"profile {raw['profile_id']!r} authenticity needs an explanation")

    # Field grounding
    field_ids = set()
    for f in raw.get("fields", []):
        fid = f.get("field_id")
        if not fid or fid in field_ids:
            raise ProfileError(f"duplicate or missing field_id in {raw['profile_id']!r}")
        field_ids.add(fid)
        if f.get("field_source") not in states.FIELD_SOURCES:
            raise ProfileError(f"field {fid!r} has invalid field_source")
        if f.get("sensitivity") not in privacy.SENSITIVITIES:
            raise ProfileError(
                f"field {fid!r} must declare a sensitivity from "
                f"{sorted(privacy.SENSITIVITIES)}. Sensitivity governs what is "
                f"persisted, so a field without one has no defined storage rule.")
        if not f.get("basis"):
            raise ProfileError(f"field {fid!r} must record the basis for its extraction target")

    # The core grounding rule: a BLOCKING check may only cite grounded fields.
    grounded = {f["field_id"] for f in raw.get("fields", [])
                if f["field_source"] == states.PROFILE_GROUNDED}
    for check in raw.get("checks", []):
        if check.get("severity") not in states.SEVERITIES:
            raise ProfileError(f"check {check.get('check_id')!r} has invalid severity")
        for cid in check.get("inputs", []):
            if cid not in field_ids and cid != "__identity__":
                raise ProfileError(
                    f"check {check.get('check_id')!r} cites unknown field {cid!r}")
        if check["severity"] == states.BLOCKING:
            ungrounded = [c for c in check.get("inputs", [])
                          if c != "__identity__" and c not in grounded]
            if ungrounded:
                raise ProfileError(
                    f"check {check['check_id']!r} is BLOCKING but cites "
                    f"RESEARCH_REQUIRED field(s) {ungrounded}. Only grounded "
                    f"information may block an applicant.")

    # A checklist must be source-grounded; the repository contains none, so any
    # non-empty checklist has to justify itself explicitly.
    checklist = raw.get("human_review", {}).get("checklist", [])
    if checklist and not prov.get("notes"):
        raise ProfileError(
            f"profile {raw['profile_id']!r} ships a human-review checklist without "
            f"recording its source in provenance.notes. An ungrounded checklist is a "
            f"fabricated regulatory requirement.")

    return raw


def load_all(root: Path, known_document_ids, spec_lookup, unsupported_document_ids):
    profiles = {}
    if not root.exists():
        return profiles
    for path in sorted(root.glob("*.json")):
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        validate(raw, known_document_ids, spec_lookup, unsupported_document_ids)
        profile = VerificationProfile(raw, path)
        if profile.document_id in profiles:
            raise ProfileError(
                f"more than one profile targets document_id {profile.document_id!r}")
        profiles[profile.document_id] = profile
    return profiles
