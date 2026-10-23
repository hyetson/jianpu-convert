import test from 'node:test';
import assert from 'node:assert/strict';
import * as fontkit from 'fontkit';
import fs from 'node:fs';
import {fullMeasureRest,compressibleRest,restRunLength} from '../dist/rests.js';
import {resolveLayout} from '../dist/layout.js';

const rest=(number,extra={})=>({number:String(number),length:'4',beats:'4',beatType:4,fifths:0,mode:'major',implicit:false,
  events:[{voice:'1:1',kind:'rest',start:'0',duration:'4',marks:[]}],directions:[],barlines:[],...extra});
test('recognize full-bar rests regardless of source rest subdivision',()=>{
  assert.equal(fullMeasureRest(rest(1)),true);
  assert.equal(fullMeasureRest(rest(1,{events:Array.from({length:8},(_,i)=>({voice:'1:1',kind:'rest',start:String(i/2),duration:'.5',marks:[]}))})),true);
});
test('do not turn missing, partial, overlapping or pickup measures into full-bar rests',()=>{
  for(const measure of [undefined,rest(1,{events:[]}),rest(1,{implicit:true}),rest(1,{length:'3'}),
    rest(1,{events:[{voice:'1:1',kind:'rest',start:'1',duration:'3',marks:[]}]}),
    rest(1,{events:[{voice:'1:1',kind:'rest',start:'0',duration:'2',marks:[]},{voice:'1:1',kind:'rest',start:'1',duration:'3',marks:[]}]})])
    assert.equal(fullMeasureRest(measure),false);
});
test('count runs exactly and stop at context, numbering or notation boundaries',()=>{
  const bars=Array.from({length:8},(_,i)=>[rest(i+1)]);
  assert.equal(restRunLength(bars,0),8);
  const changed=structuredClone(bars);changed[3][0].fifths=1;
  assert.equal(restRunLength(changed,0),3);
  const missing=structuredClone(bars);missing[2]=[undefined];
  assert.equal(restRunLength(missing,0),2);
  const ending=structuredClone(bars);ending[2][0].barlines=[{style:'light-heavy'}];
  assert.equal(restRunLength(ending,0),3);
  assert.equal(compressibleRest(rest(1,{directions:[{kind:'rehearsal'}]})),false);
  assert.equal(compressibleRest(rest(1,{barlines:[{style:'regular',repeat:{direction:'backward'}}]})),false);
});
test('threshold is configurable and requires at least two measures',()=>{
  assert.equal(resolveLayout().rests.minimumMeasuresToCompress,4);
  assert.equal(resolveLayout({rests:{minimumMeasuresToCompress:6}}).rests.minimumMeasuresToCompress,6);
  assert.throws(()=>resolveLayout({rests:{minimumMeasuresToCompress:1}}));
  assert.throws(()=>resolveLayout({rests:{minimumMeasuresToCompress:3.5}}));
});

test('source rest groups and tempo changes retain their boundaries',()=>{
  const bars=Array.from({length:8},(_,i)=>[rest(i+1)]);
  bars[0][0].directions=[{kind:'words',start:'0'}];bars[4][0].sourceRestCount=4;
  assert.equal(restRunLength(bars,0),4);
  assert.equal(restRunLength(bars,4),4);
  bars[3][0].directions=[{kind:'metronome',start:'0'}];
  assert.equal(restRunLength(bars,0),3);
  const limited=Array.from({length:6},(_,i)=>[rest(i+1)]);limited[0][0].sourceRestCount=4;
  assert.equal(restRunLength(limited,0),4);
});
test('reference Maestro subsets together cover every decimal count digit',{
  skip: !['primary','five','eight'].every(name=>fs.existsSync(`tools/fonts/reference-maestro/counts-${name}.ttf`))
    && 'Optional local reference fonts are not redistributed'
},()=>{
  const faces=['primary','five','eight'].map(name=>fontkit.openSync(`tools/fonts/reference-maestro/counts-${name}.ttf`));
  for(let digit=0;digit<=9;digit++) assert.ok(faces.some(f=>f.hasGlyphForCodePoint(48+digit) && f.glyphForCodePoint(48+digit).path.commands.length));
});
