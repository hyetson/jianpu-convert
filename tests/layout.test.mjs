import test from 'node:test';
import assert from 'node:assert/strict';
import {underlineGroups, measureSpacing, offsetAt,meterWidthRatio} from '../dist/rhythm.js';
import {contextChanges, planSystems} from '../dist/systems.js';
import {dynamicGlyph,metronomeGlyph,isTempoTerm} from '../dist/engraving.js';
import {collectTuplets,tupletDigits} from '../dist/tuplets.js';

const event=(id,start,duration,noteType,extra={})=>({id,start:String(start),duration:String(duration),noteType,kind:'note',dots:0,pitches:[{accidental:'0'}],...extra});
const groups=(events)=>underlineGroups(events,'4',4);

test('system planning reserves the paired voice labels only when that system needs them',()=>{
  const bars=Array.from({length:5},()=>({width:100,minimumWidth:100}));
  assert.deepEqual(planSystems(bars,400,4,false,indices=>indices.includes(2)?350:400),[[0,1,2],[3,4]]);
  assert.throws(()=>planSystems(bars,400,4,false,()=>0),/musical width/);
});

test('explicit mixed-value tuplets use source endpoints rather than a note count',()=>{
  const notes=[event('a',0,'2/3','quarter',{voice:'1',marks:[{kind:'tuplet',type:'start'}],tuplet:{actual:3,normal:2}}),
    event('b','2/3','1/3','eighth',{voice:'1',marks:[{kind:'tuplet',type:'stop'}],tuplet:{actual:3,normal:2}})];
  const result=collectTuplets([{number:'1',events:notes}],'1');
  assert.equal(result.warnings.length,0);assert.equal(result.groups.length,1);
  assert.deepEqual(result.groups[0].events,['a','b']);assert.equal(result.groups[0].actual,3);assert.equal(result.groups[0].duration,1);
  assert.equal(tupletDigits('3:2'),'\uE883\uE88A\uE882');
});
test('unmarked tuplet fallback requires a complete equal-duration group; ordinary slurs never become tuplets',()=>{
  const notes=Array.from({length:3},(_,i)=>event(String(i),String(i)+'/3','1/3','eighth',{voice:'1',marks:[],tuplet:{actual:3,normal:2}}));
  assert.equal(collectTuplets([{number:'1',events:notes}],'1').groups[0].source,'time-modification');
  const incomplete=collectTuplets([{number:'1',events:notes.slice(0,2)}],'1');
  assert.equal(incomplete.groups.length,0);assert.ok(incomplete.warnings.length);
  const plain=notes.map((e,i)=>({...e,tuplet:null,marks:i===0?[{kind:'slur',type:'start'}]:i===2?[{kind:'slur',type:'stop'}]:[]}));
  assert.equal(collectTuplets([{number:'1',events:plain}],'1').groups.length,0);
});

test('quiet measures follow meter duration: 2/4 is 60 percent and 3/4 is 80 percent',()=>{
  const spaced=length=>measureSpacing([event('n',0,length,length===4?'whole':'half')],length,14);
  assert.ok(Math.abs(spaced(2).width/spaced(4).width-.6)<1e-8);
  assert.ok(Math.abs(spaced(3).width/spaced(4).width-.8)<1e-8);
  assert.equal(meterWidthRatio(1.5),.5);
  const dense=measureSpacing(Array.from({length:8},(_,i)=>event(String(i),i/4,.25,'16th')),2,14);
  assert.ok(dense.width>dense.idealWidth);
  assert.ok(dense.minimumColumns.every(c=>c>=14*.8));
});
test('duration-aware packing admits six 2/4 bars in the space of four 4/4 bars',()=>{
  const short=Array.from({length:7},()=>({width:75.6,minimumWidth:65,meterWeight:.6}));
  assert.deepEqual(planSystems(short,515,4,true),[[0,1,2,3,4,5],[6]]);
  assert.deepEqual(planSystems(short,515,4,false),[[0,1,2,3],[4,5,6]]);
});

