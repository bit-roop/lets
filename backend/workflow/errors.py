"""Workflow-specific exceptions."""


class CyclicGraphError(Exception):
    """Raised when admitted dependency edges contain a directed cycle."""

    def __init__(self, cycles):
        self.cycles = cycles
        super().__init__(f"Admitted dependency graph contains cycles: {cycles}")
