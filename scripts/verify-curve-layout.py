"""Check published sample geometry and the manually transcribed source endpoints."""
from pathlib import Path
from hashlib import sha256
import json
import pdfplumber

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/jianpu'

def matching_run(name):
    output=BASE/name
    digest=sha256(output.read_bytes()).digest()
    for folder in sorted((BASE/'runs').iterdir(),reverse=True):
        report_path=folder/'report.json'
        if not report_path.exists():continue
        report=json.loads(report_path.read_text(encoding='utf-8'))
        if report.get('pdf')==str(output) and sha256((folder/'rendered.pdf').read_bytes()).digest()==digest:
            return report,json.loads((folder/'score.json').read_text(encoding='utf-8'))
    raise AssertionError(f'No matching generation report: {output}')

def verify_curve_geometry(render):
    curves=render['curveSegments']
    phrase_gaps={}
    for c in curves:
        assert abs(abs(c['sy']-c['startBound'])-abs(c['ey']-c['endBound']))<1e-9
        base1=c['sy']+(c['ey']-c['sy'])*.3
        base2=c['sy']+(c['ey']-c['sy'])*.7
        assert abs((c['y1']-base1)-(c['y2']-base2))<1e-9
        assert abs(c['x1']+c['x2']-c['sx']-c['ex'])<1e-9
        key=(c['row'],c['kind'],c['start'],c['end'],c['lane'])
        if key in phrase_gaps:
            assert abs(phrase_gaps[key]-c['endpointGap'])<1e-8
        phrase_gaps[key]=c['endpointGap']
    return len(curves)

report,score=matching_run('梆笛_44-48小节_连线核对.pdf')
assert report['errors']==report['warnings']==0
geometry_count=verify_curve_geometry(report['render'])
synthetic_report,_=matching_run('连线_排版样张.pdf')
geometry_count+=verify_curve_geometry(synthetic_report['render'])
events={e['id']:(m['number'],i+1,e) for m in score['parts'][0]['measures'] for i,e in enumerate(m['events'])}
groups={}
for curve in report['render']['curveSegments']:
    groups.setdefault((curve['kind'],curve['start'],curve['end']),[]).append(curve)
assert len(groups)==3
actual=[]
for (kind,start,end),segments in groups.items():
    a,ai,ae=events[start];b,bi,be=events[end]
    pitch=lambda e:e['pitches'][0]['step']+str(e['pitches'][0]['octave'])
    actual.append((kind,a,ai,pitch(ae),b,bi,pitch(be),len(segments)))
    assert all(c['start']==start and c['end']==end for c in segments)
    if len(segments)==2:
        assert [(c['continuesLeft'],c['continuesRight']) for c in segments]==[(False,True),(True,False)]
    else:
        assert len(segments)==1 and not segments[0]['continuesLeft'] and not segments[0]['continuesRight']
assert set(actual)=={
    ('slur','44',2,'B4','47',1,'D5',1),
    ('tied','46',2,'D5','47',1,'D5',1), # grace C5 is event 1 of bar 46
    ('slur','47',2,'B4','48',1,'D5',2),
}

rest_report,_=matching_run('空小节_排版样张.pdf')
assert rest_report['errors']==rest_report['warnings']==0
with pdfplumber.open(BASE/'空小节_排版样张.pdf') as pdf:
    p=pdf.pages[0]
    bars=[l for l in p.lines if abs(l['linewidth']-2.2)<.01]
    assert len(bars)==4
    geometry=[]
    for line in bars:
        middle=line['top']
        bounds=[l for l in p.lines if abs(l['x0']-l['x1'])<.01 and abs(l['linewidth']-.7)<.01
                and l['top']<middle<l['bottom']]
        left=max(l['x0'] for l in bounds if l['x0']<line['x0'])
        right=min(l['x0'] for l in bounds if l['x0']>line['x1'])
        assert abs(line['x0']-left-6)<.01 and abs(right-line['x1']-6)<.01
        assert abs((line['x0']+line['x1'])/2-(left+right)/2)<.01
        assert all(abs((l['top']+l['bottom'])/2-middle)<.01 for l in bounds if l['x0'] in (left,right))
        geometry.append({'measureWidth':right-left,'restLineWidth':line['x1']-line['x0'],'inset':6})
    maestro=[c for c in p.chars if 'Maestro' in c['fontname']]
    for rect in p.rects:
        # pdfplumber gives the Maestro em box, taller than its visible digit ink.
        # Select by the positioned origin; visible centering is checked in PNGs.
        digits=[c for c in p.chars if c['x0']>=rect['x0']-.1 and c['x1']<=rect['x1']+.1
                and rect['top']-.1<=c['top']<=rect['bottom']+.1 and c['text'].isdigit()]
        assert digits and all('Maestro' in c['fontname'] for c in digits)
    boxed_count=rest_report['render']['systems']
    assert len(p.rects)==boxed_count
    assert len([c for c in p.chars if c['text']=='0' and 'Arial' in c['fontname']])==24
    expected_digits=sum(len(s['bars'][0]) for s in rest_report['render']['systemLayout'])+sum(
        len(str(r['count'])) for r in rest_report['render']['restLayout'] if r['style']=='multi-measure')
    assert len(maestro)==expected_digits
result={'sourceConnections':actual,'curveSegments':len(report['render']['curveSegments']),
        'equalGapBalancedSegments':geometry_count,'restGeometry':geometry,'boxedNumbersFont':'Maestro','shortRestZeros':24}
out=ROOT/'tmp/curve-layout/geometry-verification.json'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'verifiedConnections':3,'equalGapBalancedSegments':geometry_count,'verifiedRestBars':4,'verifiedBoxedNumbers':boxed_count,'report':str(out)}))
