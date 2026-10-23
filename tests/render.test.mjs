import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

function fixture() {
  const measures=Array.from({length:5},(_,i)=>({
    number:String(i+1),length:i>=3 ? '2' : '4',beats:i>=3 ? '2' : '4',beatType:4,
    fifths:i>=2 ? 1 : 0,mode:'major',implicit:false,synthetic:true,directions:[],barlines:[],
    events:Array.from({length:i>=3 ? 2 : 4},(_,j)=>({id:`${i}-${j}`,voice:'1:1',start:String(j),duration:'1',kind:'note',
      pitches:[{degree:1,octaveDots:0,accidental:'0',step:'C',octave:4,alter:'0'}],noteType:'quarter',dots:0,marks:[]}))
  }));
  return {title:'Context integration check',subtitle:'Synthetic fixture',composer:'',draft:false,recognitionSource:false,
    bars:measures.map(m=>m.number),parts:[{id:'P1',name:'梆笛',measures}],issues:[],
    fonts:{text:process.env.JIANPU_TEST_TEXT_FONT ?? 'C:/Windows/Fonts/NotoSerifSC-VF.ttf',music:path.resolve('tools/fonts/Bravura.otf')},
    layout:{fontSize:14,margin:40,compressRests:false,maxMeasuresPerSystem:1,justifyLastSystem:true}};
}

test('local dual passages share beat columns and keep surrounding measures on one lane',()=>{
  const score=fixture(),ms=score.parts[0].measures;
  for(const m of ms) {m.length='4';m.beats='4';m.beatType=4;}
  score.workflow='local-dual-voice';score.layout.maxMeasuresPerSystem=4;score.layout.fontSize=12;
  ms[0].events[0].pitches.push({...ms[0].events[0].pitches[0],degree:3});
  ms[0].events[0].marks=[{kind:'arpeggiate'}];
  for(const i of [1,2,3]) ms[i].events.push(...Array.from({length:8},(_,j)=>({...structuredClone(ms[0].events[1]),
    id:`second-${i}-${j}`,voice:'1:2',start:String(j/2),duration:'1/2',noteType:'eighth',marks:[]})));
  ms[1].events.find(e=>e.id==='second-1-0').pitches[0].degree=3;
  ms[1].events.find(e=>e.id==='second-1-0').marks=[{kind:'slur',type:'start'}];
  ms[2].events.find(e=>e.id==='second-2-7').marks=[{kind:'slur',type:'stop'}];
  for(const e of ms[3].events.filter(e=>e.voice==='1:1')) {e.kind='rest';e.pitches=[];}
  ms[1].directions=[{kind:'words',text:'One shared term',start:'0'},
    {kind:'dynamics',text:'p',start:'0',voice:'1:2',placement:'below'}];
  const r=renderFixture(score);
  assert.deepEqual(ms.map(m=>r.voiceLayout.filter(v=>v.bar===m.number).length),[1,2,2,2,1]);
  assert.deepEqual(r.systemLayout.map(s=>s.visibleLanes),[2,1]);
  assert.equal(r.voiceLayout.find(v=>v.bar==='4' && v.voice==='1:2').lane,1);
  assert.equal(r.voiceLayout.find(v=>v.bar==='4' && v.voice==='1:1').lane,0);
  assert.deepEqual(r.voiceLabelLayout.map(v=>v.text),['梆笛I','梆笛II']);
  assert.ok(r.voiceLabelLayout.every(v=>v.right<=v.musicLeft-r.layoutResolved.localVoices.labelGap+1e-8));
  for(const lane of [0,1]) assert.equal(new Set(r.voiceLayout.filter(v=>v.system===1 && v.lane===lane).map(v=>v.y)).size,1);
  const positions=new Map(r.eventLayout.map(e=>[e.event,e]));
  for(let beat=0;beat<4;beat++) assert.ok(Math.abs(positions.get(`1-${beat}`).anchorX-positions.get(`second-1-${beat*2}`).anchorX)<1e-8);
  assert.equal(r.directionLayout.filter(d=>d.text==='One shared term').length,1);
  assert.equal(r.directionLayout.find(d=>d.text==='p').anchorEvent,'second-1-0');
  assert.equal(r.techniqueLayout.filter(t=>t.mode==='vector-arpeggio').length,1);
  assert.ok(r.curveSegments.some(c=>c.start==='second-1-0' && c.end==='second-2-7'));
  assert.equal(r.eventLayout.filter(e=>e.event.startsWith('second-')).length,24);
  assert.equal(r.warnings.length,0);
  score.localVoices={primaryVoice:'1:2'};
  const reversed=renderFixture(score);
  assert.deepEqual(reversed.voiceLabelLayout.map(v=>v.voice),['1:2','1:1']);
  assert.ok(reversed.voiceLayout.filter(v=>v.voice==='1:2' && v.pairedSystem).every(v=>v.lane===0));
});

