"""Synthetic score for regression testing, never a transcription of user PDFs."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'tmp'/'jianpu-regression'
DEST.mkdir(parents=True,exist_ok=True)


def element(parent,name,value=None,**attrs):
    node=ET.SubElement(parent,name,attrs)
    if value is not None:node.text=str(value)
    return node


def add_note(m,step,octave,duration,kind='quarter',**options):
    n=element(m,'note')
    if options.get('chord'):element(n,'chord')
    if options.get('grace'):element(n,'grace')
    if step is None:element(n,'rest',measure='yes')
    else:
        p=element(n,'pitch');element(p,'step',step);element(p,'octave',octave)
        if options.get('alter'):element(p,'alter',options['alter'])
    if not options.get('grace'):element(n,'duration',duration)
    element(n,'voice',options.get('voice',1))
    element(n,'type',kind)
    if options.get('tuplet'):
        tm=element(n,'time-modification');element(tm,'actual-notes',3);element(tm,'normal-notes',2)
    if options.get('mark'):
        marks=element(n,'notations')
        if options['mark']=='trill-mark':element(element(marks,'ornaments'),'trill-mark')
        else:element(marks,options['mark'],type=options.get('mark_type',''),number='1')
    return n


for ix,label in enumerate(['梆笛','曲笛','新笛G']):
    root=ET.Element('score-partwise',version='4.0')
    part_list=element(root,'part-list');part_name=element(part_list,'score-part',id='P1');element(part_name,'part-name',label)
    part=element(root,'part',id='P1')
    for number in range(1,25):
        m=element(part,'measure',number=str(number))
        if number==1:
            a=element(m,'attributes');element(a,'divisions',12);k=element(a,'key');element(k,'fifths',0)
            t=element(a,'time');element(t,'beats',4);element(t,'beat-type',4)
            d=element(m,'direction');dt=element(d,'direction-type');element(dt,'words','测试谱，非原谱转换')
        if 2<=number<=5 or 14<=number<=16:add_note(m,None,4,48,'whole')
        elif number==6:
            for step in 'CDE':add_note(m,step,4+ix%2,4,'eighth',tuplet=True)
            add_note(m,'G',4,36,'half')
        elif number==7:
            for j,step in enumerate('CEG'):add_note(m,step,4,48,'whole',chord=j>0)
        elif number in (8,9):add_note(m,'A',4,48,'whole',mark='tied',mark_type='start' if number==8 else 'stop')
        elif number==10:
            add_note(m,'D',5,0,'16th',grace=True)
            for step in 'GABC':add_note(m,step,4,12)
        elif number==11:
            add_note(m,'F',4,24,'half',alter=1,mark='trill-mark');add_note(m,'G',4,24,'half')
        else:
            for step in ['C','D','E','F'] if ix==0 else ['E','F','G','A'] if ix==1 else ['G','A','B','C']:
                add_note(m,step,4+int(step=='C' and ix==2),12)
    ET.ElementTree(root).write(DEST/f'part-{ix+1}.musicxml',encoding='utf-8',xml_declaration=True)
config={'title':'三笛简谱 · 合成回归样例','subtitle':'仅验证转换与绘制，不是丝绸之路转谱结果',
        'parts':[{'id':f'p{i+1}','name':label} for i,label in enumerate(['梆笛','曲笛','新笛G'])],
        'output':'output/jianpu/合成回归样例.pdf','pitchPolicy':'written',
        'layout':{'fontSize':13,'margin':35,'compressRests':True},
        'fonts':{'text':'C:/Windows/Fonts/NotoSerifSC-VF.ttf','music':'tools/fonts/Bravura.otf'}}
(DEST/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
print(DEST)
