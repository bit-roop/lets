"""Native PDF text extraction, page by page.

Slice 1 is native text only.  There is no OCR here and no OCR dependency.  A
page with no text layer is recorded as having no text layer -- it is NOT
recorded as unreadable content, because a later phase may read it with OCR.

The distinction that matters throughout: UNREADABLE is a property of the
document (we looked and nothing usable was there); FAILED is a property of the
system (the extractor raised).  They route differently.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from .. import states


@dataclass
class PageText:
    page: int
    text: str
    char_count: int
    has_text_layer: bool


@dataclass
class ExtractionResult:
    state: str
    pages: List[PageText] = field(default_factory=list)
    error: str = ""

    @property
    def full_text(self) -> str:
        return "\n".join(p.text for p in self.pages)

    @property
    def total_chars(self) -> int:
        return sum(p.char_count for p in self.pages)

    def page_offsets(self) -> Dict[int, int]:
        """Character offset at which each page starts within full_text."""
        offsets, cursor = {}, 0
        for p in self.pages:
            offsets[p.page] = cursor
            cursor += len(p.text) + 1
        return offsets

    def as_dict(self):
        return {
            "state": self.state,
            "page_count": len(self.pages),
            "pages_with_text_layer": sum(1 for p in self.pages if p.has_text_layer),
            "total_chars": self.total_chars,
            "error": self.error,
        }


def extract_pdf_text(path: Path, min_text_chars: int = 40) -> ExtractionResult:
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - dependency is mandatory in slice 1
        return ExtractionResult(state=states.FAILED, error=f"pdfplumber unavailable: {exc}")

    pages: List[PageText] = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                raw = page.extract_text() or ""
                text = raw.strip()
                pages.append(PageText(
                    page=index, text=text, char_count=len(text),
                    has_text_layer=bool(text)))
    except Exception as exc:  # noqa: BLE001 - extractor failure is a system fault
        return ExtractionResult(state=states.FAILED, pages=pages, error=str(exc))

    if not pages:
        return ExtractionResult(state=states.UNREADABLE, pages=pages,
                                error="the document contains no pages")

    with_text = [p for p in pages if p.has_text_layer]
    total = sum(p.char_count for p in pages)

    if not with_text or total < min_text_chars:
        # Looked, found nothing usable.  Not a mismatch -- this routes to review.
        return ExtractionResult(state=states.UNREADABLE, pages=pages)

    if len(with_text) < len(pages):
        return ExtractionResult(state=states.PARTIAL, pages=pages)

    return ExtractionResult(state=states.NATIVE_TEXT, pages=pages)
