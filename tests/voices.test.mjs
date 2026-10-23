import test from 'node:test';
import assert from 'node:assert/strict';
import {localVoiceRows} from '../dist/voices.js';

const note=(voice,kind='note',marks=[])=>({voice,kind,marks});
const rows=(events,required=[],directions=[])=>localVoiceRows({events,directions},['1:1','1:2'],'1:1',required);
test('local lanes distinguish a multi-pitch chord from independent source voices',()=>{
  assert.deepEqual(rows([{...note('1:1'),pitches:[1,3,5]}]),['1:1']);
  assert.deepEqual(rows([note('1:1'),note('1:2')]),['1:1','1:2']);
});
test('resting second voices fold, but explicit marks, scoped directions and continuing spans retain them',()=>{
  const events=[note('1:1'),note('1:2','rest')];
  assert.deepEqual(rows(events),['1:1']);
  assert.deepEqual(rows(events,['1:2']),['1:1','1:2']);
  assert.deepEqual(rows(events,[],[{voice:'1:2'}]),['1:1','1:2']);
  assert.deepEqual(rows([events[0],note('1:2','rest',[{kind:'fermata'}])]),['1:1','1:2']);
});
test('solo secondary voice and all-rest bars use one lane without inventing notes',()=>{
  assert.deepEqual(rows([note('1:1','rest'),note('1:2')]),['1:2']);
  assert.deepEqual(rows([note('1:1','rest'),note('1:2','rest')]),['1:1']);
  assert.deepEqual(localVoiceRows({events:[note('1:1'),note('1:2')],directions:[]},['1:1','1:2'],'1:2'),['1:2','1:1']);
});
