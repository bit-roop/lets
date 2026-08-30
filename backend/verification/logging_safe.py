"""Controlled diagnostics.

``logger.exception`` writes the exception message and the full traceback. Both
can carry things this layer must not retain: a PDF parser typically embeds the
absolute file path in its error, and an exception raised while handling
extracted text can contain the text itself. A log line is still a place the data
came to rest.

So no exception message and no traceback text is logged. What is logged is a
sanitised diagnostic: which submission, which stage, the exception *type*, and
the basename and line number of the innermost frame. That is enough to find the
bug and locate the code, and it cannot carry document content, extracted values,
an absolute path, or a secret.

The cost is real -- debugging from a type and a line number is harder than
debugging from a traceback -- and it is accepted deliberately.
"""

import logging
import traceback
from typing import Optional

logger = logging.getLogger("m5-verification")


def log_failure(stage: str, exc: BaseException,
                submission_id: Optional[str] = None,
                application_id: Optional[str] = None) -> str:
    """Record a sanitised diagnostic. Returns the code shown to no-one but ops.

    Nothing derived from the exception's *message* is emitted.
    """
    frame = _innermost_frame(exc)
    logger.error(
        "m5 failure stage=%s exc_type=%s at=%s submission=%s application=%s",
        _safe_token(stage),
        type(exc).__name__,
        frame,
        _safe_token(submission_id),
        _safe_token(application_id),
    )
    return f"{_safe_token(stage)}:{type(exc).__name__}"


def _innermost_frame(exc: BaseException) -> str:
    """'guard.py:118'. A basename, never a path."""
    try:
        frames = traceback.extract_tb(exc.__traceback__)
        if not frames:
            return "unknown"
        last = frames[-1]
        name = last.filename.replace("\\", "/").rsplit("/", 1)[-1]
        return f"{name}:{last.lineno}"
    except Exception:  # noqa: BLE001 - diagnostics must never raise
        return "unknown"


def _safe_token(value: Optional[str]) -> str:
    """Identifiers only: UUIDs, application ids, stage names.

    Anything unexpected is dropped rather than logged, because an id is the only
    thing that belongs in this position.
    """
    if not value:
        return "-"
    text = str(value)
    if len(text) > 80:
        return "<oversized>"
    if not all(ch.isalnum() or ch in "-_.:" for ch in text):
        return "<unloggable>"
    return text
