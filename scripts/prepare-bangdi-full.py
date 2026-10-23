"""Source-backed preparation for this three-page, vector 梆笛 score.

Uses the retained Audiveris export and the INPUT PDF's staff geometry/text layer.
This is a score-specific review adapter, not a general OMR accuracy guarantee.
It never reads the reference numbered-notation PDF.
"""
from pathlib import Path
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import sys
import xml.etree.ElementTree as E
import pdfplumber

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from jianpu.musicxml import read_xml,parse_part
from jianpu.vector_wedges import restore_vector_wedges
from jianpu.vector_beams import restore_vector_beams

PDF=ROOT/'example/Silk Road 2012 - 梆笛.pdf'
CACHE=ROOT/'output/jianpu/runs/20261014-155028-7af122/bangdi'
OUT=ROOT/'output/jianpu/bangdi-full-source'
OUT.mkdir(parents=True,exist_ok=True)
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((CACHE/'source.json').read_text(encoding='utf-8'))['sha256']==digest(PDF),'Cached OMR belongs to another PDF'
root=read_xml(CACHE/'corrected.musicxml')
part=root.find('part');measures=part.findall('measure')
assert len(measures)==254
changes=[]
systems=[];remaining=0
for number,m in enumerate(measures,1):
    old=m.get('number');m.set('number',str(number))
    if old!=str(number):changes.append({'kind':'bar-number','measure':number,'before':old,'after':number})
    if m.find('print') is not None:systems.append([])
    if remaining:remaining-=1;continue
    systems[-1].append((number,m))
    remaining=int(m.findtext('attributes/measure-style/multiple-rest','1'))-1
expected_anchors=[1,43,49,72,76,85,106,110,121,126,130,143,147,152,167,193,221,232,242,246,250]
assert [s[0][0] for s in systems]==expected_anchors

def pitch_index(step,octave):return 7*int(octave)+'CDEFGAB'.index(step)