test('a one-voice score keeps its original layout in the local dual workflow',()=>{
  const score=fixture(),before=renderFixture(score);
  score.workflow='local-dual-voice';const after=renderFixture(score);
  assert.deepEqual(after.measureLayout,before.measureLayout);
  assert.deepEqual(after.systemLayout,before.systemLayout);
  assert.deepEqual(after.contextAnnotations,before.contextAnnotations);
  assert.equal(after.voiceLayout.length,5);
});

test('two simultaneous independent voices can each contain a chord and their own arpeggio',()=>{
  const score=fixture(),m=score.parts[0].measures[0];
  score.parts[0].measures=[m];score.parts[0].name='笙';score.parts[0].instrumentFamily='wind';
  score.workflow='local-dual-voice';score.bars=[m.number];
  for(const e of m.events) {
    e.pitches.push({...e.pitches[0],degree:3,step:'E'});
    if(e.start==='0') e.marks=[{kind:'arpeggiate',direction:'up'}];
  }
  m.events.push(...m.events.map(e=>({...structuredClone(e),id:'second-'+e.id,voice:'1:2',
    pitches:[{...e.pitches[0],degree:2,step:'D'},{...e.pitches[0],degree:4,step:'F'},{...e.pitches[0],degree:6,step:'A'}]})));
  const r=renderFixture(score),arps=r.techniqueLayout.filter(t=>t.mode==='vector-arpeggio');
  assert.equal(r.rows,2);assert.equal(r.noteEvents,8);assert.equal(r.eventLayout.length,8);
  assert.deepEqual(arps.map(a=>a.row),[0,1]);
  assert.ok(arps[1].bottom-arps[1].top>arps[0].bottom-arps[0].top);
  const positions=new Map(r.eventLayout.map(p=>[p.event,p]));
  for(const e of m.events.filter(e=>e.voice==='1:1')) {
    const a=positions.get(e.id),b=positions.get('second-'+e.id);
    assert.ok(Math.abs(a.anchorX-b.anchorX)<1e-8);assert.ok(b.y>a.y);
  }
  assert.deepEqual(r.voiceLabelLayout.map(v=>v.text),['笙I','笙II']);
  assert.equal(r.warnings.length,0);
});

test('wind display policy hides only staccato; octave/augmentation dots and tongue symbols survive',()=>{
  const score=fixture(),part=score.parts[0],events=part.measures[0].events;
  part.instrumentFamily='wind';
  events[0].pitches[0].octaveDots=1;events[0].marks=[{kind:'staccato'},{kind:'double-tongue'}];
  events[0].duration='3/4';events[0].noteType='eighth';events[0].dots=1;
  events[1].marks=[{kind:'triple-tongue'}];
  const report=renderFixture(score);
  assert.equal(report.techniqueLayout.filter(m=>m.action==='suppress' && m.reason==='wind-staccato-hidden').length,1);
  assert.ok(!report.annotationLayout.some(m=>m.kind==='staccato'));
  assert.ok(report.noteSymbols.some(m=>m.event==='0-0' && m.kind==='octave-dot'));
  assert.ok(report.noteSymbols.some(m=>m.event==='0-0' && m.kind==='augmentation-dot' && m.count===1));
  assert.deepEqual(report.techniqueLayout.filter(m=>['double-tongue','triple-tongue'].includes(m.kind)).map(m=>m.glyphCode).sort(),['e5f0','e5f2']);
  for(const family of ['bowed','plucked','unknown']) {
    part.instrumentFamily=family;
    assert.ok(renderFixture(score).annotationLayout.some(m=>m.kind==='staccato'),family);
  }
  part.instrumentFamily='wind';score.techniques={windStaccato:'show'};
  assert.ok(renderFixture(score).annotationLayout.some(m=>m.kind==='staccato'));
});

