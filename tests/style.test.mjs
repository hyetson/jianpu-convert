import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveLayout} from '../dist/layout.js';
import {measureSpacing} from '../dist/rhythm.js';

test('partial overrides preserve omitted defaults and do not mutate other profiles',()=>{
  const custom=resolveLayout({fontSize:18,notation:{accidentalGap:1.2},context:{initialFontSize:20}});
  assert.equal(custom.notation.accidentalGap,1.2);
  assert.equal(custom.notation.upperDotGap,3);
  assert.equal(custom.context.initialFontSize,20);
  assert.equal(resolveLayout().notation.accidentalGap,.5);
  assert.equal(resolveLayout({fontSize:18}).context.initialFontSize,18);
  assert.equal(resolveLayout().maxMeasuresPerSystem,4);
  assert.equal(resolveLayout({maxMeasuresPerSystem:6}).maxMeasuresPerSystem,6);
});
test('reject malformed or misspelled configuration before writing a PDF',()=>{
  for(const options of [{fontSize:'14'},{notation:{dotRadius:-1}},{notation:{accidentalGap:NaN}},
    {notation:{accidentGap:1}},{spacing:{minimumCompressionRatio:1.1}},
    {spacing:{minimumBeatGapRatio:2}},{measureNumbers:{height:3}},{pageSize:'letter'},
    {maxMeasuresPerSystem:0},{notation:{toString:1}}]) assert.throws(()=>resolveLayout(options));
});
test('spacing overrides change usable width while respecting accidental ink clearance',()=>{
  const events=[0,.5,1,1.5,2,2.5,3,3.5].map((start,i)=>({id:String(i),start:String(start),duration:'.5',
    kind:'note',noteType:'eighth',dots:0,pitches:[{accidental:i===1 ? '1' : '0'}]}));
  const usual=measureSpacing(events,4,14);
  const profile=resolveLayout({spacing:{beatGapRatio:.9,columnWidthRatio:1.1}});
  assert.ok(measureSpacing(events,4,14,profile.spacing).width>usual.width);
  const clearance=measureSpacing(events,4,14,resolveLayout().spacing,p=>p.accidental==='1' ? 20 : 0);
  assert.ok(clearance.minimumColumns[0]>=14*.8+20);
});
