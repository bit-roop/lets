"""What may leave the pipeline, and in what form.

The pipeline reads real values out of an applicant's document. Those values are
needed to run checks, but almost none of them need to be *kept*. So raw text
never reaches the record store or an API response: each field is reduced to a
safe display form first, chosen by the sensitivity its profile declares.

The reduction happens once, at the boundary between analysis and persistence.
Everything upstream of that boundary works with the real value in memory;
everything downstream sees only what is declared safe.
"""

from typing import Any, Optional

#: Ordinary document metadata: a form number, an issuing authority, a title.
#: Not personal information, and useful to keep verbatim.
NON_SENSITIVE = "NON_SENSITIVE"

#: A person's or organisation's name. Kept only as initials, so a reviewer can
#: see that a name was found and roughly which one, without the record holding
#: the name itself.
PERSONAL_NAME = "PERSONAL_NAME"

#: A licence, registration, PAN, Aadhaar or similar number. Kept as a trailing
#: fragment only. Never stored in full.
IDENTIFIER = "IDENTIFIER"

#: A count, capacity or load. Needed for numeric cross-checks and not personal.
QUANTITY = "QUANTITY"

#: A date. Needed for temporal checks and not personal on its own.
DATE = "DATE"

SENSITIVITIES = frozenset({NON_SENSITIVE, PERSONAL_NAME, IDENTIFIER, QUANTITY, DATE})

#: Sensitivities whose values are reduced before they are stored or returned.
REDACTED_SENSITIVITIES = frozenset({PERSONAL_NAME, IDENTIFIER})

#: How many trailing characters of an identifier are retained.
IDENTIFIER_TAIL = 4


def mask_name(value: str) -> str:
    """'Aarav Deshmukh' -> 'A**** D*******'.

    Enough to confirm a name was read and to compare against another masked
    name, not enough to reconstruct it.
    """
    parts = [p for p in str(value).split() if p]
    if not parts:
        return "***"
    return " ".join(p[0] + ("*" * (len(p) - 1)) if len(p) > 1 else p for p in parts)


def mask_identifier(value: str) -> str:
    """'ABCDE1234F' -> '******234F'. Aadhaar and PAN never persist in full."""
    text = "".join(str(value).split())
    if len(text) <= IDENTIFIER_TAIL:
        return "*" * len(text)
    return "*" * (len(text) - IDENTIFIER_TAIL) + text[-IDENTIFIER_TAIL:]


def safe_display(value: Any, sensitivity: str) -> Optional[str]:
    """The only representation of an extracted value allowed to be stored."""
    if value is None:
        return None
    if sensitivity == PERSONAL_NAME:
        return mask_name(value)
    if sensitivity == IDENTIFIER:
        return mask_identifier(value)
    return str(value)


def is_redacted(sensitivity: str) -> bool:
    return sensitivity in REDACTED_SENSITIVITIES
