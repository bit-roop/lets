"""Media guard: everything here runs BEFORE the document is parsed.

Design rule for slice 1: where a check cannot be made reliably with the
available dependencies, this module records uncertainty instead of claiming a
detection.  A scanner that reports "no malicious content" when it merely failed
to look is worse than one that says it did not look.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

MAX_UPLOAD_BYTES = 10 * 1024 * 1024        # matches M4's own ceiling
MAX_PAGES = 50

#: Controls actually enforced here: byte-signature vs declared MIME, the size
#: ceiling, the accepted-format list, encryption rejection, and active-content
#: rejection. Page count is enforced by the caller, which knows the profile's
#: limit. A decompression-ratio control is deliberately NOT declared: it is not
#: implemented, and naming an unenforced control would misrepresent what this
#: guard does.

#: Leading byte signatures.  A literal table avoids a libmagic dependency.
MAGIC = {
    "application/pdf": [b"%PDF-"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
}

#: PDF constructs that make a document active rather than inert.
ACTIVE_CONTENT_MARKERS = [
    (b"/JavaScript", "embedded JavaScript"),
    (b"/JS", "embedded JavaScript"),
    (b"/Launch", "a launch action"),
    (b"/EmbeddedFile", "an embedded file"),
    (b"/OpenAction", "an automatic open action"),
]


@dataclass
class GuardResult:
    accepted: bool
    reasons: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    detected_mime: Optional[str] = None
    size_bytes: Optional[int] = None

    def as_dict(self):
        return {
            "accepted": self.accepted, "reasons": self.reasons, "notes": self.notes,
            "detected_mime": self.detected_mime, "size_bytes": self.size_bytes,
        }


def resolve_storage_path(storage_key: str, root: Path) -> Path:
    """Resolve an M4 storage_key under M4's quarantine root.

    No path component is ever taken from a filename, an extracted value, or a
    classification label.  The resolved path must stay inside the root.
    """
    if not storage_key:
        raise ValueError("submission has no storage_key")
    root = Path(root).resolve()
    candidate = (root / storage_key).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("resolved storage path escapes the submission root")
    if not candidate.is_file():
        raise FileNotFoundError("stored submission file is not present")
    return candidate


def sniff(head: bytes) -> Optional[str]:
    for mime, signatures in MAGIC.items():
        for sig in signatures:
            if head.startswith(sig):
                return mime
    return None


def check(path: Path, declared_mime: Optional[str], accepted_formats) -> GuardResult:
    result = GuardResult(accepted=True)
    size = path.stat().st_size
    result.size_bytes = size

    if size == 0:
        result.accepted = False
        result.reasons.append("The uploaded file is empty.")
        return result

    if size > MAX_UPLOAD_BYTES:
        result.accepted = False
        result.reasons.append(
            f"The file is larger than the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.")
        return result

    with path.open("rb") as fh:
        head = fh.read(1024)

    detected = sniff(head)
    result.detected_mime = detected

    if detected is None:
        result.accepted = False
        result.reasons.append(
            "The file type could not be recognised from its contents.")
        return result

    if declared_mime and detected != declared_mime:
        result.accepted = False
        result.reasons.append(
            f"The file contents are {detected}, but it was submitted as {declared_mime}.")
        return result

    if accepted_formats and detected not in accepted_formats:
        result.accepted = False
        result.reasons.append(
            f"This evidence item does not accept {detected} files.")
        return result

    if detected == "application/pdf":
        _check_pdf(path, result)

    return result


def _check_pdf(path: Path, result: GuardResult) -> None:
    raw = path.read_bytes()

    if b"/Encrypt" in raw:
        result.accepted = False
        result.reasons.append(
            "The PDF is encrypted or password-protected and cannot be examined.")
        return

    found = sorted({label for marker, label in ACTIVE_CONTENT_MARKERS if marker in raw})
    if found:
        result.accepted = False
        result.reasons.append(
            "The PDF contains active content (" + ", ".join(found) +
            ") and was not examined.")
        return

    # Save-generation count is a signal, never a verdict.  Legitimate documents
    # are re-saved all the time; this is recorded for a human, not acted on.
    generations = raw.count(b"%%EOF")
    if generations > 1:
        result.notes.append(
            f"The file contains {generations} save generations. This is common in "
            f"ordinary documents and is recorded for information only.")
