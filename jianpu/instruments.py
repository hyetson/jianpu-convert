"""Independent instrument capabilities and observed score texture, never routing rules."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import Part

CATALOG = Path(__file__).resolve().parents[1] / 'configs/instrument-capabilities.json'


def resolve_instrument_profile(profile_id: str | None, family: str = 'unknown') -> dict | None:
    if profile_id is None:
        return None
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    profile = next((p for p in catalog['profiles'] if p['id'] == profile_id), None)
    if profile is None:
        raise ValueError(f'Unknown instrumentProfileId: {profile_id}; select an explicit catalog ID')
    if family not in ('unknown', profile['family']):
        raise ValueError(f'instrumentProfileId {profile_id} conflicts with instrumentFamily {family}')
    return {'catalogVersion': catalog['catalogVersion'], 'checkedAt': catalog['checkedAt'],
            **deepcopy(profile), 'policy': deepcopy(catalog['policy'])}


def describe_texture(part: Part) -> dict:
    streams = sorted({e.voice for m in part.measures for e in m.events})
    chord_events = [e for m in part.measures for e in m.events if len(e.pitches) > 1]
    arpeggios = [e for m in part.measures for e in m.events if any(mark['kind'] == 'arpeggiate' for mark in e.marks)]
    concurrent = False
    concurrent_with_chords = False
    for measure in part.measures:
        # This is notated temporal overlap, not a claim about acoustic sustain or player count.
        sounding = [e for e in measure.events if e.kind not in ('rest', 'grace') and e.duration > 0]
        for i, a in enumerate(sounding):
            for b in sounding[i + 1:]:
                if a.voice != b.voice and max(a.start, b.start) < min(a.start + a.duration, b.start + b.duration):
                    concurrent = True
                    concurrent_with_chords |= len(a.pitches) > 1 or len(b.pitches) > 1
    return {'sourceStreams': streams, 'hasMultipleSourceStreams': len(streams) > 1,
            'hasChordEvents': bool(chord_events), 'chordEvents': [e.id for e in chord_events],
            'hasArpeggioMarks': bool(arpeggios), 'arpeggioEvents': [e.id for e in arpeggios],
            'hasConcurrentSourceStreams': concurrent,
            'hasConcurrentVoicesAndChordEvents': concurrent_with_chords,
            'voiceMeaning': 'unresolved',
            'voiceDetails': [{'voice': voice,
                'maximumPitchesPerEvent': max((len(e.pitches) for m in part.measures for e in m.events if e.voice == voice), default=0),
                'chordEvents': [e.id for e in chord_events if e.voice == voice],
                'arpeggioEvents': [e.id for e in arpeggios if e.voice == voice]} for voice in streams]}
