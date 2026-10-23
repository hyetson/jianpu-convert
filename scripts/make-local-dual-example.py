"""Create a synthetic MusicXML demonstrating local divisi, not OMR accuracy."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]


def note(m,step,duration,voice=1,chord=False,marks=()):
    n=ET.SubElement(m,'note')
    if chord:ET.SubElement(n,'chord')
    if step is None:ET.SubElement(n,'rest')
    else:
        p=ET.SubElement(n,'pitch');ET.SubElement(p,'step').text=step;ET.SubElement(p,'octave').text='4'
    ET.SubElement(n,'duration').text=str(duration)
    ET.SubElement(n,'voice').text=str(voice)
    ET.SubElement(n,'type').text={2:'eighth',4:'quarter',8:'half',16:'whole'}[duration]
    for tag,attrs in marks:
        notation=n.find('notations')
        if notation is None:notation=ET.SubElement(n,'notations')
        ET.SubElement(notation,tag,attrs)
    return n


def direction(m,kind,value,voice=None,offset=0,**attrs):
    d=ET.SubElement(m,'direction',placement='below' if kind in ('dynamics','wedge') else 'above')
    group=ET.SubElement(d,'direction-type')
    element=ET.SubElement(group,kind,attrs)
    if kind=='dynamics':ET.SubElement(element,value)
    elif kind=='wedge':element.set('type',value)
    else:element.text=value
    if offset:ET.SubElement(d,'offset').text=str(offset)
    if voice:ET.SubElement(d,'voice').text=str(voice)


def main():
    folder=ROOT/'tmp/local-dual-example';folder.mkdir(parents=True,exist_ok=True)
    root=ET.Element('score-partwise',version='4.0')
    specs=ET.SubElement(root,'part-list');spec=ET.SubElement(specs,'score-part',id='P1')
    ET.SubElement(spec,'part-name').text='演示乐器'
    part=ET.SubElement(root,'part',id='P1')
    words={1:'单声部',3:'同声部和弦 / 琶音',5:'局部双声部',7:'第二声部休止',8:'第二声部跨行连线',
           9:'双声部延续',10:'仅第一声部演奏',12:'第二声部单独演奏',14:'恢复单行：和弦仍在同一声部'}
    for bar in range(1,17):
        m=ET.SubElement(part,'measure',number=str(bar))
        if bar==1:m.append(ET.fromstring('<attributes><divisions>4</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>'))
        if bar in words:direction(m,'words',words[bar])
        if bar==5:direction(m,'dynamics','mf');direction(m,'dynamics','p',voice=2)
        if bar==8:direction(m,'wedge','crescendo',number='1')
        if bar==9:direction(m,'wedge','stop',offset=16,number='1')
        if bar in (3,14):
            for i,step in enumerate('CEG'):note(m,step,16,chord=i>0,marks=[('arpeggiate',{})] if i==0 else [])
        elif bar in (7,16):note(m,'G',16)
        elif bar in (12,13):note(m,None,16)
        else:
            steps='CDEG' if bar%2 else 'GFED'
            for step in steps:note(m,step,4)
        if bar in (5,6,7,8,9,12,13):
            ET.SubElement(ET.SubElement(m,'backup'),'duration').text='16'
            if bar in (7,13):note(m,None,16,2)
            else:
                pattern=[('E',8),('D',8)] if bar==5 else [(step,2) for step in 'ECDEGFED'] if bar==6 else [(step,4) for step in 'ECEG']
                for i,(step,duration) in enumerate(pattern):
                    marks=[]
                    if bar==8 and i==0:marks=[('slur',{'type':'start','number':'1'})]
                    if bar==9 and i==len(pattern)-1:marks=[('slur',{'type':'stop','number':'1'})]
                    note(m,step,duration,2,marks=marks)
        if bar==16:ET.SubElement(ET.SubElement(m,'barline',location='right'),'bar-style').text='light-heavy'
    xml=folder/'local-dual.musicxml'
    ET.ElementTree(root).write(xml,encoding='utf-8',xml_declaration=True)
    print(json.dumps({'musicxml':str(xml)},ensure_ascii=True))


if __name__=='__main__':main()