test('measured tremolos use strokes, pair double-note endpoints, and preserve cross-system continuation',()=>{
  const score=fixture(),measures=score.parts[0].measures;
  measures[0].events[0].marks=[{kind:'tremolo',label:'2',type:'single'}];
  measures[0].events[1].marks=[{kind:'tremolo',label:'3',type:'start'}];
  measures[1].events[1].marks=[{kind:'tremolo',label:'3',type:'stop'}];
  const report=renderFixture(score),single=report.techniqueLayout.find(m=>m.type==='single');
  assert.equal(single.strokes,2);assert.equal(single.mode,'vector-tremolo');
  const pair=report.techniqueLayout.filter(m=>m.type==='double').sort((a,b)=>a.system-b.system);
  assert.equal(pair.length,2);
  assert.deepEqual(pair.map(p=>[p.continuesLeft,p.continuesRight]),[[false,true],[true,false]]);
  assert.ok(pair.every(m=>m.start==='0-1' && m.end==='1-1' && m.strokes===3 && m.right>m.left));
  assert.ok(!report.techniqueLayout.some(m=>m.kind==='tremolo' && m.mode==='text'));
  assert.equal(report.warnings.length,0);
});

test('bowing/harmonic marks use separate glyphs; arpeggios deduplicate without inventing a direction',()=>{
  const score=fixture(),events=score.parts[0].measures[0].events;
  events[0].marks=[{kind:'down-bow'},{kind:'harmonic',harmonic:{kind:'natural'}}];
  events[1].marks=[{kind:'up-bow'},{kind:'snap-pizzicato'},{kind:'left-hand-pizzicato'}];
  events[2].pitches.push({...events[2].pitches[0],degree:3,step:'E'});
  events[2].marks=[{kind:'arpeggiate',number:'1'},{kind:'arpeggiate',number:'1'}];
  events[3].marks=[{kind:'other-technical',label:'弹'}];
  const report=renderFixture(score);
  const glyphs=new Set(report.techniqueLayout.filter(m=>m.mode==='music-glyph').map(m=>m.glyphCode));
  for(const code of ['e610','e612','e614','e631','e633']) assert.ok(glyphs.has(code),code);
  const arps=report.techniqueLayout.filter(m=>m.mode==='vector-arpeggio');
  assert.equal(arps.length,1);assert.equal(arps[0].direction,null);assert.ok(arps[0].bottom-arps[0].top>20);
  assert.ok(report.techniqueLayout.some(m=>m.kind==='other-technical' && m.label==='弹'));
  assert.equal(report.warnings.length,0);
});
test('last system keeps natural width unless explicitly justified',()=>{
  const score=fixture();score.layout.justifyLastSystem=false;
  const report=renderFixture(score);
  assert.ok(report.systemLayout.slice(0,-1).every(s=>Math.abs(s.width-515.28)<.01));
  assert.ok(report.systemLayout.at(-1).width<300);
});

