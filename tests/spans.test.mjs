import test from 'node:test';
import assert from 'node:assert/strict';
import {collectSpans,spanCurve,curveAvoidanceOffset} from '../dist/spans.js';
import {resolveLayout} from '../dist/layout.js';
import {collectWedges,wedgeOpening} from '../dist/wedges.js';

test('diminuendo pairs exact fractional offsets through continuation and variable meter',()=>{
  const direction=(text,start)=>({kind:'wedge',text,start,number:'2'});
  const measures=[{number:'1',length:'3/2',directions:[direction('diminuendo','1/2')]},
    {number:'2',length:'4',directions:[direction('continue','0'),direction('stop','2')]}];
  const result=collectWedges(measures,['1','2']);
  assert.deepEqual(result.warnings,[]);assert.equal(result.spans.length,1);
  const span=result.spans[0];assert.equal(span.start.absolute,.5);assert.equal(span.end.absolute,3.5);
  assert.equal(wedgeOpening(span,.5,8),8);assert.equal(wedgeOpening(span,2,8),4);assert.equal(wedgeOpening(span,3.5,8),0);
});
test('incomplete hairpins are reported without fabricating an end',()=>{
  const result=collectWedges([{number:'1',length:'4',directions:[{kind:'wedge',text:'crescendo',start:'0'}]}],['1']);
  assert.equal(result.spans.length,0);assert.equal(result.warnings.length,1);
});
const style=resolveLayout({}).curves;
const mark=(kind,type,extra={})=>({kind,type,...extra});
const event=(id,marks=[],step='C')=>({id,voice:'1:1',start:String(id),kind:'note',pitches:[{step,octave:4,alter:'0'}],marks});
const collect=events=>collectSpans([{number:'1',events}],'1:1',['1']);

test('slur continue retains one phrase, while a tie continue forms two pitch-specific ties',()=>{
  const r=collect([event(0,[mark('slur','start'),mark('tied','start')]),
    event(1,[mark('slur','continue'),mark('tied','continue')]),event(2,[mark('slur','stop'),mark('tied','stop')])]);
  assert.equal(r.warnings.length,0);
  assert.deepEqual(r.spans.map(s=>[s.kind,s.start,s.end]),[['tied',0,1],['slur',0,2],['tied',1,2]]);
});
test('ties cannot silently connect different pitches, and incomplete curves are omitted',()=>{
  const r=collect([event(0,[mark('tied','start')]),event(1,[mark('tied','stop')],'D')]);
  assert.equal(r.spans.length,0);assert.equal(r.warnings.length,2);
});

test('Audiveris continuation geometry on a start or system-break note does not restart the phrase',()=>{
  const r=collect([event(0,[mark('slur','start'),mark('slur','continue')]),
    event(1,[mark('slur','stop'),mark('slur','start'),mark('slur','continue')]),event(2,[mark('slur','stop')])]);
  assert.equal(r.warnings.length,0);assert.equal(r.spans.length,1);
  assert.equal(r.spans[0].start,0);assert.equal(r.spans[0].end,2);
});
test('chord ties use the marked member pitch, independently of other members',()=>{
  const a=event(0,[mark('tied','start',{pitchKey:'E4:0'})]);a.pitches.push({step:'E',octave:4,alter:'0'});
  const b=event(1,[mark('tied','stop',{pitchKey:'E4:0'})],'E');
  assert.equal(collect([a,b]).spans.length,1);
});
test('hidden marks do not draw and nested curves occupy separate lanes',()=>{
  const r=collect([event(0,[mark('slur','start')]),event(1,[mark('tied','start'),mark('slur','start',{number:'2',hidden:true})]),
    event(2,[mark('tied','stop'),mark('slur','stop',{number:'2',hidden:true})]),event(3,[mark('slur','stop')])]);
  assert.equal(r.warnings.length,0);assert.equal(r.spans.length,2);
  assert.equal(r.spans.find(s=>s.kind==='tied').lane,0);assert.equal(r.spans.find(s=>s.kind==='slur').lane,1);
});
const span={kind:'slur',start:'a',end:'b',from:0,to:2,startIndex:0,endIndex:5,placement:'above',lineType:'solid',lane:0};
const point=(x,sequence,order,top=100,bottom=114)=>({x,anchorX:x,sequence,order,top,bottom,row:0});
test('cross-line curves retain real endpoints and symmetric continuation segments, including intermediate systems',()=>{
  const first=spanCurve(span,new Map([['a',point(70,0,0)]]),0,0,0,40,550,100,114,style);
  assert.equal(first.sx,70);assert.equal(first.ex,538);assert.equal(first.continuesRight,true);
  assert.equal(first.sy,first.ey);assert.equal(first.y1,first.y2);assert.ok(first.y2<first.ey);
  const middle=spanCurve(span,new Map([['m',point(200,2,1)]]),0,1,1,40,550,100,114,style);
  assert.ok(middle.continuesLeft && middle.continuesRight);
  assert.equal(middle.sy,middle.ey);assert.equal(middle.y1,middle.y2);
  const last=spanCurve(span,new Map([['b',point(420,5,2)]]),0,2,2,40,550,100,114,style);
  assert.equal(last.sx,52);assert.equal(last.ex,420);assert.equal(last.continuesLeft,true);
  assert.equal(last.sy,last.ey);assert.equal(last.y1,last.y2);assert.ok(last.y1<last.sy);
  assert.equal(spanCurve(span,new Map(),0,3,4,40,550,100,114,style),undefined);
});
test('same-line endpoints align with digit centers; below curves clear low dots and retain style',()=>{
  const positions=new Map([['a',point(60,0,0,100,122)],['m',point(180,1,0,100,145)],['b',point(300,5,0,100,122)]]);
  const curve=spanCurve({...span,to:0,placement:'below',lineType:'dashed'},positions,0,0,0,40,550,100,114,style);
  assert.equal(curve.sx,60);assert.equal(curve.ex,300);assert.ok(curve.sy>=125.5);
  assert.ok(curve.y1>curve.sy && curve.y2>curve.ey);assert.equal(curve.lineType,'dashed');
  const mid=(curve.sy+3*curve.y1+3*curve.y2+curve.ey)/8;
  assert.ok(mid>=148.45,'curve must clear the middle low dot');
});

