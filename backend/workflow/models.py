"""
Workflow layer data models.

These are transport structures. They contain no regulatory logic and never
alter a requirement's applicability, which is decided solely by engine-v3.

Durations are expressed in the catalogue's own `sla_days` units. The
catalogue does not state whether these are working or calendar days, so the
scheduler treats them as opaque and performs no calendar conversion.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

DURATION_UNIT = "sla_days"

# SLA classifications
SLA_STANDARD = "STANDARD"            # positive integer
SLA_ZERO_DURATION = "ZERO_DURATION"  # exactly 0 — real node, no elapsed time
SLA_UNSPECIFIED = "UNSPECIFIED"      # null — never invented
SLA_INVALID = "INVALID"              # negative or non-numeric

# Node inclusion
INCLUSION_SCHEDULED = "SCHEDULED"      # APPLICABLE — committed schedule
INCLUSION_PROVISIONAL = "PROVISIONAL"  # UNKNOWN — provisional schedule only
INCLUSION_EXCLUDED = "EXCLUDED"        # CONFLICT — neither schedule


@dataclass
class SlaInfo:
    kind: str
    days: Optional[int]
    raw_value: Any
    source: str = "catalogue.json:sla_days"
    excluded_from_duration: bool = False
    note: Optional[str] = None

    @property
    def duration(self):
        """Arithmetic duration. Unspecified and invalid contribute 0 and are
        flagged, rather than being replaced by a guessed default."""
        if self.kind in (SLA_STANDARD, SLA_ZERO_DURATION):
            return self.days
        return 0

    def as_dict(self):
        return asdict(self)


def classify_sla(raw_value):
    """Classify a catalogue sla_days value. Never substitutes a default."""
    if raw_value is None:
        return SlaInfo(
            kind=SLA_UNSPECIFIED, days=None, raw_value=None,
            excluded_from_duration=True,
            note=("sla_days is not recorded for this requirement. No default "
                  "is substituted; durations that include it are lower bounds."))

    if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
        return SlaInfo(
            kind=SLA_INVALID, days=None, raw_value=raw_value,
            excluded_from_duration=True,
            note=(f"sla_days value {raw_value!r} is not a number. Treated as "
                  "unusable; no default is substituted."))

    if raw_value < 0:
        return SlaInfo(
            kind=SLA_INVALID, days=None, raw_value=raw_value,
            excluded_from_duration=True,
            note=f"sla_days value {raw_value!r} is negative. Treated as unusable.")

    if raw_value == 0:
        return SlaInfo(
            kind=SLA_ZERO_DURATION, days=0, raw_value=raw_value,
            note=("Zero-duration requirement. It occupies a real position in "
                  "the workflow and may gate dependents, but consumes no "
                  "elapsed time."))

    return SlaInfo(kind=SLA_STANDARD, days=int(raw_value), raw_value=raw_value)


@dataclass
class WorkflowNode:
    requirement_id: str
    name: str
    requirement_type: str
    department: Optional[str]
    authority: Optional[str]
    statute: Optional[str]
    state: str                  # engine-assigned; never mutated here
    confidence: str             # engine-assigned; carried through
    sla: SlaInfo
    inclusion: str
    inclusion_reason: str
    missing_facts: list = field(default_factory=list)
    missing_fact_origin: dict = field(default_factory=dict)
    quantity: Optional[dict] = None
    # Forward hook for the document milestone. Populated by a later layer;
    # the scheduler never reads or writes it.
    document_slots: list = field(default_factory=list)

    def as_dict(self):
        d = asdict(self)
        d["sla"] = self.sla.as_dict()
        return d


@dataclass
class WorkflowEdge:
    from_id: str                # prerequisite
    to_id: str                  # dependent
    dependency_type: str
    verification_status: str
    basis: Optional[str]
    admitted: bool
    admission_reason: str
    origin: str
    dropped: bool = False
    dropped_reason: Optional[str] = None

    def key(self):
        return (self.from_id, self.to_id, self.dependency_type, self.origin)

    def as_dict(self):
        return asdict(self)


@dataclass
class ScheduledNode:
    requirement_id: str
    earliest_start_day: int
    earliest_finish_day: int
    latest_start_day: Optional[int]
    latest_finish_day: Optional[int]
    slack_days: Optional[int]
    on_critical_path: bool
    depth: int
    duration_days: int
    duration_is_lower_bound: bool
    blocks: list = field(default_factory=list)
    blocks_transitively: list = field(default_factory=list)
    blocked_by: list = field(default_factory=list)

    def as_dict(self):
        return asdict(self)


@dataclass
class Schedule:
    label: str                  # "COMMITTED" or "PROVISIONAL"
    scope_note: str
    topological_order: list
    parallel_bands: list
    nodes: dict
    sequential_duration_days: int
    parallel_duration_days: int
    critical_paths: list
    critical_path_duration_days: int
    duration_completeness: str  # COMPLETE | PARTIAL
    excluded_from_duration: list
    schedule_confidence: str
    confidence_basis: str
    duration_unit: str = DURATION_UNIT

    def as_dict(self):
        d = asdict(self)
        d["nodes"] = {k: v.as_dict() for k, v in self.nodes.items()}
        return d


@dataclass
class WorkflowResult:
    workflow_version: str
    generated_for: dict
    nodes: dict
    edges: list
    schedule: Optional[Schedule]
    provisional_schedule: Optional[Schedule]
    provisional_delta: Optional[dict]
    cycles: list
    graph_diagnostics: dict
    warnings: list

    def as_dict(self):
        return {
            "workflow_version": self.workflow_version,
            "generated_for": self.generated_for,
            "nodes": {k: v.as_dict() for k, v in self.nodes.items()},
            "edges": [e.as_dict() for e in self.edges],
            "schedule": self.schedule.as_dict() if self.schedule else None,
            "provisional_schedule": (self.provisional_schedule.as_dict()
                                     if self.provisional_schedule else None),
            "provisional_delta": self.provisional_delta,
            "cycles": self.cycles,
            "graph_diagnostics": self.graph_diagnostics,
            "warnings": self.warnings,
        }


def warning(type_, severity, message, **extra):
    w = {"type": type_, "severity": severity, "message": message}
    w.update(extra)
    return w