test('renderer joins rest/note underlines per beat without altering rests or crossing the beat',()=>{
  const score=fixture(),m=score.parts[0].measures[0],template=m.events[0];
  const rest={...structuredClone(template),id:'r',start:'0',duration:'1/4',kind:'rest',pitches:[],noteType:'16th',beams:[]};
  m.events=[rest,{...structuredClone(template),id:'a',start:'1/4',duration:'1/2',noteType:'eighth',beams:[]},
    {...structuredClone(rest),id:'r2',start:'3/4'},
    {...structuredClone(template),id:'b',start:'1',duration:'3',noteType:'half'}];
  const report=renderFixture(score),lines=report.underlineLayout.filter(s=>s.bar==='1');
  assert.deepEqual(lines.map(s=>[s.level,s.start,s.end]),[[0,'r','r2'],[1,'r','r'],[1,'r2','r2']]);
  assert.ok(lines.every(s=>s.source==='rest-beat' && s.group.some(e=>e.kind==='rest')));
  assert.equal(lines[0].group.map(e=>Number(e.duration.split('/')[0])/Number(e.duration.split('/')[1] ?? 1)).reduce((a,b)=>a+b),1);
  assert.equal(report.warnings.length,0);
});
test('changed meters are fractions inside the changed measure, with protected musical space',()=>{
  const score=fixture();score.layout.maxMeasuresPerSystem=4;
  const report=renderFixture(score);
  assert.deepEqual(report.meterLayout.map(m=>[m.bar,m.beats,m.beatType,m.initial]),[['1','4',4,true],['4','2',4,false]]);
  const change=report.meterLayout[1];assert.equal(change.format,'fraction');
  assert.ok(change.height>2*14*.8 && change.height<2*14*.8*1.4);
  assert.ok(change.top>report.contextAnnotations.find(a=>a.bar==='4').y);
});
test('rendered mixed-meter widths keep the short-bar proportion after justification',()=>{
  const score=fixture();score.layout.maxMeasuresPerSystem=4;
  const measures=score.parts[0].measures.slice(0,4);
  measures.forEach((m,i)=>{
    m.length=m.beats=i>=2?'2':'4';m.events=[{...m.events[0],duration:m.length,noteType:i>=2?'half':'whole'}];
  });
  score.parts[0].measures=measures;score.bars=measures.map(m=>m.number);
  const report=renderFixture(score),[long,,short]=report.measureLayout;
  assert.ok(Math.abs(short.contentWidth/long.contentWidth-.6)<1e-8);
  assert.equal(report.systems,1);
});
test('dynamic glyphs, bold tempo terms and dotted metronome symbols reach the PDF',()=>{
  const score=fixture(),m=score.parts[0].measures[0];
  m.directions=[{start:'0',kind:'words',text:'Allegro'},{start:'0',kind:'metronome',text:'eighth=96',beatUnit:'eighth',beatDots:1,perMinute:'96'},
    ...['f','p','fp','fff','mp'].map((text,i)=>({start:String(i/2),kind:'dynamics',text}))];
  const report=renderFixture(score);
  assert.ok(report.directionLayout.filter(d=>d.kind==='dynamics').every(d=>d.font==='music'));
  assert.equal(report.directionLayout.find(d=>d.text==='Allegro').font,'Times-Bold');
  assert.ok(report.directionLayout.find(d=>d.kind==='metronome').left>report.directionLayout.find(d=>d.text==='Allegro').right);
  assert.ok(report.directionLayout.filter(d=>d.kind==='dynamics').every(d=>d.bottom-d.top<=14*1.1));
  const {noteBox,textBox}=report.directionLayout.find(d=>d.kind==='metronome-components');
  assert.ok(Math.abs(noteBox.bottom-textBox.bottom)<1e-8);
  assert.ok((textBox.bottom-textBox.top)/(noteBox.bottom-noteBox.top)>.55);
  assert.ok((textBox.bottom-textBox.top)/(noteBox.bottom-noteBox.top)<.8);
});
test('before and after grace groups fit with their principal and draw compact connectors',()=>{
  const score=fixture();score.layout.justifyLastSystem=false;
  const m=score.parts[0].measures[0],main={...m.events[0],id:'main',duration:'4',noteType:'whole',marks:[{kind:'grace-slur',type:'stop',number:'front'},{kind:'grace-slur',type:'start',number:'back'}]};
  const before={...m.events[0],id:'front',start:'0',duration:'0',kind:'grace',noteType:'eighth',grace:{position:'before',anchorId:'main'},marks:[{kind:'grace-slur',type:'start',number:'front'}]};
  const after={...before,id:'back',start:'4',grace:{position:'after',anchorId:'main'},marks:[{kind:'grace-slur',type:'stop',number:'back'}]};
  m.events=[before,main,after];score.parts[0].measures=[m];score.bars=['1'];
  const report=renderFixture(score);assert.equal(report.graceConnectors.length,2);
  assert.equal(report.curveSegments.filter(c=>c.kind==='grace-slur').length,0);
  for(const c of report.graceConnectors) {
    assert.ok(c.ex>c.sx && c.ex-c.sx<14);
    assert.equal(c.position==='before'?c.sy:c.ey,c.graceBottom+report.layoutResolved.graces.underlineGap);
    if(c.position==='before') assert.ok(c.ey>c.sy && c.ex<c.principal.left);
    else assert.ok(c.sx>c.principal.right);
  }
  const [a,b]=report.graceLayout;assert.ok(a.x<a.anchorX && b.x>b.anchorX);
  for(const g of report.graceLayout) assert.ok(g.x>g.measureLeft && g.x+14*.67*.7<g.measureRight);
  assert.equal(report.warnings.length,0);
});
test('hairpins retain timed endpoints; endpoint ornaments remain attached with a bounded lift',()=>{
  const score=fixture(),measures=score.parts[0].measures;
  score.layout.spacing={rowHeight:90,systemGap:40};
  measures[0].directions=[{kind:'wedge',text:'crescendo',start:'1/2',number:'1'}];
  measures[4].directions=[{kind:'wedge',text:'stop',start:'3/2',number:'1'}];
  measures[0].events[0].marks=[{kind:'slur',type:'start'},{kind:'trill-mark'}];
  measures[0].events[3].marks=[{kind:'slur',type:'stop'},{kind:'mordent'}];
  const report=renderFixture(score);
  assert.equal(report.wedgeSegments.length,5);
  assert.ok(new Set(report.wedgeSegments.map(w=>w.page)).size>1);
  assert.equal(report.wedgeSegments[0].start.time,.5);
  assert.equal(report.wedgeSegments.at(-1).end.time,1.5);
  assert.equal(report.wedgeSegments[0].startOpening,0);
  assert.equal(report.wedgeSegments.at(-1).endOpening,8);
  assert.ok(report.wedgeSegments.every(w=>w.ex-w.sx>22));
  for(let i=1;i<report.wedgeSegments.length;i++) assert.equal(report.wedgeSegments[i-1].endOpening,report.wedgeSegments[i].startOpening);
  for(const a of report.annotationLayout) if(a.attachment==='note') {
    assert.ok(a.baseBottom-a.bottom<=report.layoutResolved.techniques.endpointLift+1e-8);
    assert.ok(a.noteTop-a.bottom>=report.layoutResolved.techniques.ornamentGap);
  }
  assert.equal(report.warnings.length,0);
});

