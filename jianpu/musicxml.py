"""Preserve XML timing and notation instead of round-tripping through MIDI.

music21 is used for independent import diagnostics by the pipeline; this adapter
retains raw MusicXML semantics and exact rational time for the renderer.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

from .model import Event, Issue, Measure, Part

MAX_XML = 64 * 1024 * 1024
STEP_ORDER = "CDEFGAB"
SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
KEYS = {
    -7: ("C", -1), -6: ("G", -1), -5: ("D", -1), -4: ("A", -1),
    -3: ("E", -1), -2: ("B", -1), -1: ("F", 0), 0: ("C", 0),
    1: ("G", 0), 2: ("D", 0), 3: ("A", 0), 4: ("E", 0),
    5: ("B", 0), 6: ("F", 1), 7: ("C", 1),
}
MAJOR = [0, 2, 4, 5, 7, 9, 11]


def read_xml(path: Path) -> ET.Element:
    if path.suffix.lower() == ".mxl":
        with zipfile.ZipFile(path) as archive:
            container_data = archive.read("META-INF/container.xml")
            if len(container_data) > 1024 * 1024:
                raise ValueError("MusicXML container is too large")
            container = ET.fromstring(container_data)
            files = [x.attrib["full-path"] for x in container.iter()
                     if x.tag.rsplit("}", 1)[-1] == "rootfile"
                     and x.attrib.get("media-type") == "application/vnd.recordare.musicxml+xml"]
            if len(files) != 1:
                raise ValueError("Expected exactly one score rootfile in MXL")
            if archive.getinfo(files[0]).file_size > MAX_XML:
                raise ValueError("MusicXML exceeds size limit")
            data = archive.read(files[0])
    else:
        if path.stat().st_size > MAX_XML:
            raise ValueError("MusicXML exceeds size limit")
        data = path.read_bytes()
    if b"<!ENTITY" in data.upper():
        raise ValueError("XML entity declarations are not accepted")
    root = ET.fromstring(data)
    for node in root.iter():
        node.tag = node.tag.rsplit("}", 1)[-1]
    if root.tag != "score-partwise":
        raise ValueError(f"Unsupported MusicXML root: {root.tag}; expected score-partwise")
    return root


def degree_pitch(step: str, octave: int, alter: Fraction, fifths: int) -> dict:
    """Relative-major degrees: a minor key is written using la-based degrees.

    Octave dots use the major tonic in octave 4 as zero, with floor division
    across the B/C boundary. Preserve diatonic spelling, not only MIDI pitch.
    """
    if fifths not in KEYS or step not in SEMITONES:
        raise ValueError(f"Unsupported key or step: {fifths}, {step}")
    tonic, tonic_alter = KEYS[fifths]
    distance = 7 * (octave - 4) + STEP_ORDER.index(step) - STEP_ORDER.index(tonic)
    octaves, degree = divmod(distance, 7)
    actual = 12 * (octave - 4) + SEMITONES[step] + alter
    expected = SEMITONES[tonic] + tonic_alter + 12 * octaves + MAJOR[degree]
    accidental = actual - expected
    return {"step": step, "octave": octave, "alter": str(alter),
            "degree": degree + 1, "octaveDots": octaves,
            "accidental": str(accidental)}


def key_label(fifths: int, mode: str) -> str:
    step, alter = KEYS[fifths]
    suffix = "b" if alter < 0 else "#" if alter > 0 else ""
    if mode == "minor":
        ix = STEP_ORDER.index(step) + 5
        minor_step = STEP_ORDER[ix % 7]
        minor_alter = (SEMITONES[step] + alter + 9 - SEMITONES[minor_step]) % 12
        if minor_alter > 6:
            minor_alter -= 12
        return "6=" + minor_step + ("b" if minor_alter == -1 else "#" if minor_alter == 1 else "")
    return "1=" + step + suffix


def text(node: ET.Element, name: str, default: str = "") -> str:
    return node.findtext(name, default=default) or default


def notation_marks(note: ET.Element, part_id: str, measure: str, issues: list[Issue]) -> list[dict]:
    result = []
    for notation in note.findall("notations/*"):
        tag = notation.tag
        if tag in ("tied", "slur", "tuplet", "arpeggiate", "fermata"):
            result.append({"kind": tag, "type": notation.get("type", ""),
                           "number": notation.get("number", "1"),
                           "placement": notation.get("placement", "below" if notation.get("orientation") == "under" else "above"),
                           "direction": notation.get("direction", ""),
                           "lineType": notation.get("line-type", "solid"),
                           "hidden": notation.get("print-object") == "no",
                           "sourceAttributes": dict(notation.attrib), "sourceXml": ET.tostring(notation, encoding="unicode"),
                           "sourceGeometry": {k: v for k, v in notation.attrib.items()
                                              if k.startswith(("bezier-", "default-", "relative-"))}})
            if tag == "tuplet":
                result[-1].update({"lineShape":notation.get("line-shape", "curved"),
                                   "bracket":notation.get("bracket", "yes"),
                                   "showNumber":notation.get("show-number", "actual")})
                for child, key in (("tuplet-actual", "tupletActual"), ("tuplet-normal", "tupletNormal")):
                    value = text(notation, child + "/tuplet-number")
                    if value.isdigit(): result[-1][key] = int(value)
        elif tag in ("articulations", "ornaments", "technical"):
            supported = {"staccato", "tenuto", "accent", "strong-accent", "trill-mark", "tremolo",
                         "mordent", "inverted-mordent", "breath-mark", "up-bow", "down-bow", "double-tongue", "triple-tongue",
                         "fingering", "pluck", "other-technical", "harmonic", "snap-pizzicato", "left-hand-pizzicato",
                         "damp", "damp-all"}
            for mark in notation:
                label = (mark.text or "").strip()
                if tag == "ornaments" and mark.tag == "accidental-mark":
                    for previous in reversed(result):
                        if previous["kind"] == "trill-mark":
                            previous["ornamentAccidental"] = label
                            break
                    continue
                item = {"kind": mark.tag, "label": label, "type": mark.get("type", ""),
                               "number": mark.get("number", "1"), "smufl": mark.get("smufl", ""),
                               "placement": mark.get("placement", "above"),
                               "hidden": mark.get("print-object") == "no",
                               "sourceAttributes": dict(mark.attrib), "sourceXml": ET.tostring(mark, encoding="unicode")}
                if mark.tag == "tremolo" and label.isdigit():
                    item["tremoloStrokes"] = int(label)
                if mark.tag == "harmonic":
                    item["harmonic"] = {
                        "kind": next((k for k in ("natural", "artificial") if mark.find(k) is not None), "unspecified"),
                        "pitchRole": next((k for k in ("base-pitch", "touching-pitch", "sounding-pitch") if mark.find(k) is not None), "unspecified")}
                    if item["harmonic"]["kind"] == "artificial" or item["harmonic"]["pitchRole"] in ("base-pitch", "touching-pitch"):
                        issues.append(Issue("warning", "harmonic_pitch_review", part_id, measure,
                                            "Harmonic written/touching/sounding pitch roles retained; manual review required"))
                result.append(item)
                if mark.tag not in supported:
                    issues.append(Issue("warning", "notation_fallback", part_id, measure,
                                        f"{mark.tag} retained; renderer uses textual fallback"))
        elif tag not in ("accidental-mark",):
            result.append({"kind": tag, "label": (notation.text or tag).strip(),
                           "sourceAttributes": dict(notation.attrib), "sourceXml": ET.tostring(notation, encoding="unicode")})
            issues.append(Issue("warning", "notation_fallback", part_id, measure,
                                f"{tag} retained; renderer uses textual fallback"))
    # Some files provide only sounding ties, without a corresponding tied mark.
    for tie in note.findall("tie"):
        if not any(m["kind"] == "tied" and m.get("type") == tie.get("type") for m in result):
            result.append({"kind": "tied", "type": tie.get("type", ""), "number": "1"})
    # Chord members share an event; a tie must still connect the same written pitch.
    if note.find("pitch") is not None:
        pitch_key = (text(note, "pitch/step") + text(note, "pitch/octave") + ":"
                     + str(Fraction(text(note, "pitch/alter", "0"))))
        for mark in result:
            if mark["kind"] == "tied":
                mark["pitchKey"] = pitch_key
    return result


def parse_part(path: Path, part_id: str, name: str, issues: list[Issue], xml_part: str | None = None) -> Part:
    root = read_xml(path)
    nodes = root.findall("part")
    if xml_part:
        nodes = [p for p in nodes if p.get("id") == xml_part]
    if len(nodes) != 1:
        raise ValueError(f"{path.name}: found {len(nodes)} parts; configure musicxmlPart explicitly")
    source_beaming = bool(nodes[0].findall('.//beam'))
    divisions = 1
    fifths, mode, beats, beat_type, transpose = 0, "major", "4", 4, 0
    clefs = {}
    measures = []
    event_ix = 0
    for mx in nodes[0].findall("measure"):
        number = mx.get("number", str(len(measures) + 1))
        if not re.fullmatch(r"\d+", number):
            issues.append(Issue("error", "measure_number", part_id, number,
                                "Non-numeric bar numbering requires manual alignment"))
        cursor = Fraction(0)
        last_event: dict[str, Event] = {}
        measure = Measure(number, Fraction(sum(int(b) for b in beats.split("+")) * 4, beat_type),
                          beats, beat_type, fifths, mode, implicit=mx.get("implicit") == "yes")
        measure.clefs = deepcopy(clefs)
        for node in mx:
            if node.tag == "attributes":
                divisions = int(text(node, "divisions", str(divisions)))
                if divisions <= 0:
                    raise ValueError("MusicXML divisions must be positive")
                fifths = int(text(node, "key/fifths", str(fifths)))
                mode = text(node, "key/mode", mode)
                beats = text(node, "time/beats", beats)
                beat_type = int(text(node, "time/beat-type", str(beat_type)))
                transpose = int(text(node, "transpose/chromatic", str(transpose)))
                for clef in node.findall("clef"):
                    staff = clef.get("number", "1")
                    clefs[staff] = {"sign": text(clef, "sign"),
                                    "line": int(text(clef, "line", "0")),
                                    "octaveChange": int(text(clef, "clef-octave-change", "0"))}
                measure.clefs = deepcopy(clefs)
                measure.length = Fraction(sum(int(b) for b in beats.split("+")) * 4, beat_type)
                measure.beats, measure.beat_type = beats, beat_type
                measure.fifths, measure.mode, measure.transpose = fifths, mode, transpose
                measure.multi_rest = int(text(node, "measure-style/multiple-rest", "0"))
                if node.find("time/senza-misura") is not None:
                    measure.implicit = True
                    issues.append(Issue("warning", "free_rhythm", part_id, number, "Unmeasured rhythm retained"))
            elif node.tag in ("backup", "forward"):
                delta = Fraction(text(node, "duration", "0")) / divisions
                cursor += -delta if node.tag == "backup" else delta
                if cursor < 0:
                    issues.append(Issue("error", "negative_cursor", part_id, number, "MusicXML backup exceeds bar start"))
            elif node.tag == "note":
                grace = node.find("grace") is not None
                duration = Fraction(0) if grace else Fraction(text(node, "duration", "0")) / divisions
                voice = text(node, "staff", "1") + ":" + text(node, "voice", "1")
                is_chord = node.find("chord") is not None
                start = last_event[voice].start if is_chord and voice in last_event else cursor
                kind = "rest" if node.find("rest") is not None else "grace" if grace else "unpitched" if node.find("unpitched") is not None else "note"
                event_ix += 1
                event = Event(f"{part_id}:{event_ix}", voice, start, duration, kind,
                              note_type=text(node, "type", "quarter"), dots=len(node.findall("dot")))
                if node.find("pitch") is not None:
                    try:
                        pitch = degree_pitch(text(node, "pitch/step"), int(text(node, "pitch/octave")),
                                             Fraction(text(node, "pitch/alter", "0")), fifths)
                        event.pitches.append(pitch)
                        pitch["keyFifths"] = fifths
                        pitch["sourceAccidental"] = text(node, "accidental")
                        if Fraction(pitch["accidental"]).denominator != 1:
                            issues.append(Issue("warning", "microtone", part_id, number, "Microtone displayed as alteration text"))
                    except ValueError as exc:
                        issues.append(Issue("error", "pitch", part_id, number, str(exc)))
                elif kind not in ("rest", "unpitched"):
                    issues.append(Issue("error", "missing_pitch", part_id, number, "Note has no pitch"))
                event.marks = notation_marks(node, part_id, number, issues)
                if grace:
                    event.grace = {"sourceAttributes": dict(node.find('grace').attrib)}
                if source_beaming:
                    event.beams = [{"number": int(b.get("number", "1")), "value": (b.text or "").strip()}
                                   for b in node.findall("beam")]
                if node.find("time-modification") is not None:
                    event.tuplet = {"actual": int(text(node, "time-modification/actual-notes", "3")),
                                    "normal": int(text(node, "time-modification/normal-notes", "2"))}
                    event.time_modification = dict(event.tuplet)
                    # Double-note tremolo contributes a 2:1 ratio of its own;
                    # this is not a displayed duplet. Keep the raw ratio intact.
                    if any(m['kind']=='tremolo' and m.get('type') in ('start','stop') for m in event.marks):
                        ratio = Fraction(event.tuplet['actual'], event.tuplet['normal']) / 2
                        event.tuplet = None if ratio == 1 else {'actual':ratio.numerator, 'normal':ratio.denominator}
                if is_chord and voice in last_event and last_event[voice].kind == kind and last_event[voice].duration == duration:
                    anchor = last_event[voice]
                    anchor.pitches.extend(event.pitches)
                    for mark in event.marks:
                        if mark not in anchor.marks:
                            anchor.marks.append(mark)
                else:
                    if is_chord:
                        issues.append(Issue("error", "unequal_chord", part_id, number,
                                            "Chord tones have different lengths or a missing anchor; review required"))
                    measure.events.append(event)
                    last_event[voice] = event
                if not is_chord and not grace:
                    cursor += duration
            elif node.tag == "direction":
                start = cursor + Fraction(text(node, "offset", "0")) / divisions
                for d in node.findall("direction-type/*"):
                    value = (d.text or "").strip()
                    if d.tag == "metronome":
                        value = text(d, "beat-unit", "quarter") + "=" + text(d, "per-minute")
                    elif d.tag == "dynamics":
                        value = " ".join((x.text or '').strip() if x.tag=='other-dynamics' else x.tag for x in d)
                    elif d.tag in ("wedge", "bracket", "dashes"):
                        value = d.get("type", "")
                    if d.tag in ("words", "rehearsal", "metronome", "dynamics", "wedge", "bracket", "dashes"):
                        measure.directions.append({"start": str(start), "kind": d.tag, "text": value,
                                                   **({"voice": text(node,'staff','1')+':'+text(node,'voice')} if node.find('voice') is not None else {}),
                                                   "fontStyle": d.get('font-style'), "fontWeight": d.get('font-weight'),
                                                   **({"beatUnit": text(d,'beat-unit','quarter'), "beatDots":len(d.findall('beat-unit-dot')), "perMinute":text(d,'per-minute')} if d.tag=='metronome' else {}),
                                                   "number": d.get("number", "1"),
                                                   "placement": node.get("placement", "below" if d.tag in ('dynamics','wedge') else "above")})
                    else:
                        issues.append(Issue("warning", "direction_fallback", part_id, number,
                                            f"Direction {d.tag} requires review"))
                sound = node.find("sound")
                if sound is not None and sound.get("tempo") and not any(d["kind"] == "metronome" and d["start"] == str(start) for d in measure.directions):
                    measure.directions.append({"start": str(start), "kind": "metronome", "text": "quarter=" + sound.get("tempo", "")})
            elif node.tag == "barline":
                measure.barlines.append({"location": node.get("location", "right"),
                                         "style": text(node, "bar-style", "regular"),
                                         "repeat": node.find("repeat").attrib if node.find("repeat") is not None else None,
                                         "ending": node.find("ending").attrib if node.find("ending") is not None else None})
            elif node.tag not in ("print", "sound"):
                issues.append(Issue("warning", "measure_element", part_id, number, f"Unmapped measure element: {node.tag}"))
        measure.transpose = transpose
        apply_numbered_accidentals(measure)
        # Full-bar rests without <type> use the bar length, not a quarter glyph.
        if not measure.events:
            issues.append(Issue("error", "empty_measure", part_id, number,
                                "No events found; an empty recognition result is not assumed to be a rest"))
        validate_measure(measure, part_id, issues)
        measures.append(measure)
    bind_graces(measures, part_id, issues)
    for measure in measures:
        apply_numbered_accidentals(measure)
    return Part(part_id, name, expand_multi_rests(measures, part_id, issues), str(path.resolve()))


def bind_graces(measures: list[Measure], part_id: str, issues: list[Issue]) -> None:
    """Bind zero-duration ornaments to a pitched principal, preserving XML order.

    Playback steal-time hints disambiguate middle groups; terminal groups are
    after-graces. A boundary after-grace is moved into its principal's measure.
    """
    previous = {}; bound = set(); pending = {}; explicit = {}
    locations = {e.id:(m,index) for index,(m,e) in enumerate((m,e) for m in measures for e in m.events)}
    for m in measures:
        for e in m.events:
            for mark in e.marks:
                if mark['kind']!='slur':continue
                key=(e.voice,mark.get('number','1'))
                if mark.get('type')=='stop' and key in pending:
                    first=pending.pop(key)
                    if {first.kind,e.kind}=={'grace','note'}:
                        ornament,anchor=(first,e) if first.kind=='grace' else (e,first)
                        explicit[ornament.id]=(locations[anchor.id][0],anchor,locations[ornament.id][1]>locations[anchor.id][1])
                if mark.get('type')=='start':pending[key]=e
    for measure in measures:
        for voice in dict.fromkeys(e.voice for e in measure.events):
            events = [e for e in measure.events if e.voice == voice and e.id not in bound]
            i = 0
            while i < len(events):
                event = events[i]
                if event.kind != 'grace':
                    if event.kind == 'note': previous[voice] = (measure, event)
                    i += 1; continue
                group = []
                while i < len(events) and events[i].kind == 'grace':
                    group.append(events[i]); i += 1
                following = next((e for e in events[i:] if e.kind == 'note'), None)
                prior = previous.get(voice)
                attributes = [e.grace['sourceAttributes'] for e in group]
                hint_after = any('steal-time-previous' in a for a in attributes) and not any('steal-time-following' in a for a in attributes)
                after = bool(prior and ((following is None and prior[0] is measure) or hint_after))
                target_measure, anchor = prior if after else (measure, following)
                source_targets=[explicit[e.id] for e in group if e.id in explicit]
                if source_targets:
                    target_measure,anchor,after=source_targets[0]
                if anchor is None:
                    issues.append(Issue('warning','grace_anchor',part_id,measure.number,'Grace group has no pitched principal; review required'))
                    continue
                for e in group:
                    bound.add(e.id)
                    e.start = anchor.start + anchor.duration if after else anchor.start
                    e.grace.update(position='after' if after else 'before', anchorId=anchor.id,
                                   slash=e.grace['sourceAttributes'].get('slash')=='yes')
                    if target_measure is not measure:
                        measure.events.remove(e)
                        if after:target_measure.events.append(e)
                        else:target_measure.events.insert(target_measure.events.index(anchor),e)
                        for p in e.pitches:
                            p.update(degree_pitch(p['step'],p['octave'],Fraction(p['alter']),target_measure.fifths),keyFifths=target_measure.fifths)
                first, last = (anchor,group[-1]) if after else (group[0],anchor)
                # Retain an explicit source connection instead of duplicating it.
                starts = {m.get('number','1') for e in ([anchor]+group if after else group) for m in e.marks if m['kind']=='slur' and m.get('type')=='start'}
                stops = {m.get('number','1') for e in (group if after else [anchor]) for m in e.marks if m['kind']=='slur' and m.get('type')=='stop'}
                if not starts.intersection(stops):
                    number='grace:'+group[0].id
                    first.marks.append({'kind':'grace-slur','type':'start','number':number})
                    last.marks.append({'kind':'grace-slur','type':'stop','number':number})


def apply_numbered_accidentals(measure: Measure) -> None:
    """Determine displayed cancellation independently of the sounding pitch.

    Nonzero relative alterations are repeated for clarity; an unaltered degree
    must display a natural after the same degree/octave was altered in this bar.
    The state is shared by voices of the same staff, ordered by musical time.
    """
    state = {}
    events = sorted(enumerate(measure.events), key=lambda x: (x[1].start, x[1].kind != "grace", x[0]))
    for _, event in events:
        for pitch in event.pitches:
            key = (event.voice.split(":")[0], pitch.get("keyFifths", measure.fifths),
                   pitch["degree"], pitch["octaveDots"])
            alteration = Fraction(pitch["accidental"])
            previous = state.get(key, Fraction(0))
            explicit_natural = pitch.get("sourceAccidental") == "natural"
            if alteration == 0 and (previous != 0 or explicit_natural):
                pitch["displayAccidental"] = "natural"
            else:
                pitch["displayAccidental"] = str(alteration)
            state[key] = alteration


def validate_measure(m: Measure, part_id: str, issues: list[Issue]) -> None:
    voices: dict[str, list[Event]] = defaultdict(list)
    for e in m.events:
        if e.kind != "grace":
            voices[e.voice].append(e)
    for voice, events in voices.items():
        end = Fraction(0)
        for e in sorted(events, key=lambda e: e.start):
            if e.start < end:
                issues.append(Issue("error", "voice_overlap", part_id, m.number,
                                    f"Voice {voice} overlaps at beat {e.start}"))
            if e.start > end:
                issues.append(Issue("error", "voice_gap", part_id, m.number,
                                    f"Voice {voice} has an unencoded gap from {end} to {e.start}"))
            end = max(end, e.start + e.duration)
        if not m.implicit and end != m.length:
            issues.append(Issue("error", "bar_duration", part_id, m.number,
                                f"Voice {voice} covers {end} quarter beats; expected {m.length}"))


def is_full_rest(m: Measure) -> bool:
    return bool(m.events) and all(e.kind == "rest" for e in m.events)


def expand_multi_rests(measures: list[Measure], part_id: str, issues: list[Issue]) -> list[Measure]:
    """Some exporters keep all rests; others encode only the first measure.

    Expand only when numeric measure numbers show a skipped range. Never add
    duplicates to an exporter that already provides the following measures.
    """
    result = []
    for ix, m in enumerate(measures):
        result.append(m)
        if m.multi_rest <= 1 or not m.number.isdigit():
            continue
        start = int(m.number)
        next_number = int(measures[ix + 1].number) if ix + 1 < len(measures) and measures[ix + 1].number.isdigit() else start + m.multi_rest
        if next_number == start + 1:
            continue
        if next_number != start + m.multi_rest or not is_full_rest(m):
            issues.append(Issue("error", "multi_rest_range", part_id, m.number,
                                f"Rest count {m.multi_rest} conflicts with next bar {next_number}"))
            continue
        for n in range(start + 1, next_number):
            rest = deepcopy(m)
            rest.number, rest.synthetic, rest.multi_rest = str(n), True, 0
            rest.directions, rest.barlines = [], []
            for e in rest.events:
                e.id = f"{part_id}:rest:{n}:{e.voice}"
                e.marks = []
            result.append(rest)
    return result


def align_parts(parts: list[Part], issues: list[Issue]) -> list[str]:
    numbers = [m.number for p in parts for m in p.measures]
    if not all(n.isdigit() for n in numbers):
        raise ValueError("Non-numeric measure numbering cannot be automatically aligned")
    ordered = sorted(set(numbers), key=int)
    for previous, current in zip(ordered, ordered[1:]):
        if int(current) != int(previous) + 1:
            issues.append(Issue("error", "global_bar_gap", "all", current,
                                f"No part accounts for bars between {previous} and {current}"))
    for part in parts:
        lookup = {m.number: m for m in part.measures}
        if len(lookup) != len(part.measures):
            issues.append(Issue("error", "duplicate_bar", part.id, "", "Duplicate measure numbers"))
        for number in ordered:
            if number not in lookup:
                issues.append(Issue("error", "missing_bar", part.id, number,
                                    "Part is missing this bar; renderer will show a review placeholder"))
    for number in ordered:
        context = [(p.id, next((m for m in p.measures if m.number == number), None)) for p in parts]
        contexts = {(m.beats, m.beat_type, m.length) for _, m in context if m and not m.implicit}
        if len(contexts) > 1:
            issues.append(Issue("error", "alignment_meter", "all", number,
                                "Parts disagree on meter or bar length"))
    return ordered
