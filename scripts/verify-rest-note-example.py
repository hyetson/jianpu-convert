"""Verify the synthetic rest/note sample against its stated beat patterns."""
from pathlib import Path
from fractions import Fraction
import json

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'tmp/rest-note-example'
report=json.loads(Path((folder/'latest-run.txt').read_text(encoding='utf-8')).read_text(encoding='utf-8'))
assert report['errors']==report['warnings']==0
score=json.loads(Path(report['score']).read_text(encoding='utf-8'))
render=report['render']
assert render['pages']==1 and render['bars']==4
assert render['connectedUnderlineGroups']==15
assert len(render['underlineLayout'])==29
rests=0
for m in score['parts'][0]['measures']:
    assert sum(Fraction(e['duration']) for e in m['events'])==4
    rests+=sum(e['kind']=='rest' for e in m['events'])
    events={e['id']:e for e in m['events']}
    for line in (x for x in render['underlineLayout'] if x['bar']==m['number']):
        assert line['source']=='rest-beat'
        start,end=events[line['start']],events[line['end']]
        assert int(Fraction(start['start']))==int(Fraction(end['start']))
        assert all(int(Fraction(e['start']))==int(Fraction(start['start'])) for e in line['group'])
assert rests==20
result={'pages':1,'measures':4,'restsPreserved':rests,'beatGroups':15,'underlineSegments':29,'errors':0,'warnings':0}
(folder/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