test('trill and mordent stay near their notes; words are placed above the ornament and its accidental',()=>{
  const score=fixture(),m=score.parts[0].measures[0];
  m.events[0].marks=[{kind:'trill-mark',ornamentAccidental:'flat'}];
  m.events[1].marks=[{kind:'slur',type:'start'}];
  m.events[2].marks=[{kind:'inverted-mordent'}];
  m.events[3].marks=[{kind:'slur',type:'stop'}];
  m.directions=[{start:'0',kind:'words',text:'C梆笛',placement:'above'}];
  const report=renderFixture(score),tr=report.annotationLayout.find(a=>a.kind==='trill-mark'),wave=report.annotationLayout.find(a=>a.kind==='inverted-mordent');
  for(const a of [tr,wave]) assert.ok(Math.abs(a.noteTop-a.bottom-2)<1e-8,'passing arches must not lift interior ornaments');
  const words=report.directionLayout.find(d=>d.text==='C梆笛');
  assert.ok(words.bottom<=tr.top-report.layoutResolved.techniques.textGap+1e-8);
});

test('lower dynamics center on their beat and sit just below underlines or low octave dots',()=>{
  const score=fixture(),m=score.parts[0].measures[0];
  m.events[0].noteType='16th';m.events[0].duration='1/4';m.events[0].pitches[0].octaveDots=-1;
  m.directions=[{start:'0',kind:'dynamics',text:'sf',placement:'above'},
    {start:'2',kind:'dynamics',text:'p',placement:'below'}];
  const report=renderFixture(score),dynamics=report.directionLayout.filter(d=>d.kind==='dynamics');
  for(const d of dynamics) {
    assert.equal(d.placement,'below');assert.ok(Math.abs(d.top-d.anchorBottom-4)<1e-8);
    assert.ok(Math.abs((d.left+d.right)/2-d.anchorX)<1e-8);
  }
  assert.equal(dynamics[0].sourcePlacement,'above');assert.equal(dynamics[0].anchorEvent,'0-0');
  const dots=report.noteSymbols.filter(s=>s.event==='0-0' && s.kind==='octave-dot');
  assert.ok(dynamics[0].top>dots[0].cy+1);
  score.layout.terms={dynamicsGap:7};
  assert.ok(Math.abs(renderFixture(score).directionLayout.find(d=>d.text==='sf').top-dynamics[0].top-3)<1e-8);
  score.dynamicsPlacement='source';
  assert.equal(renderFixture(score).directionLayout.find(d=>d.text==='sf').placement,'above');
  m.directions[0].text='custom dynamic';
  const custom=renderFixture(score).directionLayout.find(d=>d.text==='custom dynamic');
  assert.equal(custom.placement,'above');assert.ok(custom.bottom<custom.anchorBottom);
});

