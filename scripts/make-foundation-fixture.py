"""One manually verified bar plus labeled synthetic meter exercises.

This is not an OMR result. The real bar's note data was read from the original
PDF and deliberately excludes performance marks outside the current scope.
"""
from pathlib import Path
import json
import xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tmp/foundation'
OUT.mkdir(parents=True,exist_ok=True)


def add(parent,tag,value=None,**attrs):
    n=E.SubElement(parent,tag,attrs)
    if value is not None:n.text=str(value)
    return n


root=E.Element('score-partwise',version='4.0')
names=add(root,'part-list');p=add(names,'score-part',id='P1');add(p,'part-name','梆笛')
part=add(root,'part',id='P1')
data=[
    ('原谱第43小节 · 人工核对录入，仅基础音高/时值',4,4,[('C',5,36,'half',1,0),('B',4,3,'16th',0,0),('C',5,3,'16th',0,0),('G',4,3,'16th',0,1),('B',4,3,'16th',0,0)]),
    ('规则样例：4/4，四个四分音符',4,4,[(s,4,12,'quarter',0,0) for s in 'CDEF']),
    ('规则样例：2/4，四个八分音符',2,4,[(s,4,6,'eighth',0,0) for s in 'CDEF']),
    ('规则样例：3/8，三个八分音符',3,8,[(s,4,6,'eighth',0,0) for s in 'CDE']),
    ('规则样例：4/4，小节内降3→还原3',4,4,[('E',4,12,'quarter',0,-1),('E',4,12,'quarter',0,0),('F',4,12,'quarter',0,0),('G',4,12,'quarter',0,0)]),
]
for i,(label,beats,unit,notes) in enumerate(data,1):
    m=add(part,'measure',number=str(i));a=add(m,'attributes');add(a,'divisions',12)
    k=add(a,'key');add(k,'fifths',0)
    t=add(a,'time');add(t,'beats',beats);add(t,'beat-type',unit)
    c=add(a,'clef');add(c,'sign','G');add(c,'line',2)
    d=add(m,'direction');add(add(d,'direction-type'),'words',label)
    for step,octave,duration,kind,dots,alter in notes:
        n=add(m,'note');p=add(n,'pitch');add(p,'step',step);add(p,'octave',octave);add(p,'alter',alter)
        add(n,'duration',duration);add(n,'voice',1);add(n,'type',kind)
        for _ in range(dots):add(n,'dot')
        if alter:add(n,'accidental','sharp' if alter>0 else 'flat')
E.ElementTree(root).write(OUT/'single-voice.musicxml',encoding='utf-8',xml_declaration=True)
config={'title':'单声部基础规则核对','subtitle':'首小节为梆笛原谱第43小节人工录入；其余为规则样例',
        'parts':[{'id':'bangdi','name':'梆笛'}],'output':'output/jianpu/单声部基础规则核对.pdf',
        'pitchPolicy':'written','layout':{'fontSize':15,'margin':40,'compressRests':False,'maxMeasuresPerSystem':1},
        'fonts':{'text':'C:/Windows/Fonts/NotoSerifSC-VF.ttf','music':'tools/fonts/Bravura.otf'}}
(OUT/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
print(OUT)
