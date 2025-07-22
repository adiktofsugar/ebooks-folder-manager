"""Type definitions for scripts."""

from typing import TypedDict, Literal


class Position(TypedDict):
    """Position in a file."""
    line: int
    character: int


class Range(TypedDict):
    """Range in a file."""
    start: Position
    end: Position


class Diagnostic(TypedDict):
    """A diagnostic message from pyright."""
    file: str
    severity: Literal["error", "warning", "information"]
    message: str
    range: Range
    rule: str


class PyrightOutput(TypedDict):
    """Output from pyright --outputjson."""
    version: str
    time: str
    generalDiagnostics: list[Diagnostic]