test('dynamics and tempo use dedicated music glyphs and preserve tempo spelling',()=>{
  assert.equal(dynamicGlyph('fp'),'\uE534');assert.equal(dynamicGlyph('fff'),'\uE530');assert.equal(dynamicGlyph('mp'),'\uE52C');
  assert.equal(metronomeGlyph('quarter'),'\uECA5');assert.ok(isTempoTerm('più mosso'));assert.ok(isTempoTerm('Allegro'));
});
test('after-graces reserve space after the principal without adding a beat column',()=>{
  const main=event('main',0,2,'half'),graces=[0,1,2,3].map(i=>event(`g${i}`,2,0,'16th',{kind:'grace',grace:{position:'after',anchorId:'main'}}));
  const plain=measureSpacing([main],2,14),spaced=measureSpacing([main,...graces],2,14);
  assert.deepEqual(spaced.times,plain.times);assert.ok(spaced.width>plain.width);
  assert.ok(spaced.graceOffsets.get('g0')>0 && spaced.graceOffsets.get('g3')>spaced.graceOffsets.get('g0'));
  assert.equal(spaced.graceTimes.get('g0'),1);
});

test('source beams cross beats and work in other meters; explicit standalone notes do not merge',()=>{
  const beam=value=>[{number:1,value}];
  const notes=[event('a',.5,.5,'eighth',{beams:beam('begin')}),event('b',1,.5,'eighth',{beams:beam('end')})];
  assert.equal(groups(notes).length,1);
  assert.equal(underlineGroups(notes,'3',8).length,1);
  assert.equal(groups(notes.map((e,i)=>({...e,start:String(i/2),beams:[]}))).length,2);
});
test('source sub-beams and boundaries override beat fallback',()=>{
  const notes=[0,.25,.5,.75].map((at,i)=>event(String(i),at,.25,'16th',{beams:[
    {number:1,value:i===0?'begin':i===3?'end':'continue'},
    {number:2,value:i%2===0?'begin':'end'}]}));
  assert.deepEqual(groups(notes)[0].segments,[{level:0,first:'0',last:'3'},{level:1,first:'0',last:'1'},{level:1,first:'2',last:'3'}]);
  notes.forEach((e,i)=>e.beams=[{number:1,value:i%2===0?'begin':'end'},{number:2,value:'forward hook'}]);
  assert.equal(groups(notes).length,2);
  assert.equal(groups(notes).flatMap(g=>g.segments).filter(s=>s.level===1 && s.first===s.last).length,4);
});
test('source can beam across a short rest without joining an unrelated group',()=>{
  const notes=[event('a',0,.25,'16th',{beams:[{number:1,value:'begin'}]}),event('r',.25,.25,'16th',{kind:'rest',beams:[],pitches:[]}),
    event('b',.5,.5,'eighth',{beams:[{number:1,value:'end'}]})];
  assert.equal(groups(notes).length,1);
  assert.deepEqual(groups(notes)[0].segments[0],{level:0,first:'a',last:'b'});
});
test('an intervening grace group does not interrupt a source main-note beam',()=>{
  const notes=[event('a',0,.5,'eighth',{beams:[{number:1,value:'begin'}]}),
    event('g1',.5,0,'16th',{kind:'grace',beams:[{number:1,value:'begin'},{number:2,value:'begin'}]}),
    event('g2',.5,0,'16th',{kind:'grace',beams:[{number:1,value:'end'},{number:2,value:'end'}]}),
    event('b',.5,.5,'eighth',{beams:[{number:1,value:'end'}]})];
  assert.deepEqual(groups(notes).map(g=>g.events.map(e=>e.id)),[['a','b'],['g1','g2']]);
});

