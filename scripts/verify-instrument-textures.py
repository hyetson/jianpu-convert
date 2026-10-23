"""Synthetic integration check: an explicit sheng profile, two streams, two chords."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from jianpu.single import prepare_config
from jianpu.pipeline import build


def main():
    folder=ROOT/'tmp/instrument-textures';folder.mkdir(parents=True,exist_ok=True)
    root=ET.Element('score-partwise',version='4.0')
    spec=ET.SubElement(ET.SubElement(root,'part-list'),'score-part',id='P1')
    ET.SubElement(spec,'part-name').text='高音笙'
    measure=ET.SubElement(ET.SubElement(root,'part',id='P1'),'measure',number='1')
    measure.append(ET.fromstring('<attributes><divisions>1</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>'))
    for voice,steps in [(1,'CEG'),(2,'DF')]:
        if voice==2:ET.SubElement(ET.SubElement(measure,'backup'),'duration').text='4'
        for i,step in enumerate(steps):
            note=ET.SubElement(measure,'note')
            if i:ET.SubElement(note,'chord')
            pitch=ET.SubElement(note,'pitch');ET.SubElement(pitch,'step').text=step;ET.SubElement(pitch,'octave').text='4'
            ET.SubElement(note,'duration').text='4';ET.SubElement(note,'voice').text=str(voice)
            ET.SubElement(note,'type').text='whole'
            ET.SubElement(ET.SubElement(note,'notations'),'arpeggiate',number=str(voice),direction='up')
    xml=folder/'two-voices-with-chords.musicxml'
    ET.ElementTree(root).write(xml,encoding='utf-8',xml_declaration=True)
    config,inputs=prepare_config(xml,folder/'integration.pdf',ROOT/'configs/dual-voice.json',
        workflow='local-dual-voice',instrument_name='高音笙',title='织体配置集成验证')
    config['parts'][0]['instrumentProfileId']='sheng-keyed'
    cfg=folder/'config.json';cfg.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    report=build(cfg,xml_inputs=inputs,overwrite=True)
    part=json.loads(Path(report['score']).read_text(encoding='utf-8'))['parts'][0]
    summary=part['textureSummary']
    assert report['errors']==report['warnings']==0
    assert part['instrumentProfile']['id']=='sheng-keyed' and part['instrumentFamily']=='wind'
    assert summary['hasConcurrentVoicesAndChordEvents'] and summary['voiceMeaning']=='unresolved'
    assert [d['maximumPitchesPerEvent'] for d in summary['voiceDetails']]==[3,2]
    assert report['render']['rows']==2 and len(report['render']['eventLayout'])==2
    arps=[t for t in report['render']['techniqueLayout'] if t['mode']=='vector-arpeggio']
    assert len(arps)==2 and {a['row'] for a in arps}=={0,1}
    result={'run':report['run'],'profile':'sheng-keyed','family':part['instrumentFamily'],
            'sourceStreams':summary['sourceStreams'],'hasConcurrentVoicesAndChordEvents':True,
            'chordSizes':[3,2],'separateArpeggios':2,'errors':0,'warnings':0,
            'scope':'Synthetic integration; no claim about real PDF recognition or universal playability.'}
    (folder/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
