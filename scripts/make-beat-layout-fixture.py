"""4/4 layout exercises; final bar repeats manually verified source bar 43."""
from pathlib import Path
import json
import xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tmp/beat-layout'
OUT.mkdir(parents=True,exist_ok=True)
def add(parent,tag,value=None,**attrs):
    node=E.SubElement(parent,tag,attrs)
    if value is not None: node.text=str(value)
    return node

# Durations in divisions=4 (quarter=4); tuples: pitch, octave, duration, type, dots, alter.
def rhythm(durations,steps='CDEFGABC',octave=4):
    return [(steps[i%len(steps)],octave,d,{1:'16th',2:'eighth',3:'eighth',4:'quarter',8:'half',12:'half',16:'whole'}[d],int(d in (3,12)),0) for i,d in enumerate(durations)]
patterns=[
    rhythm([1,1,1,1,2,2,1,2,1,4]),
    rhythm([2,2,2,2,2,2,2,2]),
    rhythm([4,4,4,4]), rhythm([4,4,4,4],steps='GFED'),
    rhythm([4,4,4,4],steps='EFGA'), rhythm([4,4,4,4],steps='AGFE'),
    rhythm([1,2,1]*4),
    rhythm([1]*16),
    rhythm([2,1,1,1,1,2,3,1,4]),
    rhythm([8,4,4]), rhythm([16]),
    rhythm([2]*8,steps='CDEFGFED',octave=3),
    [('E',4,2,'eighth',0,-1),('E',4,2,'eighth',0,0)]+rhythm([1,1,1,1,4,4]),
    [('C',5,12,'half',1,0),('B',4,1,'16th',0,0),('C',5,1,'16th',0,0),('G',4,1,'16th',0,1),('B',4,1,'16th',0,0)],
]
root=E.Element('score-partwise',version='4.0')
names=add(root,'part-list'); spec=add(names,'score-part',id='P1');add(spec,'part-name','梆笛')
part=add(root,'part',id='P1')
for i,notes in enumerate(patterns,1):
    measure=add(part,'measure',number=str(i))
    if i==1:
        attr=add(measure,'attributes');add(attr,'divisions',4)
        add(add(attr,'key'),'fifths',0)
        time=add(attr,'time');add(time,'beats',4);add(time,'beat-type',4)
        clef=add(attr,'clef');add(clef,'sign','G');add(clef,'line',2)
    for step,octave,duration,kind,dots,alter in notes:
        note=add(measure,'note');pitch=add(note,'pitch')
        add(pitch,'step',step);add(pitch,'alter',alter);add(pitch,'octave',octave)
        add(note,'duration',duration);add(note,'voice',1);add(note,'type',kind)
        for _ in range(dots):add(note,'dot')
        if alter:add(note,'accidental','sharp' if alter>0 else 'flat')
E.ElementTree(root).write(OUT/'single-voice.musicxml',encoding='utf-8',xml_declaration=True)
config={'title':'4/4 单声部 · 拍内排版样张',
        'subtitle':'第1-13小节为排版练习；第14小节为原谱第43小节人工录入',
        'parts':[{'id':'bangdi','name':'梆笛'}], 'output':'output/jianpu/四四拍_初步拍内排版.pdf',
        'pitchPolicy':'written','layout':{'fontSize':14,'margin':40,'compressRests':False,'maxMeasuresPerSystem':4},
        'fonts':{'text':'C:/Windows/Fonts/NotoSerifSC-VF.ttf','numbers':'C:/Windows/Fonts/arialbd.ttf','music':'tools/fonts/Bravura.otf'}}
(OUT/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
print(OUT)
