"""Basic single-voice notation rules, independent of OMR output quality."""
from dataclasses import dataclass
from fractions import Fraction


LETTERS = "CDEFGAB"


@dataclass(frozen=True)
class Clef:
    sign: str
    line: int
    octave_change: int = 0


def staff_pitch(position: int, clef: Clef) -> tuple[str, int]:
    """Bottom line=0, first space=1, next line=2; ledger positions allowed.

    This decodes diatonic position only. Key signatures and accidentals are a
    separate pass, and instrument transposition is not inferred here.
    """
    anchors = {"G": ("G", 4), "F": ("F", 3), "C": ("C", 4)}
    if clef.sign not in anchors or not 1 <= clef.line <= 5:
        raise ValueError("Only pitched G/F/C clefs on lines 1-5 are supported")
    letter, octave = anchors[clef.sign]
    absolute = 7 * (octave + clef.octave_change) + LETTERS.index(letter)
    absolute += position - 2 * (clef.line - 1)
    output_octave, index = divmod(absolute, 7)
    return LETTERS[index], output_octave


def bar_quarters(beats: int, beat_type: int) -> Fraction:
    if beats <= 0 or beat_type not in (1, 2, 4, 8, 16, 32, 64):
        raise ValueError("Invalid simple time signature")
    return Fraction(beats * 4, beat_type)


def plain_rhythm(note_type: str, dots: int = 0) -> dict:
    """Jianpu digit=quarter note, independent of the time-signature denominator.

    Returns exact quarter duration and basic visual components. No tuplets or
    ties are folded into this rule, and augmentation dashes are not new notes.
    """
    values = {"whole": Fraction(4), "half": Fraction(2), "quarter": Fraction(1),
              "eighth": Fraction(1,2), "16th": Fraction(1,4),
              "32nd": Fraction(1,8), "64th": Fraction(1,16)}
    if note_type not in values or dots not in (0,1,2):
        raise ValueError("Unsupported basic note type or dot count")
    value = values[note_type] * sum((Fraction(1,2**d) for d in range(dots+1)), Fraction(0))
    underlines = {"eighth":1,"16th":2,"32nd":3,"64th":4}.get(note_type,0)
    # Integer quarter lengths use extension dashes. Noninteger halves (e.g.
    # double-dotted half) require a tie/split, and are flagged for a later step.
    split_required = value >= 2 and value.denominator != 1
    return {"quarterDuration":str(value), "underlines":underlines,
            "extensionDashes":int(value)-1 if value >= 2 and not split_required else 0,
            "augmentationDots":dots if value < 2 else 0,
            "splitRequired":split_required}
