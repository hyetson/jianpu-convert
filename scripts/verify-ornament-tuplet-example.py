"""Check compact ornaments, text hierarchy and centered tuplet labels."""
from pathlib import Path
from fractions import Fraction
import json

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'tmp/ornament-tuplet-example'
report=json.loads(Path((folder/'latest-run.txt').read_text(encoding='utf-8')).read_text(encoding='utf-8'))
score=json.loads(Path(report['score']).read_text(encoding='utf-8'))
render=report['render']
assert report['errors']==report['warnings']==0
assert render['pages']==1 and render['bars']==4
tuplets=render['tupletLayout']
assert [(x['actual'],x['normal'],len(x['events'])) for x in tuplets]==[(3,2,3),(5,4,5),(3,2,2)]
for x in tuplets:
    assert x['font']=='music' and x['lineShape']=='curved' and abs(x['duration']-1)<1e-8
    assert abs((x['left']+x['right'])/2-(x['sx']+x['ex'])/2)<1e-8
assert len(render['curveSegments'])==4, 'three tuplet spans, including a reused slur, and one ordinary phrase'
ornaments=[x for x in render['annotationLayout'] if x.get('attachment')=='note' and 'baseBottom' in x]
assert len(ornaments)==4
for x in ornaments:
    assert 2-1e-8<=x['noteTop']-x['bottom']<=5+1e-8
trill=next(x for x in ornaments if x['kind']=='trill-mark')
words=next(x for x in render['directionLayout'] if x['text']=='C梆笛')
assert words['bottom']<=trill['top']-3
for m in score['parts'][0]['measures']:
    assert sum(Fraction(e['duration']) for e in m['events'])==4
result={'pages':1,'measures':4,'compactOrnaments':4,'tupletLabels':[3,5,3],'allExampleTupletDurations':1,'textAboveTrillAccidental':True,'errors':0,'warnings':0}
(folder/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
