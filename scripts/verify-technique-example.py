"""Check symbol policy against source semantics and generated layout reports."""
from collections import Counter
from fractions import Fraction
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]


def load_report(path):
    report=json.loads(path.read_text(encoding='utf-8'))
    score=json.loads(Path(report['score']).read_text(encoding='utf-8'))
    assert report['errors']==report['warnings']==0
    return score,report['render']


sample_path=Path((ROOT/'tmp/technique-example/latest-run.txt').read_text(encoding='utf-8'))
score,render=load_report(sample_path)
assert render['pages']==2 and render['rows']==3 and render['bars']==8
tech=render['techniqueLayout']
assert len([m for m in tech if m.get('reason')=='wind-staccato-hidden'])==1
assert [m['row'] for m in render['annotationLayout'] if m['kind']=='staccato']==[1]
assert {m['glyphCode'] for m in tech if m.get('mode')=='music-glyph'} >= {
    'e5f0','e5f2','e610','e612','e614','e631','e633','e638','e639'}
arps=[m for m in tech if m.get('mode')=='vector-arpeggio']
assert len(arps)==3 and {m['direction'] for m in arps}=={None,'up','down'}
assert all(m['bottom']-m['top']>40 for m in arps)
tremolos=[m for m in tech if m.get('mode')=='vector-tremolo']
assert Counter(m['type'] for m in tremolos)=={'single':3,'double':1}
assert all(m['strokes']==3 for m in tremolos)
assert not any(m['kind']=='tremolo' and m.get('mode')=='text' for m in tech)
assert {'弹','挑','扫','拂','轮','花舌','气震音','滚揉'} <= {m.get('label') for m in tech}
for part in score['parts']:
    for bar in part['measures']:
        assert sum(Fraction(e['duration']) for e in bar['events'])==4
        for e in bar['events']:
            for m in e['marks']:
                if m['kind']=='tremolo' and m['type'] in ('start','stop'):
                    assert e['tuplet'] is None and e['timeModification']=={'actual':2,'normal':1}
                if m['kind']=='staccato':assert '<staccato' in m['sourceXml']
assert len([m for m in render['noteSymbols'] if m['kind']=='octave-dot'])==3
assert sum(m.get('count',0) for m in render['noteSymbols'] if m['kind']=='augmentation-dot')==1

full_run=Path((ROOT/'tmp/bangdi-full/latest-run.txt').read_text(encoding='utf-8'))
full,full_render=load_report(full_run/'report.json')
assert full['parts'][0]['instrumentFamily']=='wind'
events=[e for p in full['parts'] for bar in p['measures'] for e in bar['events']]
staccato=sum(m['kind']=='staccato' and not m.get('hidden') for e in events for m in e['marks'])
suppressed=[m for m in full_render['techniqueLayout'] if m.get('reason')=='wind-staccato-hidden']
assert staccato==len(suppressed)==53
assert not any(m['kind']=='staccato' for m in full_render['annotationLayout'])
expected_octaves=sum(min(5,abs(p['octaveDots'])) for e in events for p in e['pitches'])
assert sum(m['kind']=='octave-dot' for m in full_render['noteSymbols'])==expected_octaves
result={'samplePages':2,'sampleRun':sample_path.parent.name,'fullRun':full_run.name,
        'fullPages':full_render['pages'],'fullMeasures':len(full['bars']),
        'windStaccatoHidden':staccato,'octaveDotsPreserved':expected_octaves,
        'errors':0,'warnings':0}
(ROOT/'tmp/technique-example/verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