test('tuplet curves reuse identical slurs, center music numerals, and preserve the actual duration',()=>{
  const score=fixture(),m=score.parts[0].measures[0],source=m.events[0];
  m.events=Array.from({length:3},(_,i)=>({...structuredClone(source),id:`triplet-${i}`,start:`${i}/3`,duration:'1/3',noteType:'eighth',tuplet:{actual:3,normal:2},
    marks:i===0?[{kind:'tuplet',type:'start'},{kind:'slur',type:'start'}]:i===2?[{kind:'tuplet',type:'stop'},{kind:'slur',type:'stop'}]:[]}));
  m.events.push({...structuredClone(source),id:'tail',start:'1',duration:'3',noteType:'half'});
  const report=renderFixture(score);
  assert.equal(report.tupletLayout.length,1);assert.equal(report.curveSegments.length,1);
  const group=report.tupletLayout[0];
  assert.equal(group.label,'3');assert.equal(group.font,'music');assert.equal(group.duration,1);
  assert.ok(Math.abs((group.left+group.right)/2-(group.sx+group.ex)/2)<1e-8);
  assert.ok(!report.annotationLayout.some(a=>a.kind==='tuplet'));
  assert.equal(report.warnings.length,0);
});
function renderFixture(score) {
  fs.mkdirSync('tmp/layout-tests',{recursive:true});
  const folder=fs.mkdtempSync('tmp/layout-tests/context-');
  const input=path.join(folder,'score.json'),output=path.join(folder,'check.pdf');
  fs.writeFileSync(input,JSON.stringify(score));
  const run=spawnSync(process.execPath,['dist/render.js',input,output],{encoding:'utf8'});
  assert.equal(run.status,0,run.stderr);
  return JSON.parse(fs.readFileSync(output.replace('.pdf','.render.json'),'utf8'));
}
test('renderer fills every system and annotates only actual context changes',()=>{
  const report=renderFixture(fixture());
  assert.deepEqual(report.contextAnnotations.map(a=>[a.bar,a.text]),[['1','1=C  4/4'],['3','1=G'],['4','2/4']]);
  assert.equal(report.systems,5);
  assert.ok(report.systemLayout.every(s=>Math.abs(s.width-515.28)<.01 && s.fontSize===14));
  assert.equal(report.singleVoice,true);
  assert.equal(report.noteEvents,16);
  assert.equal(report.warnings.length,0);
});
test('custom profile changes actual context positions, font sizes and pagination',()=>{
  const score=fixture();
  score.fonts.numbers='C:/Windows/Fonts/arial.ttf';
  score.layout={...score.layout,fontSize:18,margin:50,
    spacing:{rowHeight:80,systemGap:40,baselineOffset:40},header:{firstSystemOffsetY:120},
    context:{initialFontSize:20,initialOffsetY:75,changeFontSize:10},
    notation:{accidentalGap:1.2,upperDotGap:4},measureNumbers:{fontSize:11,height:20}};
  const report=renderFixture(score);
  assert.equal(report.pages,2);
  assert.ok(report.systemLayout.every(s=>s.height===120 && s.fontSize===18 && Math.abs(s.width-495.28)<.01));
  assert.equal(report.contextAnnotations[0].fontSize,20);
  assert.equal(report.contextAnnotations[0].x,50);
  assert.equal(report.contextAnnotations[0].y,135);
  assert.equal(report.contextAnnotations[1].fontSize,10);
  assert.equal(report.noteEvents,16);
  assert.equal(report.warnings.length,0);
});
test('short rests remain four centered zeros; long rests preserve their exact measure counts',()=>{
  const score=fixture();
  const note=score.parts[0].measures[0];
  const measures=[];
  const add=(silent,count)=>{
    for(let i=0;i<count;i++) {
      const m=structuredClone(note);m.number=String(measures.length+1);
      if(silent) m.events=[{...m.events[0],id:`r-${m.number}`,kind:'rest',pitches:[],noteType:'whole',start:'0',duration:'4'}];
      measures.push(m);
    }
  };
  add(false,1);add(true,3);add(false,1);add(true,4);add(false,1);add(true,25);add(false,1);
  score.parts[0].measures=measures;score.bars=measures.map(m=>m.number);
  score.layout={fontSize:14,margin:40,compressRests:true,typography:{restCountSize:20.5}};
  score.fonts.restCounts=score.fonts.text;
  const report=renderFixture(score);
  assert.equal(report.bars,36);
  assert.deepEqual(report.restLayout.map(r=>[r.bar,r.count,r.style,r.zeros]),[
    ['2',1,'zeros',4],['3',1,'zeros',4],['4',1,'zeros',4],['6',4,'multi-measure',undefined],['11',25,'multi-measure',undefined]]);
  assert.equal(report.noteEvents,16);
  assert.equal(report.warnings.length,0);
  score.layout.rests={minimumMeasuresToCompress:8};
  const changed=renderFixture(score);
  assert.equal(changed.restLayout.filter(r=>r.style==='multi-measure' && r.count===4).length,0);
  assert.equal(changed.restLayout.filter(r=>Number(r.bar)>=6 && Number(r.bar)<=9 && r.style==='zeros').length,4);
  assert.equal(changed.restLayout.find(r=>r.style==='multi-measure')?.count,25);
});