test('four sixteenths share both duration lines',()=>{
  const notes=[0,.25,.5,.75].map((t,i)=>event(String(i),t,.25,'16th'));
  assert.deepEqual(groups(notes)[0].segments,[{level:0,first:'0',last:'3'},{level:1,first:'0',last:'3'}]);
  assert.deepEqual(groups(notes)[0].events,notes);
});
test('two eighths share one duration line',()=>assert.deepEqual(groups([event('a',0,.5,'eighth'),event('b',.5,.5,'eighth')])[0].segments,[{level:0,first:'a',last:'b'}]));
test('sixteenth-eighth-sixteenth has continuous first line and separate second lines',()=>assert.deepEqual(groups([event('a',0,.25,'16th'),event('b',.25,.5,'eighth'),event('c',.75,.25,'16th')])[0].segments,[{level:0,first:'a',last:'c'},{level:1,first:'a',last:'a'},{level:1,first:'c',last:'c'}]));
test('eighth followed by two sixteenths shares second line only on the pair',()=>assert.deepEqual(groups([event('a',0,.5,'eighth'),event('b',.5,.25,'16th'),event('c',.75,.25,'16th')])[0].segments,[{level:0,first:'a',last:'c'},{level:1,first:'b',last:'c'}]));
test('connections stop at each quarter beat',()=>assert.equal(groups([event('a',.5,.5,'eighth'),event('b',1,.5,'eighth')]).length,2));
test('rest and notes share each applicable underline within a beat',()=>{
  const mixed=[event('a',0,.25,'16th'),event('r',.25,.25,'16th',{kind:'rest',pitches:[]}),event('b',.5,.5,'eighth')];
  assert.deepEqual(groups(mixed).map(g=>g.events.map(e=>e.id)),[['a','r','b']]);
  assert.deepEqual(groups(mixed)[0].segments,[{level:0,first:'a',last:'b'},{level:1,first:'a',last:'r'}]);
});
test('rest at the start or end joins even with explicit standalone source metadata',()=>{
  const r=event('r',0,.5,'eighth',{kind:'rest',pitches:[],beams:[]}),n=event('n',.5,.5,'eighth',{beams:[]});
  assert.deepEqual(groups([r,n])[0].segments,[{level:0,first:'r',last:'n'}]);
  assert.deepEqual(groups([{...n,start:'0'},{...r,start:'.5'}])[0].segments,[{level:0,first:'n',last:'r'}]);
});
test('rest-note syncopation shares the first line and retains separate second-line hooks',()=>{
  const notes=[event('r1',0,.25,'16th',{kind:'rest',pitches:[],beams:[]}),event('n',.25,.5,'eighth',{beams:[]}),
    event('r2',.75,.25,'16th',{kind:'rest',pitches:[],beams:[]})];
  assert.deepEqual(groups(notes)[0].segments,[{level:0,first:'r1',last:'r2'},{level:1,first:'r1',last:'r1'},{level:1,first:'r2',last:'r2'}]);
});
test('mixed rest-note grouping stops at the beat, gaps, long rests and tuplets',()=>{
  const rest=extra=>event('r',0,.5,'eighth',{kind:'rest',pitches:[],beams:[],...extra});
  assert.equal(groups([rest({start:'.5'}),event('n',1,.5,'eighth',{beams:[]})]).length,2);
  assert.equal(groups([rest({duration:'.25',noteType:'16th'}),event('n',.5,.5,'eighth')]).length,2);
  assert.equal(groups([rest({duration:'1',noteType:'quarter'}),event('n',1,.5,'eighth')]).length,1);
  assert.equal(groups([rest({duration:'1/3',tuplet:{actual:3,normal:2}}),event('n','1/3','1/3','eighth',{tuplet:{actual:3,normal:2}})]).length,2);
});
test('source groups containing a short rest split at a beat boundary',()=>{
  const notes=[event('a',.5,.25,'16th',{beams:[{number:1,value:'begin'}]}),
    event('r',.75,.25,'16th',{kind:'rest',pitches:[],beams:[]}),event('b',1,.5,'eighth',{beams:[{number:1,value:'end'}]})];
  assert.deepEqual(groups(notes).map(g=>g.events.map(e=>e.id)),[['a','r'],['b']]);
});
test('short rest grouping follows simple and compound metrical beats',()=>{
  const notes=[event('r',0,.5,'eighth',{kind:'rest',pitches:[],beams:[]}),event('n',.5,.5,'eighth',{beams:[]})];
  assert.equal(underlineGroups(notes,'2',4).length,1);
  assert.equal(underlineGroups(notes,'3',8).length,2);
  assert.equal(underlineGroups([...notes,event('n2',1,.5,'eighth',{beams:[]})],'6',8).length,1);
});
test('gaps and overlaps do not merge',()=>{
  assert.equal(groups([event('a',0,.25,'16th'),event('b',.5,.25,'16th')]).length,2);
  assert.equal(groups([event('a',0,.5,'eighth'),event('b',.25,.5,'eighth')]).length,2);
});
test('tuplets and other meters retain standalone underlines',()=>{
  const notes=[event('a',0,'1/3','eighth',{tuplet:{actual:3,normal:2}}),event('b','1/3','1/3','eighth',{tuplet:{actual:3,normal:2}})];
  assert.equal(groups(notes).length,2);
  assert.equal(underlineGroups([event('a',0,.5,'eighth'),event('b',.5,.5,'eighth')],'3',8).length,2);
});
test('beat gap is wider than compact intra-beat spacing',()=>{
  const notes=[0,.25,.5,.75,1].map((t,i)=>event(String(i),t,.25,'16th'));
  const s=measureSpacing(notes,4,15);
  assert.ok(s.columns[3]>s.columns[0]);
  assert.ok(s.leftPadding>10 && s.rightPadding>10);
});
test('dense measures require more width than sparse measures',()=>{
  const dense=Array.from({length:16},(_,i)=>event(String(i),i/4,.25,'16th'));
  const sparse=Array.from({length:4},(_,i)=>event(String(i),i,1,'quarter'));
  assert.ok(measureSpacing(dense,4,15).width>measureSpacing(sparse,4,15).width);
});
test('accidentals and augmentation dots reserve space',()=>{
  const plain=[event('a',0,.5,'eighth'),event('b',.5,.5,'eighth')];
  const altered=[plain[0],{...plain[1],dots:1,pitches:[{accidental:'1'}]}];
  assert.ok(measureSpacing(altered,4,15).width>measureSpacing(plain,4,15).width);
});
test('long notes have timed continuation positions; directions interpolate',()=>{
  const s=measureSpacing([event('a',0,4,'whole')],4,15);
  assert.deepEqual(s.times,[0,1,2,3]);
  const points=s.times.map(t=>offsetAt(t,s.times,s.columns));
  assert.ok(points.every((p,i)=>i===0 || p>points[i-1]));
  assert.equal(offsetAt(.5,s.times,s.columns),s.columns[0]/2);
});
test('compact spacing still reserves accidentals, dots and beat separation',()=>{
  const notes=[event('a',0,.25,'16th'),event('b',.25,.75,'eighth',{dots:1,pitches:[{accidental:'1'}]}),event('c',1,1,'quarter')];
  const s=measureSpacing(notes,4,14);
  assert.ok(s.minimumColumns[0]>=14*(.8+.3));
  assert.ok(s.minimumColumns[1]>=14*(.8+.3+.28));
  assert.ok(s.minimumWidth<s.width);
});
test('moderate compression packs an additional measure',()=>{
  const bars=Array.from({length:5},()=>({width:100,minimumWidth:82}));
  assert.deepEqual(planSystems(bars,450,5),[[0,1,2,3,4]]);
});
test('default systems keep four measures instead of balancing the final short line',()=>{
  const bars=Array.from({length:9},()=>({width:110,minimumWidth:95}));
  const systems=planSystems(bars,450);
  assert.deepEqual(systems,[[0,1,2,3],[4,5,6,7],[8]]);
});
test('four-measure preference yields to readable widths and never drops oversized bars',()=>{
  const bars=Array.from({length:7},()=>({width:160,minimumWidth:120}));
  assert.deepEqual(planSystems(bars,450),[[0,1,2],[3,4,5],[6]]);
  assert.deepEqual(planSystems([{width:700,minimumWidth:600},...bars.slice(0,4)],450),[[0],[1,2,3],[4]]);
});
test('readability bounds and explicit measure limits are respected',()=>{
  const bars=Array.from({length:4},()=>({width:260,minimumWidth:240}));
  assert.ok(planSystems(bars,450).every(line=>line.length===1));
  assert.ok(planSystems(Array.from({length:8},()=>({width:70,minimumWidth:60})),450,2).every(line=>line.length<=2));
});
test('initial context prints both; unchanged context prints neither',()=>{
  const c={fifths:0,mode:'major',beats:'4',beatType:4};
  assert.deepEqual(contextChanges(undefined,c),{key:true,meter:true});
  assert.deepEqual(contextChanges(c,{...c}),{key:false,meter:false});
  assert.deepEqual(contextChanges(c,{...c,fifths:1}),{key:true,meter:false});
  assert.deepEqual(contextChanges(c,{...c,beats:'2'}),{key:false,meter:true});
});

test('grace clusters have distinct positions and reserve room before the principal note',()=>{
  const main=event('main',0,4,'whole');
  const graces=[event('g1',0,0,'16th',{kind:'grace'}),event('g2',0,0,'16th',{kind:'grace'}),event('g3',0,0,'16th',{kind:'grace'})];
  const result=measureSpacing([...graces,main],4,14),plain=measureSpacing([main],4,14);
  const positions=graces.map(e=>result.graceOffsets.get(e.id));
  assert.ok(positions[0]<positions[1] && positions[1]<positions[2] && positions[2]<0);
  assert.ok(result.leftPadding-plain.leftPadding>=-positions[0]-1e-9);
  assert.ok(positions[1]-positions[0]>14*.67*.7);
});