test('unequal endpoint bounds retain equal clearance and a balanced arch during collision avoidance',()=>{
  for(const placement of ['above','below']) {
    const positions=new Map([['a',point(60,0,0,100,122)],['m',point(95,1,0,45,175)],['b',point(300,5,0,82,135)]]);
    const curve=spanCurve({...span,to:0,placement,lane:1},positions,0,0,0,40,550,100,114,style);
    const midX=(curve.sx+curve.ex)/2;
    assert.ok(Math.abs(Math.abs(curve.sy-curve.startBound)-Math.abs(curve.ey-curve.endBound))<1e-9);
    const bezier=(a,b,c,d,t)=>(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d;
    for(const t of [0,.1,.25,.4,.5]) {
      const x=bezier(curve.sx,curve.x1,curve.x2,curve.ex,t),mirrorX=bezier(curve.sx,curve.x1,curve.x2,curve.ex,1-t);
      const y=bezier(curve.sy,curve.y1,curve.y2,curve.ey,t),mirrorY=bezier(curve.sy,curve.y1,curve.y2,curve.ey,1-t);
      const baseline=curve.sy+(curve.ey-curve.sy)*(x-curve.sx)/(curve.ex-curve.sx);
      const mirrorBaseline=curve.sy+(curve.ey-curve.sy)*(mirrorX-curve.sx)/(curve.ex-curve.sx);
      assert.ok(Math.abs(x+mirrorX-2*midX)<1e-9);
      assert.ok(Math.abs((y-baseline)-(mirrorY-mirrorBaseline))<1e-9);
    }
    // Check the off-center ornament too, after reaching the height cap and lifting.
    let lo=0,hi=1;
    for(let i=0;i<40;i++){const t=(lo+hi)/2;if(bezier(curve.sx,curve.x1,curve.x2,curve.ex,t)<95)lo=t;else hi=t;}
    const y=bezier(curve.sy,curve.y1,curve.y2,curve.ey,(lo+hi)/2);
    const gap=style.clearance+style.laneGap;
    assert.ok(placement==='above' ? y<=45-gap+.05 : y>=175+gap-.05);
  }
});

test('plain and upper-dotted note endpoints have the same gap in both pitch directions',()=>{
  for(const [startTop,endTop] of [[100,96],[96,100],[100,92],[92,100]]) {
    const positions=new Map([['a',point(60,0,0,startTop)],['b',point(300,5,0,endTop)]]);
    const curve=spanCurve({...span,to:0},positions,0,0,0,40,550,100,114,style);
    assert.equal(startTop-curve.sy,style.clearance);
    assert.equal(endTop-curve.ey,style.clearance);
    assert.equal(curve.ey-curve.sy,endTop-startTop);
    const base1=curve.sy+(curve.ey-curve.sy)*.3,base2=curve.sy+(curve.ey-curve.sy)*.7;
    assert.ok(Math.abs((curve.y1-base1)-(curve.y2-base2))<1e-9);
  }
});

test('overlapping curves can be separated without changing their endpoint clearance difference',()=>{
  const positions=new Map([['a',point(60,0,0)],['b',point(300,5,0)]]);
  const inner=spanCurve({...span,to:0},positions,0,0,0,40,550,100,114,style);
  const outer={...inner,sy:inner.sy+3,ey:inner.ey+3,y1:inner.y1+3,y2:inner.y2+3};
  const shift=curveAvoidanceOffset(outer,inner,5);
  assert.ok(shift>=7.99);
  const moved={...outer,sy:outer.sy-shift,ey:outer.ey-shift,y1:outer.y1-shift,y2:outer.y2-shift};
  assert.ok(curveAvoidanceOffset(moved,inner,5)<.001);
  assert.equal(moved.ey-moved.sy,outer.ey-outer.sy);
});
