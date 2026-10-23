"""Generate an explicitly synthetic, reproducible three-family technique sample."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from jianpu.pipeline import build


def note(step='C', octave=4, duration=4, kind='quarter', marks='', dots=0, chord=False, beam=''):
    # Divisions = 4. No timbre/gesture is inferred from the note's pitch.
    return (f'<note>{"<chord/>" if chord else ""}<pitch><step>{step}</step><octave>{octave}</octave></pitch>'
            f'<duration>{duration}</duration><voice>1</voice><type>{kind}</type>{"<dot/>"*dots}'
            f'{beam}{marks}</note>')


def technical(value):
    return f'<notations><technical>{value}</technical></notations>'


def ornament(value):
    return f'<notations><ornaments>{value}</ornaments></notations>'


def quarters(first='', second='', third='', fourth=''):
    return ''.join(note(step=step, marks=mark) for step, mark in zip('CDEF', (first, second, third, fourth)))


def measure(number, label, content):
    attributes = ('<attributes><divisions>4</divisions><key><fifths>0</fifths></key>'
                  '<time><beats>4</beats><beat-type>4</beat-type></time>'
                  '<clef><sign>G</sign><line>2</line></clef></attributes>') if number == 1 else ''
    return (f'<measure number="{number}">{attributes}<direction placement="above"><direction-type>'
            f'<words>{label}</words></direction-type></direction>{content}</measure>')


def tremolo_pair():
    ratio = '<time-modification><actual-notes>2</actual-notes><normal-notes>1</normal-notes></time-modification>'
    return (note(duration=8, kind='whole', marks=ratio+ornament('<tremolo type="start">3</tremolo>')) +
            note('E', duration=8, kind='whole', marks=ratio+ornament('<tremolo type="stop">3</tremolo>')))


def main():
    target = ROOT / 'tmp/technique-example'
    target.mkdir(parents=True, exist_ok=True)
    staccato = '<notations><articulations><staccato/></articulations></notations>'
    single = ornament('<tremolo type="single">3</tremolo>')
    wind = [
        ('隐藏跳音；保留八度与附点', note(octave=5,duration=3,kind='eighth',dots=1,marks=staccato)+
         note('D',duration=1,kind='16th')+note('E',duration=4)+note('F',duration=8,kind='half')),
        ('双吐 / 三吐', quarters(technical('<double-tongue/>'),technical('<triple-tongue/>'))),
        ('花舌与震音分别保留', quarters(technical('<other-technical>花舌</other-technical>'),single)),
        ('颤指与上、下波音', quarters(ornament('<trill-mark/>'),ornament('<inverted-mordent/>'),ornament('<mordent/>'))),
        ('双吐含独立高音点', note(octave=5,marks=technical('<double-tongue/>'))+note('D')+note('E')+note('G')),
        ('换气与连线', note(marks='<notations><slur type="start" number="1"/></notations>')+note('D')+
         note('E',marks='<notations><slur type="stop" number="1"/></notations>')+
         note('F',marks='<notations><articulations><breath-mark/></articulations></notations>')),
        ('气震音不替换为 tr', quarters(technical('<other-technical>气震音</other-technical>'))),
        ('延长记号', note(duration=16,kind='whole',marks='<notations><fermata/></notations>')),
    ]
    bowed = [
        ('保留跳音；下弓 / 上弓', quarters(staccato,technical('<down-bow/>'),technical('<up-bow/>'))),
        ('自然泛音；空弦指法 0', quarters(technical('<harmonic><natural/></harmonic>'),technical('<fingering>0</fingering>'))),
        ('单音颤弓：三条斜线', note(duration=16,kind='whole',marks=single)),
        ('双音震音保留拍数', tremolo_pair()),
        ('揉弦保留原文', quarters(technical('<other-technical>滚揉</other-technical>'))),
        ('左手拨弦 / snap pizz.', quarters(technical('<left-hand-pizzicato/>'),technical('<snap-pizzicato/>'))),
        ('小号指法与音级分开', quarters(technical('<fingering>1</fingering>'),technical('<fingering>2</fingering>'),technical('<fingering>3</fingering>'),technical('<fingering>4</fingering>'))),
        ('连弓组保留原连线', note(marks='<notations><slur type="start" number="1"/></notations>')+note('D')+note('E')+
         note('G',marks='<notations><slur type="stop" number="1"/></notations>')),
    ]

    def arpeggio(direction=''):
        tag = f'<notations><arpeggiate{(" direction="+chr(34)+direction+chr(34)) if direction else ""}/></notations>'
        return ''.join(note(step, duration=16,kind='whole',marks=tag,chord=i>0) for i,step in enumerate('CEG'))

    plucked = [
        ('弹 / 挑：中文技法标注', quarters(technical('<other-technical>弹</other-technical>'),technical('<other-technical>挑</other-technical>'))),
        ('轮指：原文与震音分别保留', note(duration=16,kind='whole',marks='<notations><technical><other-technical>轮</other-technical></technical><ornaments><tremolo type="single">3</tremolo></ornaments></notations>')),
        ('琶音方向未指定', arpeggio()),
        ('上行琶音', arpeggio('up')),
        ('下行琶音', arpeggio('down')),
        ('扫 / 拂保留原文', quarters(technical('<other-technical>扫</other-technical>'),technical('<other-technical>拂</other-technical>'))),
        ('止音 / 全止音', quarters(technical('<damp/>'),technical('<damp-all/>'))),
        ('泛音圈与八度点分开', note(octave=5,duration=16,kind='whole',marks=technical('<harmonic><natural/></harmonic>'))),
    ]
    specs = [('wind','吹管示例','wind',wind),('bowed','拉弦示例','bowed',bowed),('plucked','弹拨示例','plucked',plucked)]
    xmls = []
    config = json.loads((ROOT/'configs/bangdi-full.json').read_text(encoding='utf-8'))
    config.update(title='民族乐器特殊技法转换示例', subtitle='人工构造验收样张 · 非原谱识别结果 · 上方小字为核对说明', composer='',
                  output='output/jianpu/民族乐器_特殊技法_转换示例.pdf',parts=[])
    config['layout']['spacing'].update(rowHeight=95,systemGap=40,baselineOffset=36)
    config['layout']['context']['initialOffsetY']=60
    config['layout']['maxMeasuresPerSystem']=4
    config['layout']['techniques']={'symbolSizeRatio':1,'textSize':8}
    config['layout']['terms']={'expressionSize':7}
    for part_id,name,family,bars in specs:
        xml = target/f'{part_id}.musicxml'
        body = ''.join(measure(i,label,content) for i,(label,content) in enumerate(bars,1))
        source = (f'<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>{name}</part-name></score-part></part-list>'
                  f'<part id="P1">{body}</part></score-partwise>')
        ET.fromstring(source)
        xml.write_text(source,encoding='utf-8')
        xmls.append(xml)
        config['parts'].append({'id':part_id,'name':name,'instrumentFamily':family})
    config_file=target/'config.json'
    config_file.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    result=build(config_file,xml_inputs=xmls,overwrite=True)
    (target/'latest-run.txt').write_text(result['report'],encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('pdf','report','errors','warnings')},ensure_ascii=False))


if __name__=='__main__':
    main()
