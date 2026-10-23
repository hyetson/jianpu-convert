"""Manually checked source excerpt plus synthetic connection fixtures. No OMR claim."""
from pathlib import Path
import json
import xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tmp/curve-layout'
OUT.mkdir(parents=True,exist_ok=True)

def add(parent,tag,value=None,**attrs):
    node=E.SubElement(parent,tag,attrs)
    if value is not None:node.text=str(value)
    return node

def score():
    root=E.Element('score-partwise',version='4.0')
    entry=add(add(root,'part-list'),'score-part',id='P1');add(entry,'part-name','梆笛')
    return root,add(root,'part',id='P1')

def measure(part,number,initial=False):
    m=add(part,'measure',number=str(number))
    if initial:
        attrs=add(m,'attributes');add(attrs,'divisions',4);add(add(attrs,'key'),'fifths',0)
        time=add(attrs,'time');add(time,'beats',4);add(time,'beat-type',4)
        clef=add(attrs,'clef');add(clef,'sign','G');add(clef,'line',2)
    return m

def note(m,step,octave=5,duration=4,kind='quarter',marks=(),dot=False,alter=0,grace=False):
    n=add(m,'note')
    if grace:add(n,'grace',slash='yes')
    if step=='rest':add(n,'rest')
    else:
        p=add(n,'pitch');add(p,'step',step)
        if alter:add(p,'alter',alter)
        add(p,'octave',octave)
    if not grace:add(n,'duration',duration)
    add(n,'voice',1);add(n,'type',kind)
    if dot:add(n,'dot')
    if marks:
        ns=add(n,'notations')
        for tag,attrs in marks:add(ns,tag,**attrs)
    return n

def mark(kind,type,number='1',**attrs):return kind,{'type':type,'number':number,**attrs}

def save(root,name,title,subtitle,max_bars):
    E.ElementTree(root).write(OUT/f'{name}.musicxml',encoding='utf-8',xml_declaration=True)
    config=json.loads((ROOT/'configs/single-voice-layout.example.json').read_text(encoding='utf-8'))
    config.update(title=title,subtitle=subtitle,output=f'output/jianpu/{title}.pdf')
    config['layout'].update(maxMeasuresPerSystem=max_bars,compressRests=False)
    (OUT/f'{name}.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')

root,part=score()
m=measure(part,44,True)
note(m,'C',duration=12,kind='half',dot=True)
note(m,'B',octave=4,duration=2,kind='eighth',marks=[mark('slur','start')])
note(m,'C',duration=2,kind='eighth')
m=measure(part,45);note(m,'D',duration=16,kind='whole')
m=measure(part,46)
note(m,'C',kind='eighth',grace=True)
note(m,'D',duration=16,kind='whole',marks=[mark('tied','start')])
m=measure(part,47)
note(m,'D',duration=2,kind='eighth',marks=[mark('tied','stop'),mark('slur','stop')])
note(m,'B',octave=4,duration=2,kind='eighth',marks=[mark('slur','start')])
for step in 'CDGF':note(m,step,duration=2,kind='eighth')
for step,alter in [('E',-1),('F',0),('E',-1),('C',0)]:note(m,step,duration=1,kind='16th',alter=alter)
m=measure(part,48)
note(m,'D',duration=12,kind='half',dot=True,marks=[mark('slur','stop')]);note(m,'rest')
save(root,'source-excerpt','梆笛_44-48小节_连线核对','人工录入核对片段；仅保留起止音均在片段内的完整连线',4)

root,part=score()
for i in range(1,13):
    m=measure(part,i,i==1)
    for j,step in enumerate('CDEG'):
        marks=[]
        if (i,j)==(1,0):marks=[mark('slur','start')]
        if (i,j)==(1,3):marks=[mark('slur','stop')]
        if (i,j)==(2,2):marks=[mark('slur','start')]
        if (i,j)==(4,1):marks=[mark('slur','stop')]
        if (i,j)==(5,0):marks=[mark('slur','start',placement='below')]
        if (i,j)==(5,3):marks=[mark('slur','stop')]
        if (i,j)==(6,1):marks=[mark('slur','start',placement='below')]
        if (i,j)==(7,2):marks=[mark('slur','stop')]
        if (i,j)==(8,0):marks=[mark('slur','start','2',**{'line-type':'dashed'})]
        if (i,j)==(9,3):marks=[mark('slur','stop','2')]
        if (i,j)==(10,2):marks=[mark('slur','start')]
        if (i,j)==(12,1):marks=[mark('slur','stop')]
        octave=3 if i in (5,6,7) else 4 if (i,j) in ((1,0),(4,1)) else 5
        note(m,step,octave=octave,marks=marks)
save(root,'synthetic','连线_排版样张','模拟样例：端点含高音点与普通音符，兼含跨行、上下方与虚线',4)