evidence=[]
with pdfplumber.open(PDF) as document:
    system_index=0
    for page_no,page in enumerate(document.pages,1):
        staff_lines=sorted([l for l in page.lines if l['width']>300 and l['height']<.05],key=lambda l:l['top'])
        assert len(staff_lines)==35
        staffs=[staff_lines[i:i+5] for i in range(0,len(staff_lines),5)]
        notes_by_staff=defaultdict(list)
        for c in page.chars:
            if c['text'] not in ('œ','˙','w') or 'Maestro' not in c['fontname']:continue
            y=page.height-c['matrix'][5]
            staff_index=min(range(len(staffs)),key=lambda i:abs(y-(staffs[i][0]['top']+staffs[i][-1]['top'])/2))
            lines=staffs[staff_index];bottom=lines[-1]['top'];half_step=(bottom-lines[0]['top'])/8
            position=round((bottom-y)/half_step)
            assert abs((bottom-y)/half_step-position)<.12
            index=30+position # bottom treble line E4: 7*4 + CDEFGAB.index(E)
            head={'x':c['x0'],'y':y,'glyph':c['text'],'step':'CDEFGAB'[index%7],'octave':index//7,'small':c['size']<15,'size':c['size']}
            stems=[l for l in page.lines if l['width']<.05 and l['height']>c['size']*.4 and c['x0']-.5<l['x0']<c['x0']+c['size']*.35
                   and min(abs(l['top']-y),abs(l['bottom']-y))<1.6]
            beam_levels=[]
            if stems:
                stem=min(stems,key=lambda l:min(abs(l['top']-y),abs(l['bottom']-y)))
                beam_levels=[round(r['top'],2) for r in page.rects if r['width']>2 and .4<r['height']<3
                             and r['x0']-.6<=stem['x0']<=r['x1']+.6 and stem['top']-3<=r['top']<=stem['bottom']+1]
            head['beams']=len(set(beam_levels))
            notes_by_staff[staff_index].append(head)
        for staff_index,lines in enumerate(staffs):
            top,bottom=lines[0]['top'],lines[-1]['top'];left,right=lines[0]['x0'],lines[0]['x1']
            xs=sorted({l['x0'] for l in page.lines if l['width']<.05 and abs(l['top']-top)<.2 and abs(l['bottom']-bottom)<.2})
            edges=[]
            for x in [left]+[x for x in xs if x>left+.2]+[right]:
                if edges and x-edges[-1]<5:edges[-1]=max(x,edges[-1])
                else:edges.append(x)
            # The courtesy 2/4 after the final rest of source system 5 is not a bar.
            if page_no==1 and staff_index==4 and edges[-1]-edges[-2]<25:edges.pop(-2)
            mapping=systems[system_index];system_index+=1
            assert len(edges)-1==len(mapping),(page_no,staff_index,edges,[n for n,_ in mapping])
            for (a,b),(number,m) in zip(zip(edges,edges[1:]),mapping):
                heads=sorted([n for n in notes_by_staff[staff_index] if a<=n['x']<b],key=lambda n:(round(n['x'],1),pitch_index(n['step'],n['octave'])))
                accidentals=[]
                for c in page.chars:
                    if 'Maestro' not in c['fontname'] or c['text'] not in ('b','#','n') or not a<=c['x0']<b:continue
                    y=page.height-c['matrix'][5]
                    candidates=[n for n in heads if .5<n['x']-c['x0']<20 and abs(n['y']-y)<1]
                    if candidates:
                        target=min(candidates,key=lambda n:n['x']-c['x0'])
                        target['explicitAlter']={'b':-1,'#':1,'n':0}[c['text']]
                        accidentals.append({'symbol':c['text'],'x':c['x0'],'y':y,'noteX':target['x']})
                state={}
                for n in heads:
                    key=(n['step'],n['octave'])
                    if 'explicitAlter' in n:state[key]=n['explicitAlter']
                    n['alter']=state.get(key,0)
                main=[n for n in heads if not n['small']]
                # Six spurious OMR quarter notes overlay valid beamed notes here.
                xml_main=[n for n in m.findall('note') if n.find('pitch') is not None and n.find('grace') is None and n.findtext('voice','1')=='1']
                extra=[n for n in m.findall('note') if n.findtext('voice','1')!='1']
                assert len(main)==len(xml_main),(number,'source/OMR head mismatch',len(main),len(xml_main))
                if extra:
                    assert number in (242,243,250,251)
                    changes.append({'kind':'phantom-voices','measure':number,'removed':len(extra),'sourceMainHeads':len(main)})
                    for n in extra:m.remove(n)
                    for node in list(m):
                        if node.tag in ('backup','forward'):m.remove(node)
                # Sort members of a notated chord by written pitch before matching.
                ordered=[]
                for n in xml_main:
                    if n.find('chord') is not None:ordered[-1].append(n)
                    else:ordered.append([n])
                xml_main=[n for group in ordered for n in sorted(group,key=lambda n:pitch_index(n.findtext('pitch/step'),n.findtext('pitch/octave')))]
                for n,head in zip(xml_main,main):
                    old=(n.findtext('pitch/step'),n.findtext('pitch/octave'),n.findtext('pitch/alter','0'))
                    pitch=n.find('pitch');pitch.find('step').text=head['step'];pitch.find('octave').text=str(head['octave'])
                    alter=pitch.find('alter')
                    if alter is None:alter=E.SubElement(pitch,'alter')
                    alter.text=str(head['alter'])
                    after=(head['step'],str(head['octave']),str(head['alter']))
                    if old!=after:changes.append({'kind':'pitch','measure':number,'before':old,'after':after,'source':[page_no,head['x'],head['y']]})
                    accidental=n.find('accidental')
                    if accidental is not None:n.remove(accidental)
                    if 'explicitAlter' in head:E.SubElement(n,'accidental').text={-1:'flat',0:'natural',1:'sharp'}[head['explicitAlter']]
                for c in page.chars:
                    if c['text'] not in ('Ÿ','i') or 'Maestro' not in c['fontname'] or not a<=c['x0']<b or not main:continue
                    head,target=min(zip(main,xml_main),key=lambda pair:abs(pair[0]['x']-c['x0']))
                    y=page.height-c['matrix'][5]
                    if abs(head['x']-c['x0'])<15 and head['y']-40<y<head['y']:
                        if target.find('notations/ornaments/trill-mark') is None:
                            ns=target.find('notations')
                            if ns is None:ns=E.SubElement(target,'notations')
                            ornaments=E.SubElement(ns,'ornaments');E.SubElement(ornaments,'trill-mark')
                            if c['text']=='i':E.SubElement(ornaments,'accidental-mark',placement='above').text='flat'
                            changes.append({'kind':'restore-trill','measure':number,'source':[page_no,c['x0'],y]})
                for head in [n for n in heads if n['small']]:
                    later=[(h,n) for h,n in zip(main,xml_main) if h['x']>head['x']]
                    target=min(later,key=lambda pair:pair[0]['x'])[1] if later else None
                    grace=E.Element('note');E.SubElement(grace,'grace',slash='yes')
                    pitch=E.SubElement(grace,'pitch')
                    for key in ('step','alter','octave'):E.SubElement(pitch,key).text=str(head[key])
                    E.SubElement(grace,'voice').text='1'
                    E.SubElement(grace,'type').text={0:'eighth',1:'eighth',2:'16th',3:'32nd'}.get(head['beams'],'eighth')
                    siblings=[n for n in heads if n['small'] and abs(n['x']-head['x'])<100]
                    for level in range(1,head['beams']+1):
                        members=[n for n in siblings if n['beams']>=level]
                        pos=members.index(head)
                        if len(members)>1:E.SubElement(grace,'beam',number=str(level)).text='begin' if pos==0 else 'end' if pos==len(members)-1 else 'continue'
                    if target is not None:m.insert(list(m).index(target),grace)
                    else:m.append(grace) # written end-of-bar ornament before the next bar
                    changes.append({'kind':'restore-grace','measure':number,'pitch':[head['step'],head['octave'],head['alter']],'source':[page_no,head['x'],head['y']]})
                evidence.append({'measure':number,'page':page_no,'system':system_index,'bounds':[a,top,b,bottom],'notes':heads,'accidentals':accidentals})

# Convert to a common exact tick unit, preserving original rational durations.
division=1;beats=4;beat_type=4
for m in measures:
    if m.find('attributes/divisions') is not None:division=int(m.findtext('attributes/divisions'))
    if m.find('attributes/time') is not None:
        beats=int(m.findtext('attributes/time/beats'));beat_type=int(m.findtext('attributes/time/beat-type'))
    for node in m:
        dur=node.find('duration')
        if dur is not None:dur.text=str(Fraction(dur.text)/division)
    for attr in m.findall('attributes'):
        div=attr.find('divisions')
        if div is not None:attr.remove(div)
    notes=m.findall('note')
    if len(notes)==1 and notes[0].find('rest') is not None and notes[0].find('rest').get('measure')=='yes':
        dur=notes[0].find('duration');expected=Fraction(beats*4,beat_type)
        if Fraction(dur.text)!=expected:
            changes.append({'kind':'full-rest-duration','measure':int(m.get('number')),'before':dur.text,'after':str(expected)})
            dur.text=str(expected)

def notes_at(number):return [n for n in measures[number-1].findall('note') if n.find('grace') is None]

for number in (72,147):
    m=measures[number-1];n=notes_at(number)[0];assert n.find('rest') is not None
    changes.append({'kind':'false-rest','measure':number,'removedDuration':n.findtext('duration')})
    m.remove(n)

for number,count,normal in [(75,7,4),(107,6,4)]:
    notes=notes_at(number)[-count:]
    for i,n in enumerate(notes):
        n.find('duration').text=str(Fraction(n.findtext('duration'))*Fraction(normal,count))
        tm=n.find('time-modification')
        if tm is not None:n.remove(tm)
        tm=E.SubElement(n,'time-modification')
        E.SubElement(tm,'actual-notes').text=str(count);E.SubElement(tm,'normal-notes').text=str(normal)
        E.SubElement(tm,'normal-type').text=n.findtext('type')
        ns=n.find('notations')
        if ns is None:ns=E.SubElement(n,'notations')
        if i in (0,count-1):E.SubElement(ns,'tuplet',type='start' if i==0 else 'stop',number='1')
    changes.append({'kind':'source-tuplet','measure':number,'actual':count,'normal':normal})

# Source bar 140 has one augmentation dot on Ab5; OMR counted two.
n=notes_at(140)[-2]
assert n.findtext('pitch/step')=='A' and len(n.findall('dot'))==2
n.remove(n.findall('dot')[-1]);n.find('duration').text='3/8'
changes.append({'kind':'augmentation-dot','measure':140,'before':'7/16, two dots','after':'3/8, one dot','source':'page 2 system 4, Ab5 before last G5'})

# The last beamed group visibly includes an eighth rest before its high G.
m=measures[-1];target=notes_at(254)[2]
rest=E.Element('note');E.SubElement(rest,'rest');E.SubElement(rest,'duration').text='1/2'
E.SubElement(rest,'voice').text='1';E.SubElement(rest,'type').text='eighth'
m.insert(list(m).index(target),rest)
changes.append({'kind':'restore-rest','measure':254,'duration':'1/2','source':'page 3 final measure eighth-rest glyph'})

attr=measures[0].find('attributes')
E.SubElement(attr,'divisions').text='336'
for m in measures:
    for node in m:
        dur=node.find('duration')
        if dur is not None:
            ticks=Fraction(dur.text)*336
            assert ticks.denominator==1,(m.get('number'),dur.text)
            dur.text=str(ticks.numerator)
    # Remove duplicate OMR tie marks (two identical starts cannot be paired).
    for n in m.findall('note'):
        for parent in (n,n.find('notations')):
            if parent is None:continue
            seen=set()
            for child in list(parent):
                if child.tag not in ('tie','tied'):continue
                key=(child.tag,tuple(sorted(child.attrib.items())))
                if key in seen:parent.remove(child)
                seen.add(key)

# Reapply visible tempo/instrument directions that OMR omitted. These mark
# structural rest boundaries; they are transcribed from the INPUT PDF only.
for number,words,tempo in [(1,'Rubato',52),(15,'Moderato',92),(57,'piu mosso',96),
                           (85,'',80),(112,'piu mosso',None),(236,'presto',184),
                           (41,'F梆笛 solo',None),(68,'a2',None),(99,'C梆笛',None),(218,'小梆笛',None)]:
    m=measures[number-1]
    if words:
        d=E.Element('direction',placement='above');E.SubElement(E.SubElement(d,'direction-type'),'words').text=words
        m.insert(list(m).index(m.find('note')),d)
    if tempo:
        d=E.Element('direction',placement='above');metro=E.SubElement(E.SubElement(d,'direction-type'),'metronome')
        E.SubElement(metro,'beat-unit').text='quarter';E.SubElement(metro,'per-minute').text=str(tempo)
        m.insert(list(m).index(m.find('note')),d)
    changes.append({'kind':'restore-direction','measure':number,'words':words,'tempo':tempo})
for m in measures:
    for barline in m.findall('barline'):
        for ending in barline.findall('ending'):
            changes.append({'kind':'false-repeat-ending','measure':int(m.get('number')),'number':ending.get('number')})
            barline.remove(ending)
    for d in list(m.findall('direction')):
        # OMR read printed system bar numbers as numeric words/rehearsal marks.
        labels=d.findall('direction-type/words')+d.findall('direction-type/rehearsal')
        if labels and all((x.text or '').strip().isdigit() for x in labels):
            m.remove(d);changes.append({'kind':'false-numeric-direction','measure':int(m.get('number'))})
        # Native source m99 has one p below the staff; the upper duplicate is
        # an OMR interpretation of the ornament/flat area above the note.
        elif m.get('number')=='99' and d.get('placement')=='above' and d.find('direction-type/dynamics/p') is not None:
            m.remove(d);changes.append({'kind':'false-upper-dynamic','measure':99,'symbol':'p','source':'one native Maestro p below staff'})

changes.extend(restore_vector_beams(PDF,root,evidence))
hairpins=restore_vector_wedges(PDF,root,evidence)
xml_path=OUT/'bangdi-reviewed.musicxml'
E.indent(root);E.ElementTree(root).write(xml_path,encoding='utf-8',xml_declaration=True)
issues=[];parsed=parse_part(xml_path,'bangdi','梆笛',issues)
manifest={'input':str(PDF),'inputSha256':digest(PDF),'cachedXml':str(CACHE/'corrected.musicxml'),
          'cachedXmlSha256':digest(CACHE/'corrected.musicxml'),'measures':len(parsed.measures),
          'sourceSystemAnchors':expected_anchors,'changes':changes,'sourceEvidence':evidence,
          'issues':[i.__dict__ for i in issues],'hairpins':hairpins,
          'scope':'Source PDF geometry verifies noteheads, diatonic pitches, local accidentals and grace pitches; rhythm/ornament/curve semantics still require full human proofread.'}
(OUT/'source-review.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'musicxml':str(xml_path),'sourceSystems':len(systems),'visibleMeasures':len(evidence),'changes':len(changes),'issues':[i.__dict__ for i in issues]},ensure_ascii=True))
