"""Profile loader.

A verification profile says how to inspect evidence M4 already requires. These
tests hold the line that it cannot become a back door for declaring regulatory
requirements, and that nothing ungrounded is ever allowed to block an applicant.
"""

import copy
import json
import unittest
from pathlib import Path

from backend.verification import m4_gateway, states
from backend.verification.profiles import loader
from backend.verification.profiles.registry import get_profile_registry

PROFILE_DIR = loader.PROFILE_ROOT


def _known_ids():
    return set(m4_gateway.document_ids())


def _unsupported_ids():
    return {r.document_id for r in m4_gateway.all_requirements()
            if r.verification_status == "UNSUPPORTED"}


def _validate(raw):
    return loader.validate(raw, _known_ids(), m4_gateway.spec, _unsupported_ids())


def _valid_profile():
    with (PROFILE_DIR / "S02-FORM-1.v1.json").open(encoding="utf-8") as fh:
        return json.load(fh)


class TestShippedProfiles(unittest.TestCase):

    def test_both_slice1_profiles_load(self):
        registry = get_profile_registry()
        self.assertEqual(registry.profiled_document_ids(),
                         ["F02-FORM-B", "S02-FORM-1"])

    def test_every_profile_targets_a_real_upload_document(self):
        for profile in get_profile_registry().all():
            self.assertIn(profile.document_id, _known_ids())
            self.assertEqual(m4_gateway.spec(profile.document_id).item_kind,
                             "UPLOAD_DOCUMENT")

    def test_profiles_carry_provenance_and_limitations(self):
        for profile in get_profile_registry().all():
            self.assertTrue(profile.provenance.get("basis"))
            self.assertTrue(profile.provenance.get("limitations"),
                            f"{profile.profile_id} states no limitations; the "
                            f"repository grounds no field schema, so there are some")

    def test_every_anchor_records_its_basis(self):
        for profile in get_profile_registry().all():
            for anchor in profile.anchors_required + profile.anchors_forbidden:
                self.assertTrue(
                    anchor.get("basis"),
                    f"anchor {anchor.get('text')!r} in {profile.profile_id} has no basis")

    def test_no_profile_declares_authenticity_it_cannot_establish(self):
        for profile in get_profile_registry().all():
            self.assertIn(profile.authenticity["capability"],
                          states.DECLARABLE_AUTHENTICITY)

    def test_shipped_checklists_are_empty(self):
        """The repository contains no checklist content, so shipping one would
        be inventing a regulatory requirement."""
        for profile in get_profile_registry().all():
            self.assertEqual(profile.human_review.get("checklist", []), [])


class TestProfileCannotCreateRequirements(unittest.TestCase):
    """Test 7: a profile cannot define, restate or scope a requirement."""

    def test_unknown_document_id_is_rejected(self):
        raw = _valid_profile()
        raw["document_id"] = "FAKE-DOC-99"
        with self.assertRaises(loader.ProfileError) as ctx:
            _validate(raw)
        self.assertIn("unknown document_id", str(ctx.exception))

    def test_every_forbidden_key_is_rejected(self):
        samples = {
            "obligation": "MANDATORY",
            "approval_id": "S-02",
            "requirement_id": "S02-REQ-999",
            "blocking": True,
            "condition": {"fact": "x", "op": "==", "value": True},
            "condition_description": "invented",
            "applicability": "APPLICABLE",
            "verification_status": "VERIFIED",
            "coverage": "SUPPORTED",
            "readiness": "READY",
            "sla_days": 30,
            "depends_on": ["S-01"],
            "item_kind": "UPLOAD_DOCUMENT",
            "accepted_formats": ["application/pdf"],
        }
        self.assertEqual(set(samples), set(loader.FORBIDDEN_TOP_LEVEL),
                         "the forbidden-key list and this test have drifted apart")
        for key, value in samples.items():
            raw = _valid_profile()
            raw[key] = value
            with self.assertRaises(loader.ProfileError, msg=key) as ctx:
                _validate(raw)
            self.assertIn(key, str(ctx.exception))

    def test_unrecognised_keys_are_rejected(self):
        raw = _valid_profile()
        raw["new_regulatory_rule"] = "anything"
        with self.assertRaises(loader.ProfileError):
            _validate(raw)

    def test_loading_profiles_does_not_change_the_m4_registry(self):
        before = [(r.requirement_id, r.document_id, r.obligation)
                  for r in m4_gateway.all_requirements()]
        get_profile_registry()
        after = [(r.requirement_id, r.document_id, r.obligation)
                 for r in m4_gateway.all_requirements()]
        self.assertEqual(before, after)

    def test_profile_cannot_target_an_unsupported_requirement(self):
        unsupported = _unsupported_ids()
        if not unsupported:
            self.skipTest("no UNSUPPORTED requirements in the registry")
        raw = _valid_profile()
        raw["document_id"] = sorted(unsupported)[0]
        with self.assertRaises(loader.ProfileError):
            _validate(raw)


class TestGroundingDiscipline(unittest.TestCase):

    def test_blocking_check_cannot_cite_a_research_required_field(self):
        raw = _valid_profile()
        for field in raw["fields"]:
            if field["field_id"] == "document_date":
                field["field_source"] = states.RESEARCH_REQUIRED
        raw["checks"].append({
            "check_id": "INVENTED", "kind": "date_not_future",
            "inputs": ["document_date"], "severity": "BLOCKING",
            "message": "x",
        })
        with self.assertRaises(loader.ProfileError) as ctx:
            _validate(raw)
        self.assertIn("RESEARCH_REQUIRED", str(ctx.exception))

    def test_shipped_blocking_checks_only_cite_grounded_inputs(self):
        for profile in get_profile_registry().all():
            grounded = set(profile.grounded_field_ids()) | {"__identity__"}
            for check in profile.checks:
                if check["severity"] == states.BLOCKING:
                    for cited in check["inputs"]:
                        self.assertIn(cited, grounded, check["check_id"])

    def test_field_without_basis_is_rejected(self):
        raw = _valid_profile()
        raw["fields"][0].pop("basis")
        with self.assertRaises(loader.ProfileError):
            _validate(raw)

    def test_missing_provenance_is_rejected(self):
        raw = _valid_profile()
        raw["provenance"].pop("basis")
        with self.assertRaises(loader.ProfileError):
            _validate(raw)


if __name__ == "__main__":
    unittest.main()
