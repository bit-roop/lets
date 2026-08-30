"""UTF-8 document catalogue and provenance validation."""

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .models import Coverage, DocumentRequirement, DocumentSpec, SourceRef, VERIFICATION_STATES, ITEM_KINDS, OBLIGATIONS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ROOT = PROJECT_ROOT / "regulatory-documents"


class RegistryError(ValueError):
    pass


def _read(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


class DocumentRegistry:
    def __init__(self, root: Path = DOCUMENT_ROOT):
        self.root = Path(root)
        self.sources_raw = _read(self.root / "sources" / "document_sources.json")
        self.specs_raw = _read(self.root / "specs" / "documents.json")
        self.coverage_raw = _read(self.root / "requirements" / "coverage.json")
        self.requirements_raw: List[Dict[str, Any]] = []
        for name in ("fssai.json", "dish.json", "boiler.json"):
            self.requirements_raw.extend(_read(self.root / "requirements" / name))
        self._validate()

    def _source(self, source_id: str, item: Dict[str, Any]) -> SourceRef:
        raw = self.sources_raw.get(source_id)
        if not raw:
            raise RegistryError(f"Unknown source_id {source_id!r} for {item.get('requirement_id')}")
        status = item.get("verification_status")
        if status not in VERIFICATION_STATES:
            raise RegistryError(f"Invalid verification_status for {item.get('requirement_id')}")
        if not item.get("source_id") or not item.get("last_verified"):
            raise RegistryError(f"Incomplete provenance for {item.get('requirement_id')}")
        if status == "VERIFIED" and not raw.get("source_url"):
            raise RegistryError(f"VERIFIED item has no source URL: {item.get('requirement_id')}")
        return SourceRef(
            source_id=source_id, authority=raw["authority"], title=raw["title"],
            url=raw.get("source_url"), checklist_item=item.get("checklist_item"),
            verification_status=status, last_verified=item["last_verified"],
            currentness=item.get("currentness", raw.get("currentness", "CURRENTNESS_REQUIRES_RECHECK")),
            section=item.get("section", raw.get("section")), notes=item.get("notes", raw.get("note")),
        )

    def _validate(self):
        if not isinstance(self.requirements_raw, list):
            raise RegistryError("requirements files must contain arrays")
        ids = set()
        for spec in self.specs_raw:
            if not spec.get("document_id") or spec.get("item_kind") not in ITEM_KINDS:
                raise RegistryError(f"Invalid document spec {spec}")
        for req in self.requirements_raw:
            rid = req.get("requirement_id")
            if not rid or rid in ids:
                raise RegistryError(f"Duplicate or missing requirement_id: {rid}")
            ids.add(rid)
            if req.get("obligation") not in OBLIGATIONS:
                raise RegistryError(f"Invalid obligation for {rid}")
            if req.get("verification_status") not in VERIFICATION_STATES:
                raise RegistryError(f"Invalid status for {rid}")
            if req.get("verification_status") == "VERIFIED_SCOPE_UNCLEAR" and (
                req.get("obligation") == "MANDATORY" or req.get("blocking", False)
            ):
                raise RegistryError(f"Scope-unclear requirement cannot be mandatory/blocking: {rid}")
            if req.get("verification_status") == "UNSUPPORTED" and (
                req.get("obligation") == "MANDATORY" or req.get("blocking", False)
            ):
                raise RegistryError(f"Unsupported requirement cannot be mandatory/blocking: {rid}")
            if not req.get("source_id") or not req.get("last_verified"):
                raise RegistryError(f"Missing provenance for {rid}")
            if req.get("document_id") not in {s["document_id"] for s in self.specs_raw}:
                raise RegistryError(f"Unknown document_id for {rid}")
            self._source(req["source_id"], req)
        supported = set(self.supported_approval_ids())
        for approval_id, item in self.coverage_raw.items():
            if item.get("status") == "SUPPORTED" and approval_id not in supported:
                raise RegistryError(f"Coverage says supported but no requirements exist: {approval_id}")
            if item.get("status") == "UNSUPPORTED" and approval_id in supported:
                raise RegistryError(f"Coverage says unsupported but requirements exist: {approval_id}")

    def supported_approval_ids(self):
        return sorted({r["approval_id"] for r in self.requirements_raw})

    def specs(self) -> List[DocumentSpec]:
        return [DocumentSpec(**s) for s in self.specs_raw]

    def requirements(self, approval_ids: Optional[Iterable[str]] = None) -> List[DocumentRequirement]:
        selected = set(approval_ids) if approval_ids else None
        out = []
        for r in self.requirements_raw:
            if selected is not None and r["approval_id"] not in selected:
                continue
            out.append(DocumentRequirement(
                requirement_id=r["requirement_id"], approval_id=r["approval_id"],
                document_id=r["document_id"], obligation=r["obligation"],
                condition=r.get("condition"), condition_description=r.get("condition_description"),
                blocking=r.get("blocking", r["obligation"] == "MANDATORY"),
                verification_status=r["verification_status"], source=self._source(r["source_id"], r),
                notes=r.get("notes"),
            ))
        return out

    def coverage(self, approval_ids: Optional[Iterable[str]] = None) -> List[Coverage]:
        selected = set(approval_ids) if approval_ids else None
        out = []
        for aid, raw in sorted(self.coverage_raw.items()):
            if selected is not None and aid not in selected:
                continue
            reqs = [r for r in self.requirements_raw if r["approval_id"] == aid]
            out.append(Coverage(aid, raw["status"], raw["reason"], len(reqs), sorted({r["source_id"] for r in reqs})))
        return out

    def spec(self, document_id: str) -> DocumentSpec:
        for spec in self.specs():
            if spec.document_id == document_id:
                return spec
        raise KeyError(document_id)

    def validate_submission(self, document_id: str, item_kind: Optional[str] = None) -> DocumentSpec:
        """Validate identity and reject unsupported evidence placeholders."""
        try:
            spec = self.spec(document_id)
        except KeyError:
            raise RegistryError(f"Unknown document_id: {document_id!r}")
        if item_kind is not None and item_kind != spec.item_kind:
            raise RegistryError(
                f"item_kind mismatch for {document_id!r}: expected {spec.item_kind}, got {item_kind}")
        statuses = [r["verification_status"] for r in self.requirements_raw if r["document_id"] == document_id]
        if "UNSUPPORTED" in statuses:
            raise RegistryError(f"document_id is unsupported and cannot be submitted: {document_id!r}")
        return spec


_registry: Optional[DocumentRegistry] = None


def get_document_registry() -> DocumentRegistry:
    global _registry
    if _registry is None:
        _registry = DocumentRegistry()
    return _registry
