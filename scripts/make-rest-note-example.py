"""A synthetic 4/4 sample of rest/note duration lines; not an OMR result."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from jianpu.pipeline import build


def main():
    folder=ROOT/'tmp/rest-note-example'
    folder.mkdir(parents=True,exist_ok=True)
    # quarter = 4 units. None is an ordinary rest, not a missing event.
    patterns=[
        ('八分休止与音符：拍内相连', [(None,2),('C',2),('D',2),(None,2)]*2),
        ('十六分音符、休止、八分音符', [('C',1),(None,1),('E',2)]*4),
        ('休止、八分音符、休止：切分', [(None,1),('D',2),(None,1)]*4),
        ('附点、短休止与整拍休止', [(None,3),('C',1),('D',3),(None,1),(None,4),('E',2),(None,2)]),
    ]
    root=ET.Element('score-partwise',version='4.0')
    part_list=ET.SubElement(root,'part-list')
    spec=ET.SubElement(part_list,'score-part',id='P1')
    ET.SubElement(spec,'part-name').text='梆笛'
    part=ET.SubElement(root,'part',id='P1')
    for index,(label,pattern) in enumerate(patterns,1):
        m=ET.SubElement(part,'measure',number=str(index))
        if index==1:
            attributes=ET.fromstring('<attributes><divisions>4</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>')
            m.append(attributes)
        direction=ET.SubElement(m,'direction',placement='above')
        ET.SubElement(ET.SubElement(direction,'direction-type'),'words').text=label
        for step,duration in pattern:
            note=ET.SubElement(m,'note')
            if step is None:ET.SubElement(note,'rest')
            else:
                pitch=ET.SubElement(note,'pitch')
                ET.SubElement(pitch,'step').text=step
                ET.SubElement(pitch,'octave').text='4'
            ET.SubElement(note,'duration').text=str(duration)
            ET.SubElement(note,'voice').text='1'
            ET.SubElement(note,'type').text={1:'16th',2:'eighth',3:'eighth',4:'quarter'}[duration]
            if duration==3:ET.SubElement(note,'dot')
            # Include source metadata: explicit empty beams on other notes/rests
            # must not prevent their newly authorized mixed-beat grouping.
            if index==4 and step=='E':ET.SubElement(note,'beam',number='1').text='begin'
            if index==4 and step is None and duration==2:ET.SubElement(note,'beam',number='1').text='end'
    xml=folder/'rest-notes.musicxml'
    ET.ElementTree(root).write(xml,encoding='utf-8',xml_declaration=True)
    config=json.loads((ROOT/'configs/bangdi-full.json').read_text(encoding='utf-8'))
    config.update(title='休止符与音符 · 拍内合并示例',subtitle='人工构造排版样张 · 4/4 拍 · 减时线相连，时值与音符事件不变',composer='',
                  parts=[{'id':'rest-example','name':'梆笛','instrumentFamily':'wind'}],
                  output='output/jianpu/休止符与音符_拍内合并示例.pdf')
    config['layout'].update(fontSize=16,compressRests=False,maxMeasuresPerSystem=2,justifyLastSystem=True)
    config['layout']['spacing'].update(rowHeight=100,systemGap=40)
    config['layout']['terms']={'expressionSize':8}
    config_file=folder/'config.json'
    config_file.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    result=build(config_file,xml_inputs=[xml],overwrite=True)
    (folder/'latest-run.txt').write_text(result['report'],encoding='utf-8')
    print(json.dumps({key:result[key] for key in ('pdf','report','errors','warnings')},ensure_ascii=True))


if __name__=='__main__':main()
