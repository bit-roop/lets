"""PDF structural inventory.  Structure only -- no text extraction here."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class PdfInventory:
    page_count: int
    signature_objects_present: bool
    producer: Optional[str] = None
    creator: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    def as_dict(self):
        return {
            "page_count": self.page_count,
            "signature_objects_present": self.signature_objects_present,
            "producer": self.producer,
            "creator": self.creator,
            "notes": self.notes,
        }


class PdfStructureError(Exception):
    """The file claims to be a PDF but its structure could not be read."""


def inventory(path: Path) -> PdfInventory:
    from pypdf import PdfReader

    try:
        reader = PdfReader(str(path))
        page_count = len(reader.pages)
    except Exception as exc:  # noqa: BLE001 - any parser failure is one condition
        raise PdfStructureError(str(exc)) from exc

    meta = reader.metadata or {}

    # Presence of a signature object is NOT evidence of authenticity.  It is
    # recorded so a later phase can validate it; slice 1 validates nothing.
    signature_present = False
    try:
        fields = reader.get_fields() or {}
        signature_present = any(
            str(v.get("/FT")) == "/Sig" for v in fields.values() if hasattr(v, "get"))
    except Exception:  # noqa: BLE001
        signature_present = False

    return PdfInventory(
        page_count=page_count,
        signature_objects_present=signature_present,
        producer=_meta_str(meta, "/Producer"),
        creator=_meta_str(meta, "/Creator"),
    )


def _meta_str(meta, key) -> Optional[str]:
    try:
        value = meta.get(key)
    except Exception:  # noqa: BLE001
        return None
    return str(value) if value is not None else None
