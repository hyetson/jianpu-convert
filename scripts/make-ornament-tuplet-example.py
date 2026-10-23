"""Synthetic ornaments/text and tuplet-curve acceptance examples."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from jianpu.pipeline import build


def add(parent,tag,value=None,**attrs):
    node=E.SubElement(parent,tag,attrs)
    if value is not None:node.text=str(value)
    return node


def note(m,step='C',octave=5,duration=60,kind='quarter',ornament=None,slur=None,ratio=None,edge=None):
    n=add(m,'note');p=add(n,'pitch');add(p,'step',step);add(p,'octave',octave)
    add(n,'duration',duration);add(n,'voice',1);add(n,'type',kind)
    if ratio:
        mod=add(n,'time-modification');add(mod,'actual-notes',ratio[0]);add(mod,'normal-notes',ratio[1])
        for level in range(1,3 if kind=='16th' else 2):add(n,'beam',('begin' if edge=='start' else 'end' if edge=='stop' else 'continue'),number=str(level))
    notation=add(n,'notations')
    if slur:add(notation,'slur',type=slur,number='1')
    if edge:add(notation,'tuplet',type=edge,number='1',**{'line-shape':'curved'})
    if ornament:
        container=add(notation,'ornaments');add(container,ornament)
        if ornament=='trill-mark':add(container,'accidental-mark','flat',placement='above')
    return n


def main():
    folder=ROOT/'tmp/ornament-tuplet-example';folder.mkdir(parents=True,exist_ok=True)
    root=E.Element('score-partwise',version='4.0');parts=add(root,'part-list');sp=add(parts,'score-part',id='P1');add(sp,'part-name','梆笛')
    part=add(root,'part',id='P1')
    labels=['C梆笛','三连音：三个八分音符共一拍','五连音：五个十六分共一拍','三连音：混合时值，共一拍']
    for index,label in enumerate(labels,1):
        m=add(part,'measure',number=str(index))
        if index==1:
            m.append(E.fromstring('<attributes><divisions>60</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>'))
        direction=add(m,'direction',placement='above');add(add(direction,'direction-type'),'words',label)
        if index==1:
            note(m,'C',ornament='trill-mark',slur='start')
            note(m,'D',ornament='inverted-mordent')
            note(m,'E',octave=4,ornament='mordent')
            note(m,'G',octave=4,slur='stop',ornament='inverted-mordent')
        else:
            actual=5 if index==3 else 3
            durations=[40,20] if index==4 else [12]*5 if index==3 else [20]*3
            for i,duration in enumerate(durations):
                edge='start' if i==0 else 'stop' if i==len(durations)-1 else None
                note(m,'CDEFG'[i],duration=duration,kind='quarter' if duration==40 else '16th' if index==3 else 'eighth',
                     ratio=(actual,4 if actual==5 else 2),edge=edge,slur=edge if index==2 else None)
            note(m,'A');note(m,'G');note(m,'F')
    xml=folder/'ornaments-tuplets.musicxml';E.ElementTree(root).write(xml,encoding='utf-8',xml_declaration=True)
    config=json.loads((ROOT/'configs/bangdi-full.json').read_text(encoding='utf-8'))
    config.update(title='技法上标、文字与连音组',subtitle='人工构造校对样张 · 上标贴近音符 · 文字在上 · 连音数居中',composer='',
                  parts=[{'id':'example','name':'梆笛','instrumentFamily':'wind'}],output='output/jianpu/技法上标与连音组_排版示例.pdf')
    config['layout'].update(maxMeasuresPerSystem=2,compressRests=False,justifyLastSystem=True)
    config['layout']['spacing'].update(rowHeight=112,systemGap=40)
    config['layout']['terms']={'expressionSize':8}
    path=folder/'config.json';path.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    report=build(path,xml_inputs=[xml],overwrite=True)
    (folder/'latest-run.txt').write_text(report['report'],encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('pdf','report','errors','warnings')},ensure_ascii=True))


if __name__=='__main__':main()
