from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any


def rational(value: Fraction) -> str:
    return str(value)


@dataclass
class Issue:
    severity: str
    code: str
    part: str
    measure: str
    message: str


@dataclass
class Event:
    id: str
    voice: str
    start: Fraction
    duration: Fraction
    kind: str  # note, rest, grace, unpitched
    pitches: list[dict[str, Any]] = field(default_factory=list)
    note_type: str = "quarter"
    dots: int = 0
    tuplet: dict[str, Any] | None = None
    marks: list[dict[str, Any]] = field(default_factory=list)
    beams: list[dict[str, Any]] | None = None
    grace: dict[str, Any] | None = None
    time_modification: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id, "voice": self.voice, "start": rational(self.start),
            "duration": rational(self.duration), "kind": self.kind,
            "pitches": self.pitches, "noteType": self.note_type, "dots": self.dots,
            "tuplet": self.tuplet, "marks": self.marks, "beams": self.beams, "grace": self.grace,
            "timeModification": self.time_modification,
        }


@dataclass
class Measure:
    number: str
    length: Fraction
    beats: str
    beat_type: int
    fifths: int
    mode: str
    events: list[Event] = field(default_factory=list)
    directions: list[dict[str, Any]] = field(default_factory=list)
    barlines: list[dict[str, Any]] = field(default_factory=list)
    implicit: bool = False
    multi_rest: int = 0
    transpose: int = 0
    synthetic: bool = False
    clefs: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "number": self.number, "length": rational(self.length), "beats": self.beats,
            "beatType": self.beat_type, "fifths": self.fifths, "mode": self.mode,
            "implicit": self.implicit, "transpose": self.transpose, "synthetic": self.synthetic,
            "sourceRestCount": self.multi_rest,
            "clefs": self.clefs,
            "events": [e.to_json() for e in self.events],
            "directions": self.directions, "barlines": self.barlines,
        }


@dataclass
class Part:
    id: str
    name: str
    measures: list[Measure]
    source: str
    instrument_family: str = "unknown"
    instrument_profile: dict[str, Any] | None = None
    texture_summary: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "source": self.source, "instrumentFamily": self.instrument_family,
                **({'instrumentProfile': self.instrument_profile} if self.instrument_profile is not None else {}),
                **({'textureSummary': self.texture_summary} if self.texture_summary is not None else {}),
                "measures": [m.to_json() for m in self.measures]}
