"""Generate synthetic PDF fixtures for the M5 test suite.

EVERY VALUE IN THESE FILES IS INVENTED FOR TESTING.

The repository contains no applicant documents and no authoritative field
schema for any evidence item. These fixtures are NOT specimens of real
government forms, and nothing in them may be treated as evidence about what a
real Form No. 1 or Form B looks like. They exist only to exercise the pipeline.

Written with a minimal hand-rolled PDF writer so the test suite needs no
additional dependency beyond the two already required by slice 1.
"""

from pathlib import Path
from typing import List

FIXTURE_DIR = Path(__file__).resolve().parent
BANNER = "SYNTHETIC TEST FIXTURE - NOT A REAL DOCUMENT"


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def write_pdf(path: Path, pages: List[List[str]]) -> Path:
    """Minimal multi-page PDF with a Helvetica text layer."""
    objects, page_ids = [], []
    page_object_start = 3 + len(pages)  # 1 catalog, 2 pages tree, 3.. fonts/content

    content_ids = []
    for index, lines in enumerate(pages):
        stream_lines = ["BT", "/F1 11 Tf", "72 760 Td", "14 TL"]
        for line in lines:
            stream_lines.append(f"({_escape(line)}) Tj")
            stream_lines.append("T*")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines)
        content_ids.append(page_object_start + index)

    font_id = page_object_start + len(pages)

    for index, lines in enumerate(pages):
        page_ids.append(3 + index)

    body = {}
    body[1] = "<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    body[2] = (f"<< /Type /Pages /Count {len(pages)} /Kids [{kids}] >>")

    for index, pid in enumerate(page_ids):
        body[pid] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
            f"/Contents {content_ids[index]} 0 R >>")

    for index, lines in enumerate(pages):
        stream_lines = ["BT", "/F1 11 Tf", "72 760 Td", "14 TL"]
        for line in lines:
            stream_lines.append(f"({_escape(line)}) Tj")
            stream_lines.append("T*")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines)
        body[content_ids[index]] = (
            f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")

    body[font_id] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for obj_id in sorted(body):
        offsets[obj_id] = len(out)
        out += f"{obj_id} 0 obj\n{body[obj_id]}\nendobj\n".encode("latin-1")

    xref_offset = len(out)
    max_id = max(body)
    out += f"xref\n0 {max_id + 1}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for obj_id in range(1, max_id + 1):
        out += f"{offsets.get(obj_id, 0):010d} 00000 n \n".encode("latin-1")
    out += (f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n").encode("latin-1")

    path.write_bytes(bytes(out))
    return path


def build_all(directory: Path = FIXTURE_DIR) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    built = {}

    built["form1"] = write_pdf(directory / "synthetic_form_1.pdf", [[
        BANNER,
        "Directorate of Industrial Safety and Health",
        "Factory Form No. 1",
        "Application for registration and grant of licence",
        "Under the Factories Act",
        "Name of the Occupier: Aarav Deshmukh",
        "Maximum number of workers: 67",
        "Date: 12/05/2026",
    ]])

    # Deliberately misnamed on disk: the classifier must still match on content.
    built["form1_misnamed"] = write_pdf(directory / "linux_assignment.pdf", [[
        BANNER,
        "Directorate of Industrial Safety and Health",
        "Factory Form No. 1",
        "Under the Factories Act",
        "Name of the Occupier: Aarav Deshmukh",
        "Date: 12/05/2026",
    ]])

    built["formb"] = write_pdf(directory / "synthetic_form_b.pdf", [[
        BANNER,
        "FSSAI",
        "FSSAI Form B",
        "Application for State Licence under the FSS Act",
        "Submitted through FoSCoS",
        "Name of the Company: Example Foods Private Limited",
        "Date: 03/04/2026",
    ]])

    # Correctly named on disk, wrong content: must still fail.
    built["formb_named_form1"] = write_pdf(directory / "factory_form_no_1.pdf", [[
        BANNER,
        "FSSAI",
        "FSSAI Form B",
        "Application for State Licence under the FSS Act",
        "Date: 03/04/2026",
    ]])

    built["unrelated"] = write_pdf(directory / "synthetic_unrelated.pdf", [[
        BANNER,
        "Introduction to operating system scheduling",
        "This document discusses process scheduling algorithms",
        "and has nothing to do with regulatory evidence.",
        "Round robin, shortest job first, and priority scheduling.",
    ]])

    built["blank"] = write_pdf(directory / "synthetic_blank.pdf", [[]])

    built["future_date"] = write_pdf(directory / "synthetic_form_1_future.pdf", [[
        BANNER,
        "Directorate of Industrial Safety and Health",
        "Factory Form No. 1",
        "Under the Factories Act",
        "Name of the Occupier: Aarav Deshmukh",
        "Maximum number of workers: 67",
        "Date: 01/01/2099",
    ]])

    js = directory / "synthetic_active_content.pdf"
    write_pdf(js, [[BANNER, "Factory Form No. 1", "Under the Factories Act"]])
    js.write_bytes(js.read_bytes().replace(
        b"%%EOF\n", b"/JavaScript (app.alert\\(1\\))\n%%EOF\n"))
    built["active_content"] = js

    encrypted = directory / "synthetic_encrypted.pdf"
    write_pdf(encrypted, [[BANNER, "Factory Form No. 1"]])
    encrypted.write_bytes(encrypted.read_bytes().replace(
        b"trailer\n<< /Size", b"trailer\n<< /Encrypt 99 0 R /Size"))
    built["encrypted"] = encrypted

    built["not_a_pdf"] = directory / "synthetic_not_a_pdf.pdf"
    built["not_a_pdf"].write_bytes(b"this is plain text pretending to be a pdf\n")

    return built


if __name__ == "__main__":
    for name, path in build_all().items():
        print(f"{name:22s} {path}")
