"""Check local voice display and preservation of all source sounding events."""
from pathlib import Path
import hashlib
import json
from fractions import Fraction

ROOT=Path(__file__).resolve().parents[1]
output=ROOT/'output/jianpu/单乐器_局部双声部_排版示例.pdf'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=None
for folder in sorted((output.parent/'runs').iterdir(),reverse=True):
    path=folder/'report.json'
    if not path.is_file():continue
    candidate=json.loads(path.read_text(encoding='utf-8'))
    if candidate.get('pdf')==str(output) and digest(folder/'rendered.pdf')==digest(output):
        report=candidate;break
assert report is not None
score=json.loads(Path(report['score']).read_text(encoding='utf-8'))
r=report['render'];part=score['parts'][0]
assert score['workflow']=='local-dual-voice' and report['errors']==report['warnings']==0
assert len(score['parts'])==1 and r['rows']==2 and r['bars']==16
assert {v['bar'] for v in r['voiceLayout'] if v['dual']}=={'5','6','8','9'}
assert [s['visibleLanes'] for s in r['systemLayout']]==[1,2,2,1]
assert next(v for v in r['voiceLayout'] if v['bar']=='12' and v['voice']=='1:2')['lane']==1
assert next(v for v in r['voiceLayout'] if v['bar']=='12' and v['voice']=='1:1')['lane']==0
assert [v['text'] for v in r['voiceLabelLayout']]==[part['name']+'I',part['name']+'II']*2
for label in r['voiceLabelLayout']:
    assert label['right']<=label['musicLeft']-r['layoutResolved']['localVoices']['labelGap']+1e-8
for system in (2,3):
    for voice in ('1:1','1:2'):
        assert len({v['y'] for v in r['voiceLayout'] if v['system']==system and v['voice']==voice})==1
events={e['id']:e for m in part['measures'] for e in m['events']}
positions={p['event']:p for p in r['eventLayout']}
sounding={e['id'] for e in events.values() if e['kind']!='rest'}
assert sounding<=positions.keys(),sounding-positions.keys()
assert len(positions)==len(r['eventLayout'])
for bar in ('5','6','8','9'):
    m=next(m for m in part['measures'] if m['number']==bar)
    first=[e for e in m['events'] if e['voice']=='1:1']
    second=[e for e in m['events'] if e['voice']=='1:2']
    for a in first:
        for b in second:
            if Fraction(a['start'])==Fraction(b['start']):
                assert abs(positions[a['id']]['anchorX']-positions[b['id']]['anchorX'])<1e-8
assert len([d for d in r['directionLayout'] if d['text']=='mf'])==1
dynamic=next(d for d in r['directionLayout'] if d['text']=='p')
assert events[dynamic['anchorEvent']]['voice']=='1:2'
assert len([t for t in r['techniqueLayout'] if t['mode']=='vector-arpeggio'])==2
assert len(r['curveSegments'])==2
assert r['curveSegments'][0]['continuesRight'] and r['curveSegments'][1]['continuesLeft']
assert all(events[c['start']]['voice']==events[c['end']]['voice']=='1:2' for c in r['curveSegments'])
assert len(r['wedgeSegments'])==2
assert r['wedgeSegments'][0]['endAbsolute']==r['wedgeSegments'][1]['startAbsolute']
assert r['wedgeSegments'][0]['endOpening']==r['wedgeSegments'][1]['startOpening']
result={'run':report['run'],'pdf':str(output),'pdfSha256':digest(output),'pages':r['pages'],'bars':16,
        'localDualBars':[5,6,8,9],'pairedSystems':2,'voiceLabels':len(r['voiceLabelLayout']),'verifiedSoundingEvents':len(sounding),
        'verifiedPitchHeads':sum(len(events[e]['pitches']) for e in sounding),'arpeggios':2,
        'crossSystemSlurSegments':2,'wedgeSegments':2,'errors':0,'warnings':0,
        'scope':'Synthetic MusicXML layout verification, not PDF OMR accuracy.'}
(ROOT/'tmp/local-dual-example/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
