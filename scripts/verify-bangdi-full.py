"""Verify source coverage, notation data and the published full-score artifact."""
from pathlib import Path
from collections import Counter,defaultdict
from fractions import Fraction
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'output/jianpu'
config=json.loads((ROOT/'configs/bangdi-full.json').read_text(encoding='utf-8'))
output=ROOT/config['output']
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=None
for folder in sorted((base/'runs').iterdir(),reverse=True):
    if not (folder/'report.json').exists():continue
    candidate=json.loads((folder/'report.json').read_text(encoding='utf-8'))
    if candidate.get('pdf')==str(output) and digest(folder/'rendered.pdf')==digest(output):
        report=candidate;break
assert report is not None
score=json.loads(Path(report['score']).read_text(encoding='utf-8'))
source=json.loads((base/'bangdi-full-source/source-review.json').read_text(encoding='utf-8'))
assert source['inputSha256']==digest(ROOT/'example/Silk Road 2012 - 梆笛.pdf')
assert report['errors']==report['warnings']==0
part=score['parts'][0]
assert len(score['parts'])==1
assert [m['number'] for m in part['measures']]==[str(i) for i in range(1,255)]
assert {e['voice'] for m in part['measures'] for e in m['events']}=={'1:1'}
lookup={int(m['number']):m for m in part['measures']}
for measure in source['sourceEvidence']:
    expected=Counter((n['small'],n['step'],n['octave'],str(n['alter'])) for n in measure['notes'])
    actual=Counter((e['kind']=='grace',p['step'],p['octave'],p['alter'])
                   for e in lookup[measure['measure']]['events'] for p in e['pitches'])
    assert expected==actual,measure['measure']
render=report['render']
assert render['singleVoice'] and render['rows']==1 and render['bars']==254
assert score['workflow']=='single-voice'
dynamics=[d for d in render['directionLayout'] if d['kind']=='dynamics']
assert len(dynamics)==16
for d in dynamics:
    assert d['placement']=='below'
    assert abs(d['top']-d['anchorBottom']-render['layoutResolved']['terms']['dynamicsGap'])<1e-8
    assert abs((d['left']+d['right'])/2-d['anchorX'])<1e-8
sf=next(d for d in dynamics if d['text']=='sf')
assert (sf['bar'],sf['start'],sf['sourcePlacement'])==('68','7/2','above')
assert sf['anchorEvent'] in {e['id'] for e in lookup[68]['events']}
assert all(abs(s['width']-515.28)<.01 for s in render['systemLayout'][:-1])
for index,system in enumerate(render['systemLayout'],1):
    bars=[m for m in render['measureLayout'] if m['system']==index]
    assert sum(m['meterWeight'] for m in bars)<=4+1e-8
for m in render['measureLayout']:
    length=sum(int(n) for n in m['beats'].split('+'))*4/m['beatType']
    assert abs(m['meterWeight']-(length+1)/5)<1e-8
    assert abs(m['idealWidth']-14*9*m['meterWeight'])<1e-8
assert any(len(s['bars'])>4 for s in render['systemLayout'])
assert 0<render['systemLayout'][-1]['width']<515.28
assert render['systemLayout'][-1]['spacingRatio']==1

assert [(m['bar'],m['beats'],m['beatType'],m['initial']) for m in render['meterLayout']]==[
    ('1','4',4,True),('85','2',4,False),('155','3',4,False),('156','4',4,False),('188','2',4,False),('236','4',4,False)]
assert all(m['format']=='fraction' and m['height']>2*14*.8 for m in render['meterLayout'])
assert all(d['font']=='music' for d in render['directionLayout'] if d['kind']=='dynamics')
assert all(d['font']=='term-bold' for d in render['directionLayout'] if d['text'] in ['Rubato','Moderato','piu mosso','presto'])
assert len([d for d in render['directionLayout'] if d['bar']=='99' and d['kind']=='dynamics'])==1
assert len(render['graceLayout'])==19
assert Counter(g['position'] for g in render['graceLayout'])=={'before':11,'after':8}
grace_groups=defaultdict(list)
for g in render['graceLayout']:
    assert Fraction(g['duration'])==0
    measure=next(m for m in part['measures'] if m['number']==g['bar'])
    anchor=next(e for e in measure['events'] if e['id']==g['anchor'])
    assert Fraction(g['start'])==Fraction(anchor['start'])+(Fraction(anchor['duration']) if g['position']=='after' else 0)
    assert g['measureLeft']<g['x'] and g['x']+14*.67*.7<g['measureRight']
    assert g['x']<g['anchorX'] if g['position']=='before' else g['x']>g['anchorX']
    grace_groups[g['anchor'],g['position']].append(g['event'])
