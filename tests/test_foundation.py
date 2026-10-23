from fractions import Fraction
import unittest

from jianpu.foundation import Clef, bar_quarters, plain_rhythm, staff_pitch
from jianpu.musicxml import apply_numbered_accidentals, degree_pitch
from jianpu.model import Measure, Event
from pathlib import Path
import tempfile
from test_musicxml import ATTR, note, rest
from jianpu.musicxml import parse_part


class FoundationTests(unittest.TestCase):
    def test_treble_lines_spaces_and_ledger(self):
        clef=Clef('G',2)
        self.assertEqual([staff_pitch(i,clef) for i in (0,2,4,6,8)], [('E',4),('G',4),('B',4),('D',5),('F',5)])
        self.assertEqual(staff_pitch(-2,clef),('C',4))
        self.assertEqual(staff_pitch(3,clef),('A',4))
    def test_other_clefs_have_different_anchor(self):
        self.assertEqual(staff_pitch(6,Clef('F',4)),('F',3))
        self.assertEqual(staff_pitch(0,Clef('F',4)),('G',2))
        self.assertEqual(staff_pitch(4,Clef('C',3)),('C',4))
        self.assertEqual(staff_pitch(2,Clef('G',2,-1)),('G',3))
    def test_meter_exact_quarter_totals(self):
        self.assertEqual(bar_quarters(4,4),4)
        self.assertEqual(bar_quarters(2,4),2)
        self.assertEqual(bar_quarters(3,8),Fraction(3,2))
    def test_basic_rhythm_is_not_rescaled_by_meter(self):
        self.assertEqual(plain_rhythm('quarter')['quarterDuration'],'1')
        self.assertEqual(plain_rhythm('eighth')['underlines'],1)
        self.assertEqual(plain_rhythm('16th')['underlines'],2)
        self.assertEqual(plain_rhythm('half')['extensionDashes'],1)
        self.assertEqual(plain_rhythm('whole')['extensionDashes'],3)
        self.assertEqual(plain_rhythm('half',1)['extensionDashes'],2)
        self.assertEqual(plain_rhythm('quarter',1)['quarterDuration'],'3/2')
    def test_cancel_flat_inside_bar(self):
        flat=degree_pitch('E',4,Fraction(-1),0);natural=degree_pitch('E',4,Fraction(0),0)
        m=Measure('1',Fraction(2),'2',4,0,'major',events=[
            Event('a','1:1',Fraction(0),Fraction(1),'note',[flat]),
            Event('b','1:1',Fraction(1),Fraction(1),'note',[natural])])
        apply_numbered_accidentals(m)
        self.assertEqual(flat['displayAccidental'],'-1')
        self.assertEqual(natural['displayAccidental'],'natural')
    def test_accidental_resets_at_barline(self):
        pitch=degree_pitch('E',4,Fraction(0),0)
        m=Measure('2',Fraction(1),'1',4,0,'major',events=[Event('a','1:1',Fraction(0),Fraction(1),'note',[pitch])])
        apply_numbered_accidentals(m)
        self.assertEqual(pitch['displayAccidental'],'0')


class FoundationXMLTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'tmp')
    def tearDown(self):
        self.tmp.cleanup()
    def parse(self,body):
        path=Path(self.tmp.name)/'score.musicxml'
        path.write_text('<score-partwise><part id="P1">'+body+'</part></score-partwise>',encoding='utf-8')
        issues=[]
        return parse_part(path,'p','笛',issues),issues
    def test_clef_preserved_and_inherited(self):
        attributes=ATTR.replace('</attributes>','<clef><sign>G</sign><line>2</line></clef></attributes>')
        p,_=self.parse(f'<measure number="1">{attributes}{rest()}</measure><measure number="2">{rest()}</measure>')
        self.assertEqual(p.measures[0].clefs['1'],{'sign':'G','line':2,'octaveChange':0})
        self.assertEqual(p.measures[1].clefs,p.measures[0].clefs)
    def test_three_eighths_in_three_eighth_meter(self):
        attributes=ATTR.replace('<beats>4</beats><beat-type>4</beat-type>','<beats>3</beats><beat-type>8</beat-type>')
        p,issues=self.parse(f'<measure number="1">{attributes}'+''.join(note(s,duration=6,kind='eighth') for s in 'CDE')+'</measure>')
        self.assertEqual(p.measures[0].length,Fraction(3,2))
        self.assertFalse([i for i in issues if i.severity=='error'])
