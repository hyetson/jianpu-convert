from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

from jianpu.pipeline import PROJECT, build
from jianpu.single import prepare_config
from jianpu.musicxml import parse_part


class SingleVoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=PROJECT/'tmp')
        self.root=Path(self.temp.name)
        self.xml=self.root/'声部.musicxml'
        self.xml.write_text('<score-partwise><part id="P1"/></score-partwise>',encoding='utf-8')
        self.pdf=self.root/'输入.pdf';self.pdf.write_bytes(b'%PDF-example')
        self.profile=self.root/'profile.json'
        self.profile.write_text(json.dumps({'fonts':{'music':'fonts/music.otf'},'layout':{'fontSize':14}}),encoding='utf-8')
        self.output=self.root/'output.pdf'

    def tearDown(self):self.temp.cleanup()

    def test_profile_paths_are_independent_of_working_directory(self):
        config,xml=prepare_config(self.xml,self.output,self.profile,instrument_family='wind',instrument_name='梆笛',title='测试')
        self.assertEqual(config['workflow'],'single-voice')
        self.assertEqual(config['title'],'测试')
        self.assertEqual(config['fonts']['music'],str(self.root/'fonts/music.otf'))
        self.assertEqual(xml,[self.xml])
        self.assertEqual(config['parts'][0]['instrumentFamily'],'wind')

    def test_pdf_recognition_and_reviewed_xml_are_explicit_separate_paths(self):
        config,xml=prepare_config(self.pdf,self.output,self.profile)
        self.assertIsNone(xml);self.assertEqual(config['parts'][0]['pdf'],str(self.pdf))
        config,xml=prepare_config(self.pdf,self.output,self.profile,musicxml=self.xml,xml_part='P1')
        self.assertEqual(xml,[self.xml]);self.assertEqual(config['parts'][0]['musicxmlPart'],'P1')
        with self.assertRaises(ValueError):prepare_config(self.xml,self.output,self.profile,musicxml=self.xml)

    def test_single_workflow_refuses_invalid_output_family_and_midi(self):
        with self.assertRaises(ValueError):prepare_config(self.pdf,self.pdf,self.profile)
        with self.assertRaises(ValueError):prepare_config(self.xml,self.root/'result.txt',self.profile)
        with self.assertRaises(ValueError):prepare_config(self.xml,self.output,self.profile,instrument_family='guessed')
        midi=self.root/'input.mid';midi.write_bytes(b'MThd')
        with self.assertRaises(ValueError):prepare_config(midi,self.output,self.profile)

    def test_single_workflow_never_renders_multiple_voices_even_in_draft_mode(self):
        self.xml.write_text('<score-partwise><part id="P1"><measure number="1"><attributes><divisions>1</divisions>'
            '<key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time></attributes>'
            '<note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>whole</type></note>'
            '<backup><duration>4</duration></backup>'
            '<note><pitch><step>E</step><octave>4</octave></pitch><duration>4</duration><voice>2</voice><type>whole</type></note>'
            '</measure></part></score-partwise>',encoding='utf-8')
        font=str(PROJECT/'tools/fonts/Bravura.otf')
        config={'workflow':'single-voice','parts':[{'id':'one','name':'一'}],'output':str(self.output),'fonts':{'text':font,'music':font}}
        path=self.root/'run.json';path.write_text(json.dumps(config),encoding='utf-8')
        with patch('jianpu.pipeline.subprocess.run') as renderer:
            with self.assertRaisesRegex(ValueError,'2 staff:voice'):
                build(path,xml_inputs=[self.xml],node_executable=sys.executable,draft=True)
            renderer.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assertTrue(list(self.root.glob('runs/*/failure.json')))

    def test_single_workflow_rejects_multiple_parts_before_omr(self):
        config={'workflow':'single-voice','parts':[{'id':'one'},{'id':'two'}]}
        path=self.root/'run.json';path.write_text(json.dumps(config),encoding='utf-8')
        with patch('jianpu.pipeline.transcribe') as omr:
            with self.assertRaisesRegex(ValueError,'exactly one part'):build(path)
            omr.assert_not_called()

    def write_voices(self, count):
        notes=[]
        for i in range(1,count+1):
            if i>1:notes.append('<backup><duration>4</duration></backup>')
            notes.append(f'<direction placement="below"><direction-type><dynamics><p/></dynamics></direction-type><voice>{i}</voice></direction>')
            notes.append(f'<note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><voice>{i}</voice><type>whole</type></note>')
            if i==1:notes.append('<note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>whole</type></note>')
        self.xml.write_text('<score-partwise><part id="P1"><measure number="1"><attributes><divisions>1</divisions>'
            '<key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time></attributes>'+''.join(notes)+
            '</measure></part></score-partwise>',encoding='utf-8')

    def test_dual_workflow_preserves_chords_and_scoped_directions(self):
        self.write_voices(2)
        issues=[];part=parse_part(self.xml,'solo','单乐器',issues)
        self.assertEqual(issues,[])
        self.assertEqual(len(part.measures[0].events),2)
        self.assertEqual(len(part.measures[0].events[0].pitches),2)
        self.assertEqual([d['voice'] for d in part.measures[0].directions],['1:1','1:2'])
        config,_=prepare_config(self.xml,self.output,self.profile,workflow='local-dual-voice',primary_voice='1:2')
        self.assertEqual(config['workflow'],'local-dual-voice')
        self.assertEqual(config['localVoices']['primaryVoice'],'1:2')
        with self.assertRaises(ValueError):prepare_config(self.xml,self.output,self.profile,primary_voice='1:2')

    def test_dual_rejects_third_voice_and_absent_primary_before_rendering(self):
        for count,primary,message in [(3,None,'1-2 staff:voice'),(2,'1:9','Primary voice')]:
            self.write_voices(count)
            config,_=prepare_config(self.xml,self.output,PROJECT/'configs/dual-voice.json',workflow='local-dual-voice',primary_voice=primary)
            # This rejection test needs existing files, not a reference-score font.
            font=str(PROJECT/'tools/fonts/Bravura.otf')
            config['fonts']={'text':font,'music':font}
            path=self.root/'dual.json';path.write_text(json.dumps(config),encoding='utf-8')
            with patch('jianpu.pipeline.subprocess.run') as renderer:
                with self.assertRaisesRegex(ValueError,message):build(path,xml_inputs=[self.xml],node_executable=sys.executable,draft=True)
                renderer.assert_not_called()
