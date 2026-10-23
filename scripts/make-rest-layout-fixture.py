"""Synthetic 4/4 rest runs separated by short melodic measures."""
from pathlib import Path
import json
import xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tmp/rest-layout'
OUT.mkdir(parents=True,exist_ok=True)
def add(parent,tag,value=None,**attrs):
    node=E.SubElement(parent,tag,attrs)
    if value is not None:node.text=str(value)
    return node
root=E.Element('score-partwise',version='4.0')
entry=add(add(root,'part-list'),'score-part',id='P1');add(entry,'part-name','梆笛')
part=add(root,'part',id='P1')
number=0
for count in [1,2,3,4,8,11,25,0]:
    for silent in [False]+[True]*count:
        number+=1;measure=add(part,'measure',number=str(number))
        if number==1:
            attrs=add(measure,'attributes');add(attrs,'divisions',4);add(add(attrs,'key'),'fifths',0)
            time=add(attrs,'time');add(time,'beats',4);add(time,'beat-type',4)
            clef=add(attrs,'clef');add(clef,'sign','G');add(clef,'line',2)
        if silent:
            note=add(measure,'note');add(note,'rest',measure='yes');add(note,'duration',16)
            add(note,'voice',1);add(note,'type','whole')
        else:
            for step in 'CDEG':
                note=add(measure,'note');pitch=add(note,'pitch');add(pitch,'step',step);add(pitch,'octave',4)
                add(note,'duration',4);add(note,'voice',1);add(note,'type','quarter')
E.ElementTree(root).write(OUT/'rests.musicxml',encoding='utf-8',xml_declaration=True)
config=json.loads((ROOT/'configs/single-voice-layout.example.json').read_text(encoding='utf-8'))
config.update(title='4/4 空小节 · 排版样张',subtitle='模拟样例：1-3小节逐小节置0；4、8、11、25小节合并计数',output='output/jianpu/空小节_排版样张.pdf')
config['layout']['compressRests']=True
config['layout']['typography']['restCountSize']=20.5
config['layout']['rests']={'minimumMeasuresToCompress':4,'widthRatio':6,'minimumWidthRatio':5,
    'symbolInset':6,'lineWidth':2.2,'capHeight':10,'capWidth':1.3,'countGap':4,'countDigitGap':1.3,'zeroInset':8}
config['fonts']['restCounts']=[f'tools/fonts/reference-maestro/counts-{name}.ttf' for name in ('primary','five','eight')]
(OUT/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'{number} source measures: {OUT}')