test('renderer retains curve endpoints across both system and page breaks',()=>{
  const score=fixture();
  score.layout.spacing={rowHeight:90,systemGap:40};
  score.layout.curves={slurHeight:2,tieHeight:1,maximumHeight:2};
  const events=score.parts[0].measures.map(m=>m.events);
  events[0][0].marks=[{kind:'slur',type:'start',placement:'below',lineType:'dashed'}];
  events[4][1].marks=[{kind:'slur',type:'stop'}];
  events[0][1].marks=[{kind:'tied',type:'start'}];events[0][2].marks=[{kind:'tied',type:'stop'}];
  events[0][1].pitches[0].octaveDots=-2;
  score.fonts.measureNumbers=score.fonts.text;
  score.layout.measureNumbers={fontSize:18};
  const report=renderFixture(score);
  assert.equal(report.pages,2);assert.equal(report.warnings.length,0);
  const phrase=report.curveSegments.filter(c=>c.kind==='slur');
  assert.equal(phrase.length,5);assert.ok(phrase.every(c=>c.start==='0-0' && c.end==='4-1' && c.placement==='below' && c.lineType==='dashed'));
  assert.deepEqual(phrase.map(c=>[c.continuesLeft,c.continuesRight]),[[false,true],[true,true],[true,true],[true,true],[true,false]]);
  assert.equal(phrase.at(-1).page,2);
  assert.ok(phrase[0].endpointGap>report.layoutResolved.curves.clearance,'first segment must exercise extra collision clearance');
  assert.ok(phrase.every(c=>Math.abs(c.endpointGap-phrase[0].endpointGap)<1e-8),'a phrase must keep the same gap across systems and pages');
  const tie=report.curveSegments.find(c=>c.kind==='tied');assert.equal(tie.system,1);assert.equal(tie.continuesRight,false);
});
