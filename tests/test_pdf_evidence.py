from pathlib import Path
import tempfile
from unittest.mock import patch
import unittest
import zipfile

from jianpu.pdf_evidence import repair_rest_counts
from jianpu.musicxml import read_xml
from test_musicxml import ATTR, rest, note


class FakePage:
    width=100;height=100
    def __init__(self,words):self.words=words
    def extract_words(self,extra_attrs=None):
        assert extra_attrs==['fontname','size']
        return self.words


class FakePDF:
    def __init__(self,words):self.pages=[FakePage(words)]
    def __enter__(self):return self
    def __exit__(self,*args):pass


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'tmp')
        self.folder=Path(self.tmp.name);self.xml=self.folder/'raw.musicxml'
        with zipfile.ZipFile(self.folder/'score.omr','w') as z:
            z.writestr('sheet#1/sheet#1.xml','<sheet><picture width="1000" height="1000"/><system><sig><inters><multiple-rest id="1"><bounds x="300" y="400" w="100" h="10"/></multiple-rest></inters></sig></system></sheet>')
        attr=ATTR.replace('</attributes>','<measure-style><multiple-rest>2</multiple-rest></measure-style></attributes>')
        self.xml.write_text(f'<score-partwise><part id="P1"><measure number="1">{attr}{rest()}</measure><measure number="2">{rest()}</measure><measure number="4">{note(duration=48)}</measure></part></score-partwise>',encoding='utf-8')
    def tearDown(self):self.tmp.cleanup()
    def repair(self,words):
        issues=[]
        with patch('pdfplumber.open',return_value=FakePDF(words)):
            out=repair_rest_counts(self.folder/'fake.pdf',self.xml,self.folder,'p',issues)
        return out,issues
    def test_source_count_changes_only_rest_group_and_preserves_gap(self):
        out,issues=self.repair([{'text':'14','x0':33,'x1':37,'top':28,'bottom':32}])
        measures=read_xml(out).findall('part/measure')
        self.assertEqual(len(measures),15)
        self.assertEqual(measures[-1].get('number'),'16')
        self.assertEqual(len(measures[-1].findall('note/pitch')),1)
        self.assertIn('rest_counts_corrected',[i.code for i in issues])
    def test_ambiguous_source_refuses_correction(self):
        words=[{'text':v,'x0':33,'x1':37,'top':28,'bottom':32} for v in ('14','15')]
        out,issues=self.repair(words)
        self.assertEqual(out,self.xml)
        self.assertIn('rest_mapping',[i.code for i in issues])
    def test_no_source_digit_does_not_guess(self):
        out,issues=self.repair([])
        self.assertEqual(out,self.xml)
        self.assertIn('rest_count_unverified',[i.code for i in issues])