for (anchor,position),ids in grace_groups.items():
    matches=[c for c in render['graceConnectors'] if c['anchor']==anchor and c['position']==position]
    assert len(matches)==1 and set(matches[0]['events'])==set(ids)
    c=matches[0]
    assert c['ex']>c['sx'] and c['ex']-c['sx']<14
    assert abs((c['sy'] if position=='before' else c['ey'])-c['graceBottom']-render['layoutResolved']['graces']['underlineGap'])<1e-8
    if position=='before':assert c['ey']>c['sy'] and c['ex']<c['principal']['left']
assert not any(c['kind']=='grace-slur' for c in render['curveSegments'])
assert all(d['bottom']-d['top']<=11 for d in render['directionLayout'] if d['kind']=='dynamics')
for d in render['directionLayout']:
    if d['kind']!='metronome-components':continue
    a,b=d['noteBox'],d['textBox']
    assert abs(a['bottom']-b['bottom'])<1e-8
    assert .55<(b['bottom']-b['top'])/(a['bottom']-a['top'])<.8

beam_heads=0
for measure in source['sourceEvidence']:
    events=lookup[measure['measure']]['events']
    for small in (False,True):
        groups=[]
        for head in (h for h in measure['notes'] if h['small']==small):
            if groups and abs(groups[-1][0]['x']-head['x'])<.1:groups[-1].append(head)
            else:groups.append([head])
        actual=[e for e in events if e['pitches'] and (e['kind']=='grace')==small]
        assert len(groups)==len(actual)
        for heads,event in zip(groups,actual):
            expected=[{'number':b['number'],'value':b['value']} for b in heads[0]['sourceBeams']]
            assert event['beams']==expected,(measure['measure'],event['id'])
            beam_heads+=len(heads)
    pending={}
    event_indices={e['id']:i for i,e in enumerate(events)}
    short_types={'eighth':1,'16th':2,'32nd':3,'64th':4,'128th':5}
    rest_beats={int(Fraction(e['start'])) for e in events if e['kind']=='rest' and e['noteType'] in short_types and
                not e['tuplet'] and Fraction(e['start'])+Fraction(e['duration'])<=int(Fraction(e['start']))+1}
    def covered(a,b,level):
        return any(s['bar']==str(measure['measure']) and s['level']==level and
                   event_indices[s['start']]<=event_indices[a['id']] and event_indices[s['end']]>=event_indices[b['id']]
                   for s in render['underlineLayout'])
    for event in events:
        for beam in event['beams'] or []:
            level=beam['number']-1
            if beam['value']=='begin':pending[level]=event['id']
            elif beam['value']=='end':
                start=pending.pop(level)
                stream=[e for e in events[event_indices[start]:event_indices[event['id']]+1]
                        if e['voice']==event['voice'] and (e['kind']=='grace')==(event['kind']=='grace')]
                # Check every original connection, allowing the newly requested
                # mixed rest/note beat boundary to split a source beam group.
                for a,b in zip(stream,stream[1:]):
                    different_beat=int(Fraction(a['start']))!=int(Fraction(b['start']))
                    split=(a['kind']!='grace' and different_beat and
                           (int(Fraction(a['start'])) in rest_beats or int(Fraction(b['start'])) in rest_beats))
                    if split:
                        assert not covered(a,b,level),(measure['measure'],'mixed beat crossed',a['id'],b['id'])
                    elif min(short_types.get(a['noteType'],0),short_types.get(b['noteType'],0))>level:
                        assert covered(a,b,level),(measure['measure'],level,a['id'],b['id'])
    assert not pending,(measure['measure'],pending)

mixed_groups={}
for segment in render['underlineLayout']:
    if segment['source']!='rest-beat':continue
    group=segment['group']
    key=(segment['bar'],tuple(e['id'] for e in group))
    mixed_groups[key]=group
    assert len({int(Fraction(e['start'])) for e in group})==1,key
    assert any(e['kind']=='rest' for e in group),key
    assert all(Fraction(a['start'])+Fraction(a['duration'])==Fraction(b['start']) for a,b in zip(group,group[1:])),key
    assert Fraction(group[-1]['start'])+Fraction(group[-1]['duration'])<=int(Fraction(group[0]['start']))+1,key

assert len(source['hairpins'])==5
for hairpin in source['hairpins']:
    segments=[w for w in render['wedgeSegments'] if w['start']['order']==hairpin['start']['measure']-1 and abs(w['start']['time']-float(Fraction(hairpin['start']['time'])))<1e-8]
    assert segments
    assert segments[0]['type']==hairpin['type']
    assert segments[-1]['end']['order']==hairpin['end']['measure']-1
    assert segments[-1]['end']['time']==float(Fraction(hairpin['end']['time']))
    assert segments[0]['startAbsolute']==float(Fraction(hairpin['start']['absolute']))
    assert segments[-1]['endAbsolute']==float(Fraction(hairpin['end']['absolute']))
    assert segments[0]['startOpening']==0 and segments[-1]['endOpening']==render['layoutResolved']['wedges']['height']
    for a,b in zip(segments,segments[1:]):
        assert a['endAbsolute']==b['startAbsolute'] and a['endOpening']==b['startOpening']

