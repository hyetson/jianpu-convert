from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
import zipfile

from jianpu.musicxml import align_parts, degree_pitch, key_label, parse_part


ATTR = '<attributes><divisions>12</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time></attributes>'


def note(step='C', octave=4, duration=12, voice='1', extra='', chord=False, kind='quarter'):
    return f'<note>{"<chord/>" if chord else ""}<pitch><step>{step}</step><octave>{octave}</octave></pitch><duration>{duration}</duration><voice>{voice}</voice><type>{kind}</type>{extra}</note>'


def rest(duration=48):
    return f'<note><rest measure="yes"/><duration>{duration}</duration><voice>1</voice></note>'


class MusicXMLTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'tmp')
        self.path = Path(self.tmp.name) / 'score.musicxml'

    def tearDown(self):
        self.tmp.cleanup()

    def parse(self, body):
        self.path.write_text('<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Flute</part-name></score-part></part-list><part id="P1">'+body+'</part></score-partwise>', encoding='utf-8')
        issues = []
        return parse_part(self.path, 'flute', '笛', issues), issues

    def test_movabled_degree_and_accidental(self):
        p = degree_pitch('F', 4, Fraction(1), 2)
        self.assertEqual((p['degree'], p['accidental']), (3, '0'))
        p = degree_pitch('F', 4, Fraction(0), 2)
        self.assertEqual((p['degree'], p['accidental']), (3, '-1'))
        p = degree_pitch('C', 5, Fraction(0), 1)
        self.assertEqual((p['degree'], p['octaveDots']), (4, 0))

    def test_tuplet_display_preserves_source_ratio_and_curve_style(self):
        extra = ('<notations><tuplet type="start" number="2" line-shape="curved" bracket="yes" show-number="both">'
                 '<tuplet-actual><tuplet-number>3</tuplet-number></tuplet-actual>'
                 '<tuplet-normal><tuplet-number>2</tuplet-number></tuplet-normal></tuplet></notations>')
        part,_ = self.parse(f'<measure number="1">{ATTR}{note(duration=48,kind="whole",extra=extra)}</measure>')
        mark=part.measures[0].events[0].marks[0]
        self.assertEqual((mark['tupletActual'],mark['tupletNormal']),(3,2))
        self.assertEqual((mark['lineShape'],mark['bracket'],mark['showNumber']),('curved','yes','both'))

    def test_technique_semantics_and_original_xml_survive(self):
        extra = ('<notations><articulations><staccato print-object="no"/></articulations>'
                 '<ornaments><tremolo type="single">3</tremolo></ornaments>'
                 '<technical><harmonic><natural/><sounding-pitch/></harmonic>'
                 '<double-tongue/><other-technical>弹</other-technical></technical>'
                 '<arpeggiate/></notations>')
        part, issues = self.parse(f'<measure number="1">{ATTR}{note(duration=48,kind="whole",extra=extra)}</measure>')
        marks = {m['kind']:m for m in part.measures[0].events[0].marks}
        self.assertTrue(marks['staccato']['hidden'])
        self.assertEqual(marks['tremolo']['tremoloStrokes'], 3)
        self.assertEqual(marks['harmonic']['harmonic'], {'kind':'natural','pitchRole':'sounding-pitch'})
        self.assertIn('<natural', marks['harmonic']['sourceXml'])
        self.assertEqual(marks['arpeggiate']['direction'], '')
        self.assertEqual(marks['other-technical']['label'], '弹')
        self.assertFalse(issues)
        part.instrument_family = 'wind'
        self.assertEqual(part.to_json()['instrumentFamily'], 'wind')

    def test_artificial_harmonic_keeps_roles_and_requires_review(self):
        extra = '<notations><technical><harmonic><artificial/><touching-pitch/></harmonic></technical></notations>'
        part, issues = self.parse(f'<measure number="1">{ATTR}{note(duration=48,kind="whole",extra=extra)}</measure>')
        mark = part.measures[0].events[0].marks[0]
        self.assertEqual(mark['harmonic'], {'kind':'artificial','pitchRole':'touching-pitch'})
        self.assertTrue(any(i.code=='harmonic_pitch_review' for i in issues))

    def test_double_tremolo_time_modification_is_not_a_duplet(self):
        def extra(kind):
            return (f'<notations><ornaments><tremolo type="{kind}">3</tremolo></ornaments></notations>'
                    '<time-modification><actual-notes>2</actual-notes><normal-notes>1</normal-notes></time-modification>')
        part, issues = self.parse(f'<measure number="1">{ATTR}{note(duration=24,kind="whole",extra=extra("start"))}{note("E",duration=24,kind="whole",extra=extra("stop"))}</measure>')
        self.assertFalse(issues)
        self.assertEqual([e.duration for e in part.measures[0].events], [Fraction(2),Fraction(2)])
        for event in part.measures[0].events:
            self.assertIsNone(event.tuplet)
            self.assertEqual(event.to_json()['timeModification'], {'actual':2,'normal':1})

    def test_source_beams_distinguish_unbeamed_from_missing_metadata(self):
        part,_=self.parse(f'<measure number="1">{ATTR}{note(duration=6,kind="eighth",extra="<beam number=\"1\">begin</beam>")}{note(duration=6,kind="eighth",extra="<beam number=\"1\">end</beam>")}{note(duration=36)}</measure>')
        self.assertEqual(part.measures[0].events[0].beams,[{'number':1,'value':'begin'}])
        self.assertEqual(part.measures[0].events[1].beams,[{'number':1,'value':'end'}])
        self.assertEqual(part.measures[0].events[2].beams,[])
        part,_=self.parse(f'<measure number="1">{ATTR}{note(duration=48)}</measure>')
        self.assertIsNone(part.measures[0].events[0].beams)

    def test_front_and_terminal_graces_are_zero_time_and_bound_to_principal(self):
        grace=lambda step: f'<note><grace slash="yes"/><pitch><step>{step}</step><octave>5</octave></pitch><voice>1</voice><type>eighth</type></note>'
        part,issues=self.parse(f'<measure number="1">{ATTR}{grace("D")}{note(duration=48,kind="whole")}{grace("E")}{grace("F")}</measure>')
        events=part.measures[0].events;main=events[1]
        self.assertFalse(issues)
        self.assertEqual([e.grace['position'] for e in events if e.kind=='grace'],['before','after','after'])
        self.assertTrue(all(e.duration==0 and e.grace['anchorId']==main.id for e in events if e.kind=='grace'))
        self.assertEqual(events[-1].start,Fraction(4))
        self.assertEqual(sum(e.duration for e in events),Fraction(4))
        self.assertEqual(len([m for e in events for m in e.marks if m['kind']=='grace-slur']),4)

    def test_boundary_after_grace_moves_to_principals_measure(self):
        grace='<note><grace steal-time-previous="10"/><pitch><step>D</step><octave>5</octave></pitch><voice>1</voice><type>eighth</type></note>'
        part,issues=self.parse(f'<measure number="1">{ATTR}{note(duration=48)}</measure><measure number="2">{grace}{note(duration=48)}</measure>')
        self.assertFalse(issues)
        self.assertEqual([len(m.events) for m in part.measures],[2,1])
        self.assertEqual(part.measures[0].events[-1].grace['position'],'after')
        self.assertEqual(part.measures[0].events[-1].grace['anchorId'],part.measures[0].events[0].id)

    def test_metronome_keeps_dotted_unit_and_terms_keep_source_style(self):
        direction='<direction><direction-type><words font-style="italic" font-weight="bold">più mosso</words><metronome><beat-unit>eighth</beat-unit><beat-unit-dot/><per-minute>96</per-minute></metronome></direction-type></direction>'
        part,issues=self.parse(f'<measure number="1">{ATTR}{direction}{note(duration=48)}</measure>')
        words,metro=part.measures[0].directions
        self.assertEqual((words['fontStyle'],words['fontWeight']),('italic','bold'))
        self.assertEqual((metro['beatUnit'],metro['beatDots'],metro['perMinute']),('eighth',1,'96'))
        self.assertFalse(issues)

    def test_source_slur_moves_front_grace_to_following_principals_measure(self):
        grace='<note><grace/><pitch><step>D</step><octave>5</octave></pitch><voice>1</voice><type>eighth</type><notations><slur type="start" number="2"/></notations></note>'
        principal=note(duration=48,extra='<notations><slur type="stop" number="2"/></notations>')
        part,issues=self.parse(f'<measure number="1">{ATTR}{note(duration=48)}{grace}</measure><measure number="2">{principal}</measure>')
        self.assertFalse(issues)
        self.assertEqual([len(m.events) for m in part.measures],[1,2])
        ornament,anchor=part.measures[1].events
        self.assertEqual((ornament.grace['position'],ornament.grace['anchorId']),('before',anchor.id))
        self.assertEqual(ornament.start,0)

    def test_octave_boundary_floor(self):
        self.assertEqual(degree_pitch('B', 3, Fraction(0), 0)['octaveDots'], -1)
        self.assertEqual(degree_pitch('C', 5, Fraction(0), 0)['octaveDots'], 1)
        self.assertEqual(degree_pitch('F', 4, Fraction(1), 1)['degree'], 7)

    def test_minor_label_relative_major(self):
        self.assertEqual(key_label(0, 'minor'), '6=A')
        self.assertEqual(key_label(2, 'minor'), '6=B')
        self.assertEqual(key_label(-3, 'minor'), '6=C')

    def test_chord_does_not_advance_time(self):
        part, issues = self.parse(f'<measure number="1">{ATTR}{note(duration=48, kind="whole")}{note("E",duration=48,chord=True,kind="whole")}</measure>')
        self.assertEqual(len(part.measures[0].events), 1)
        self.assertEqual(len(part.measures[0].events[0].pitches), 2)
        self.assertFalse([i for i in issues if i.severity == 'error'])

    def test_backup_keeps_voices_separate(self):
        part, issues = self.parse(f'<measure number="1">{ATTR}{note(duration=48)}<backup><duration>48</duration></backup>{note("E",duration=48,voice="2")}</measure>')
        events = part.measures[0].events
        self.assertEqual([e.voice for e in events], ['1:1','1:2'])
        self.assertEqual([e.start for e in events], [Fraction(0),Fraction(0)])
        self.assertFalse([i for i in issues if i.severity == 'error'])

    def test_tuplets_keep_exact_time_and_notes(self):
        tuplet = '<time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification>'
        notes = ''.join(note(s,duration=4,kind='eighth',extra=tuplet) for s in 'CDE') + note('F',duration=36,kind='half')
        part, issues = self.parse(f'<measure number="1">{ATTR}{notes}</measure>')
        self.assertEqual(part.measures[0].events[1].start, Fraction(1,3))
        self.assertEqual(len(part.measures[0].events), 4)
        self.assertFalse([i for i in issues if i.severity == 'error'])

    def test_multi_rest_collapsed_expansion(self):
        attr = ATTR.replace('</attributes>','<measure-style><multiple-rest>3</multiple-rest></measure-style></attributes>')
        part, issues = self.parse(f'<measure number="1">{attr}{rest()}</measure><measure number="4">{rest()}</measure>')
        self.assertEqual([m.number for m in part.measures], ['1','2','3','4'])
        self.assertTrue(part.measures[1].synthetic)
        self.assertFalse([i for i in issues if i.severity == 'error'])

    def test_multi_rest_explicit_does_not_duplicate(self):
        attr = ATTR.replace('</attributes>','<measure-style><multiple-rest>3</multiple-rest></measure-style></attributes>')
        part, _ = self.parse(f'<measure number="1">{attr}{rest()}</measure><measure number="2">{rest()}</measure><measure number="3">{rest()}</measure>')
        self.assertEqual(len(part.measures), 3)

    def test_empty_recognition_is_not_rest(self):
        part, issues = self.parse(f'<measure number="1">{ATTR}</measure>')
        self.assertEqual(part.measures[0].events, [])
        self.assertIn('empty_measure', [i.code for i in issues])

    def test_overfull_bar_is_reported(self):
        _, issues = self.parse(f'<measure number="1">{ATTR}{note(duration=60)}</measure>')
        self.assertIn('bar_duration',[i.code for i in issues])

    def test_tie_and_slur_are_distinct(self):
        notation='<tie type="start"/><notations><slur type="start" number="2"/></notations>'
        part, _ = self.parse(f'<measure number="1">{ATTR}{note(duration=48,extra=notation)}</measure>')
        self.assertEqual({m['kind'] for m in part.measures[0].events[0].marks}, {'slur','tied'})

    def test_trill_upper_accidental_is_attached_to_ornament_not_pitch(self):
        notation='<notations><ornaments><trill-mark/><accidental-mark placement="above">flat</accidental-mark></ornaments></notations>'
        part,issues=self.parse(f'<measure number="1">{ATTR}{note(duration=48,extra=notation)}</measure>')
        event=part.measures[0].events[0]
        self.assertEqual(event.marks[0]['ornamentAccidental'],'flat')
        self.assertEqual(event.pitches[0]['alter'],'0')
        self.assertFalse(issues)

    def test_mxl_container(self):
        self.parse(f'<measure number="1">{ATTR}{rest()}</measure>')
        mxl=Path(self.tmp.name)/'score.mxl'
        with zipfile.ZipFile(mxl,'w') as z:
            z.writestr('META-INF/container.xml','<container><rootfiles><rootfile full-path="score.xml" media-type="application/vnd.recordare.musicxml+xml"/></rootfiles></container>')
            z.write(self.path,'score.xml')
        self.assertEqual(len(parse_part(mxl,'p','笛',[]).measures),1)

    def test_curve_style_orientation_and_chord_tie_pitch_are_preserved(self):
        marks='<notations><slur type="start" number="2" orientation="under" line-type="dashed" bezier-x="12"/><tied type="start"/></notations>'
        hidden='<notations><tied type="start" print-object="no"/></notations>'
        part,_=self.parse(f'<measure number="1">{ATTR}{note(duration=48,extra=marks)}{note("E",duration=48,chord=True,extra=hidden)}</measure>')
        events=part.measures[0].events
        slur=next(m for m in events[0].marks if m['kind']=='slur')
        self.assertEqual((slur['placement'],slur['lineType'],slur['sourceGeometry']),('below','dashed',{'bezier-x':'12'}))
        ties=[m for m in events[0].marks if m['kind']=='tied']
        self.assertEqual([m['pitchKey'] for m in ties],['C4:0','E4:0'])
        self.assertEqual([m['hidden'] for m in ties],[False,True])

    def test_missing_measure_is_not_silently_padded(self):
        a,_=self.parse(f'<measure number="1">{ATTR}{rest()}</measure><measure number="2">{rest()}</measure>')
        b,_=self.parse(f'<measure number="1">{ATTR}{rest()}</measure>')
        b.id='b';issues=[]
        self.assertEqual(align_parts([a,b],issues),['1','2'])
        self.assertIn('missing_bar',[i.code for i in issues])


if __name__=='__main__':
    unittest.main()
