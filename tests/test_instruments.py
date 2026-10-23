from copy import deepcopy
from fractions import Fraction as F
import json
import unittest
from unittest.mock import patch

from jianpu.instruments import CATALOG, describe_texture, resolve_instrument_profile
from jianpu.model import Event, Measure, Part
from jianpu.single import prepare_config
from jianpu.pipeline import build
from pathlib import Path
import tempfile


def event(name, voice, pitches=1, kind='note', start=0, duration=4, marks=()):
    return Event(name, voice, F(start), F(duration), kind, [{'degree': i+1} for i in range(pitches)], marks=list(marks))


def measure(number, events):
    return Measure(str(number), F(4), '4', 4, 0, 'major', events=events)


class InstrumentTextureTests(unittest.TestCase):
    def test_catalog_levels_references_and_unique_ids(self):
        c=json.loads(CATALOG.read_text(encoding='utf-8'))
        self.assertEqual(len({p['id'] for p in c['profiles']}),len(c['profiles']))
        for p in c['profiles']:
            for key,levels in c['levels'].items():self.assertIn(p[key],levels)
            self.assertTrue(set(p['sources'])<=c['sources'].keys())
            self.assertTrue(resolve_instrument_profile(p['id'])['policy']['preservePitchCollections'])

    def test_capabilities_are_independent_and_model_specific(self):
        for name in ('sheng-keyed','guzheng','yangqin'):
            p=resolve_instrument_profile(name)
            self.assertEqual(p['pitchCollections'],'common')
            self.assertEqual(p['soloIndependentVoices'],'documented')
            self.assertTrue(p['policy']['preserveSourceVoices'])
        self.assertEqual(resolve_instrument_profile('erhu')['pitchCollections'],'extended-review')
        self.assertEqual(resolve_instrument_profile('sanxian')['pitchCollections'],'unknown')

    def test_unknown_ids_and_family_conflicts_fail_without_guessing(self):
        self.assertIsNone(resolve_instrument_profile(None))
        with self.assertRaises(ValueError):resolve_instrument_profile('自动猜测笙')
        with self.assertRaises(ValueError):resolve_instrument_profile('qudi','plucked')
        p=resolve_instrument_profile('pipa');p['policy']['preserveSourceVoices']=False
        self.assertTrue(resolve_instrument_profile('pipa')['policy']['preserveSourceVoices'])

    def test_two_independent_voices_each_keep_chords_and_arpeggios(self):
        part=Part('p','笙',[measure(1,[event('a','1:1',3,marks=[{'kind':'arpeggiate'}]),
                                     event('b','1:2',2,marks=[{'kind':'arpeggiate'}])])],'test')
        before=deepcopy(part.to_json()['measures']);s=describe_texture(part)
        self.assertTrue(s['hasConcurrentVoicesAndChordEvents'])
        self.assertEqual([v['maximumPitchesPerEvent'] for v in s['voiceDetails']],[3,2])
        self.assertEqual(s['arpeggioEvents'],['a','b'])
        self.assertEqual(s['voiceMeaning'],'unresolved')
        part.instrument_profile=resolve_instrument_profile('sheng-keyed');part.texture_summary=s
        self.assertEqual(part.to_json()['measures'],before)

    def test_chords_in_one_passage_and_voices_in_another_are_not_simultaneous(self):
        part=Part('p','琵琶',[measure(1,[event('a','1:1',3)]),measure(2,[event('b','1:2')])],'test')
        s=describe_texture(part)
        self.assertTrue(s['hasMultipleSourceStreams']);self.assertTrue(s['hasChordEvents'])
        self.assertFalse(s['hasConcurrentSourceStreams']);self.assertFalse(s['hasConcurrentVoicesAndChordEvents'])

    def test_resting_and_grace_streams_do_not_create_notated_sounding_overlap(self):
        part=Part('p','曲笛',[measure(1,[event('a','1:1',2),event('b','1:2',0,'rest'),
            event('c','1:3',1,'grace',duration=0)])],'test')
        part.instrument_profile=resolve_instrument_profile('qudi')
        self.assertFalse(describe_texture(part)['hasConcurrentSourceStreams'])
        self.assertEqual(len(part.measures[0].events[0].pitches),2,'A cautionary profile must not delete unusual source pitches')

    def test_profile_config_is_carried_to_part_and_checked_before_omr(self):
        with tempfile.TemporaryDirectory(dir=CATALOG.parents[1]/'tmp') as folder:
            root=Path(folder);xml=root/'one.xml';xml.write_text('<score-partwise/>')
            profile=root/'profile.json';profile.write_text(json.dumps({'instrumentProfileId':'sheng-keyed'}))
            config,_=prepare_config(xml,root/'out.pdf',profile,workflow='local-dual-voice')
            self.assertEqual(config['parts'][0]['instrumentProfileId'],'sheng-keyed')
            config['parts'][0]['instrumentFamily']='plucked'
            cfg=root/'run.json';cfg.write_text(json.dumps(config))
            with patch('jianpu.pipeline.transcribe') as omr:
                with self.assertRaisesRegex(ValueError,'conflicts'):build(cfg)
                omr.assert_not_called()