def curve_y(c,x):
    cubic=lambda a,b,d,e,t:(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*d+t**3*e
    lo=0;hi=1
    for _ in range(24):
        t=(lo+hi)/2
        if cubic(c['sx'],c['x1'],c['x2'],c['ex'],t)<x:lo=t
        else:hi=t
    return cubic(c['sy'],c['y1'],c['y2'],c['ey'],(lo+hi)/2)
for a in render['annotationLayout']:
    if a.get('attachment')=='note':
        if 'baseBottom' in a:
            assert -1e-8<=a['baseBottom']-a['bottom']<=render['layoutResolved']['techniques']['endpointLift']+1e-8
            assert a['noteTop']-a['bottom']>=render['layoutResolved']['techniques']['ornamentGap']-1e-8
        continue
    for c in render['curveSegments']:
        if (a['page'],a['system'],a['row'])!=(c['page'],c['system'],c['row']) or c['placement']=='below':continue
        left=max(a['left'],c['sx']);right=min(a['right'],c['ex'])
        if right<left:continue
        assert a['bottom']<=min(curve_y(c,left+(right-left)*i/8) for i in range(9))-render['layoutResolved']['curves']['annotationGap']+1e-6

ornament99=next(a for a in render['annotationLayout'] if a['event']==lookup[99]['events'][0]['id'] and a['kind']=='trill-mark')
words99=next(d for d in render['directionLayout'] if d['bar']=='99' and d['text']=='C梆笛')
assert words99['bottom']<=ornament99['top']-render['layoutResolved']['techniques']['textGap']
assert ornament99['ornamentAccidental']=='flat'
assert [(t['actual'],t['normal'],len(t['events'])) for t in render['tupletLayout']]==[(7,4,7),(6,4,6)]
for group,expected_duration in zip(render['tupletLayout'],(1,.5)):
    assert group['font']=='music' and group['lineShape']=='curved'
    assert abs((group['left']+group['right'])/2-(group['sx']+group['ex'])/2)<1e-8
    assert abs(group['duration']-expected_duration)<1e-8
for w in render['wedgeSegments']:
    for c in render['curveSegments']:
        if c['page']!=w['page'] or c['system']!=w['system']+1:continue
        left=max(w['sx'],c['sx']);right=min(w['ex'],c['ex'])
        if right<=left:continue
        for i in range(33):
            x=left+(right-left)*i/32
            opening=w['startOpening']+(w['endOpening']-w['startOpening'])*(x-w['sx'])/(w['ex']-w['sx'])
            assert abs(curve_y(c,x)-(w['sy']+opening/2))>2
            assert abs(curve_y(c,x)-(w['sy']-opening/2))>2
assert [(x['bar'],x['count']) for x in render['restLayout'] if x['style']=='multi-measure']==[
    ('1',14),('15',25),('49',8),('57',11),('80',5),('85',14),('132',8),('156',9),
    ('170',18),('188',5),('193',14),('207',5),('212',4)]
gaps=defaultdict(list)
for c in render['curveSegments']:
    assert abs(abs(c['sy']-c['startBound'])-abs(c['ey']-c['endBound']))<1e-8
    assert abs((c['y1']-(c['sy']+.3*(c['ey']-c['sy'])))-(c['y2']-(c['sy']+.7*(c['ey']-c['sy']))))<1e-8
    gaps[c['row'],c['kind'],c['start'],c['end'],c['lane']].append(c['endpointGap'])
assert all(max(values)-min(values)<1e-8 for values in gaps.values())
assert lookup[254]['barlines'][-1]['style']=='light-heavy'
result={'inputPdfSha256':source['inputSha256'],'outputPdfSha256':digest(output),'run':report['run'],
        'pages':render['pages'],'measures':254,'sourceSystems':21,'sourceVisibleMeasures':len(source['sourceEvidence']),
        'verifiedPitchHeads':sum(len(m['notes']) for m in source['sourceEvidence']),
        'verifiedBeamHeads':beam_heads,'sourceHairpins':len(source['hairpins']),'wedgeSegments':len(render['wedgeSegments']),
        'beforeGraceEvents':11,'afterGraceEvents':8,'meterChanges':len(render['meterLayout'])-1,
        'noteEvents':render['noteEvents'],'graceEvents':sum(e['kind']=='grace' for m in part['measures'] for e in m['events']),
        'errors':report['errors'],'warnings':report['warnings'],'pdf':str(output),'restNoteBeatGroups':len(mixed_groups),
        'verifiedLowerDynamics':len(dynamics),'dynamicsGap':render['layoutResolved']['terms']['dynamicsGap'],
        'scope':'Geometry/text-backed review plus machine checks; not a claim of complete human musical proofreading.'}
(base/'bangdi-full-source/full-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
