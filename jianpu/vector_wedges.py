"""Map native vector hairpins to the already reviewed score's musical timeline."""
from fractions import Fraction
import xml.etree.ElementTree as E
import pdfplumber


def restore_vector_wedges(pdf,root,evidence):
    measures=root.findall('part/measure');lengths={};onsets={};absolute={};total=Fraction(0);beats=4;unit=4
    for m in measures:
        number=int(m.get('number'))
        if m.find('attributes/time') is not None:
            beats=int(m.findtext('attributes/time/beats'));unit=int(m.findtext('attributes/time/beat-type'))
        length=Fraction(beats*4,unit);lengths[number]=length;absolute[number]=total;total+=length
        cursor=Fraction(0);previous=cursor;times=[]
        for n in m.findall('note'):
            start=previous if n.find('chord') is not None else cursor
            if n.find('pitch') is not None and n.find('grace') is None:times.append(start)
            if n.find('grace') is None and n.find('chord') is None:
                previous=start;cursor+=Fraction(n.findtext('duration','0'))/336
        onsets[number]=times
    def locate(rows,x):
        edges=[]
        for r in rows:
            a,_,b,_=r['bounds'];number=r['measure']
            edges.extend([(abs(x-a),1,number,Fraction(0)),(abs(x-b),0,number,lengths[number])])
        nearest=min(edges)
        if nearest[0]<=7:
            _,_,number,time=nearest
            return {'measure':number,'time':str(time),'absolute':str(absolute[number]+time),'anchor':'barline'}
        r=next(r for r in rows if r['bounds'][0]<=x<=r['bounds'][2]);number=r['measure']
        heads=[n for n in r['notes'] if not n['small']]
        pairs=list(zip(heads,onsets[number]))
        assert pairs,(number,'hairpin endpoint has no musical anchor')
        head,time=min(pairs,key=lambda pair:abs(pair[0]['x']-x))
        assert abs(head['x']-x)<8,(number,x,head['x'])
        return {'measure':number,'time':str(time),'absolute':str(absolute[number]+time),'anchor':'note'}
    pieces=[]
    with pdfplumber.open(pdf) as document:
        for page_no,page in enumerate(document.pages,1):
            systems=sorted({r['system'] for r in evidence if r['page']==page_no})
            for system in systems:
                rows=[r for r in evidence if r['system']==system];bottom=rows[0]['bounds'][3]
                for c in page.curves:
                    if c['fill'] or len(c['pts'])!=3 or c['width']<8 or not 2<c['height']<14 or not bottom+4<(c['top']+c['bottom'])/2<bottom+50:continue
                    pts=c['pts'];left=[y for x,y in pts if abs(x-c['x0'])<.1];right=[y for x,y in pts if abs(x-c['x1'])<.1]
                    start_width=max(left)-min(left);end_width=max(right)-min(right)
                    pieces.append({'page':page_no,'system':system,'type':'crescendo' if end_width>start_width else 'diminuendo',
                                   'start':locate(rows,c['x0']),'end':locate(rows,c['x1']),'points':pts})
                lines=[l for l in page.lines if l['width']>20 and l['height']<10 and bottom+4<(l['top']+l['bottom'])/2<bottom+40]
                for i,a in enumerate(lines):
                    for b in lines[i+1:]:
                        if abs(a['x0']-b['x0'])>.1 or abs(a['x1']-b['x1'])>.1:continue
                        left=abs(a['pts'][0][1]-b['pts'][0][1]);right=abs(a['pts'][-1][1]-b['pts'][-1][1])
                        if min(left,right)<1 or max(left,right)>12:continue
                        pieces.append({'page':page_no,'system':system,'type':'continue','start':locate(rows,a['x0']),
                                       'end':locate(rows,a['x1']),'points':[a['pts'],b['pts']]})
    spans=[]
    for piece in sorted(pieces,key=lambda p:Fraction(p['start']['absolute'])):
        if piece['type']=='continue':
            assert spans and spans[-1]['end']['absolute']==piece['start']['absolute'],'Native continuation does not join previous hairpin'
            spans[-1]['end']=piece['end'];spans[-1]['pieces'].append(piece)
        else:spans.append({'type':piece['type'],'start':piece['start'],'end':piece['end'],'pieces':[piece]})
    for m in measures:
        for d in list(m.findall('direction')):
            for dt in d.findall('direction-type'):
                for wedge in dt.findall('wedge'):dt.remove(wedge)
            if all(not list(dt) for dt in d.findall('direction-type')):m.remove(d)
    for index,span in enumerate(spans,1):
        for endpoint,kind in ((span['start'],span['type']),(span['end'],'stop')):
            m=measures[endpoint['measure']-1];d=E.Element('direction',placement='below')
            E.SubElement(E.SubElement(d,'direction-type'),'wedge',type=kind,number=str(index))
            E.SubElement(d,'offset').text=str(int(Fraction(endpoint['time'])*336))
            m.insert(list(m).index(m.find('note')),d)
    return spans
