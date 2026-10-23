import {quarters} from './rhythm.js';
import type {Style} from './layout.js';
import type {TupletGroup} from './tuplets.js';
export interface SpanMark {kind:string;type?:string;number?:string;placement?:string;lineType?:string;pitchKey?:string;hidden?:boolean}
interface SpanEvent {id:string;voice:string;start:string;kind:string;pitches:{step:string;octave:number;alter:string}[];marks:SpanMark[];grace?:{anchorId:string}|null}
export interface Span {kind:string;start:string;end:string;from:number;to:number;startIndex:number;endIndex:number;placement:string;lineType:string;lane:number;tuplet?:TupletGroup}
export function collectSpans(measures:{number:string;events:SpanEvent[]}[],voice:string,bars:string[]) {
  const pending=new Map<string,Omit<Span,'end'|'to'|'endIndex'|'lane'>>();
  const spans:Span[]=[],warnings:string[]=[];
  const sequence=new Map<string,number>();
  const events=measures.flatMap(m=>[...m.events].filter(e=>e.voice===voice).sort((a,b)=>quarters(a.start)-quarters(b.start)).map(e=>({event:e,order:bars.indexOf(m.number)})));
  events.forEach(({event:e,order},index)=>{
    sequence.set(e.id,index);
    const marks=e.marks.filter(m=>['slur','tied','grace-slur'].includes(m.kind) && !m.hidden);
    for(const mark of marks) {
      const pitch=mark.pitchKey ?? e.pitches.map(p=>`${p.step}${p.octave}:${p.alter}`).sort().join(',');
      const key=mark.kind+':'+(mark.number ?? '1')+(mark.kind==='tied' ? ':'+pitch : '');
      const type=mark.type;
      // Audiveris may attach line-break geometry as start+continue, or as
      // stop+start+continue on the same note. A continuing phrase is not restarted.
      if(mark.kind==='slur' && pending.has(key) && marks.some(m=>m.kind==='slur' && (m.number ?? '1')===(mark.number ?? '1') && m.type==='continue') &&
        marks.some(m=>m.kind==='slur' && (m.number ?? '1')===(mark.number ?? '1') && m.type==='stop') &&
        marks.some(m=>m.kind==='slur' && (m.number ?? '1')===(mark.number ?? '1') && m.type==='start') && type!=='continue') continue;
      if(type==='stop' || type==='continue') {
        const start=pending.get(key);
        if(start && mark.kind==='slur' && type==='continue') continue;
        if(start && index>start.startIndex) {
          if(mark.kind==='slur' && type==='continue') continue;
          spans.push({...start,end:e.id,to:order,endIndex:index,lane:0});pending.delete(key);
        } else warnings.push(`${e.id}: unmatched ${mark.kind} ${type}`);
      }
      if(type==='start' || type==='continue') {
        if(pending.has(key)) warnings.push(`${e.id}: overlapping ${mark.kind} number ${mark.number ?? '1'}`);
        pending.set(key,{kind:mark.kind,start:e.id,from:order,startIndex:index,
          placement:mark.placement==='below' ? 'below' : 'above',lineType:mark.lineType ?? 'solid'});
      }
    }
  });
  pending.forEach(span=>warnings.push(`${span.start}: ${span.kind} has no end; curve omitted`));
  const byId=new Map(events.map(({event})=>[event.id,event]));
  for(const span of spans) {
    const a=byId.get(span.start),b=byId.get(span.end);
    if(a?.grace?.anchorId===b?.id || b?.grace?.anchorId===a?.id) span.kind='grace-slur';
  }
  // Place short inner ties/slurs closer to notes, then stack larger phrases.
  const allocated:Span[]=[];
  for(const span of [...spans].sort((a,b)=>(a.endIndex-a.startIndex)-(b.endIndex-b.startIndex))) {
    if(span.kind==='grace-slur') continue;
    while(allocated.some(other=>other.placement===span.placement && other.lane===span.lane &&
      other.startIndex<span.endIndex && span.startIndex<other.endIndex)) span.lane++;
    allocated.push(span);
  }
  return {spans,warnings,sequence};
}

export interface Anchor {x:number;anchorX:number;top:number;bottom:number;sequence:number;row:number;order:number}
export function spanCurve(span:Span,positions:Map<string,Anchor>,row:number,firstOrder:number,lastOrder:number,
  left:number,right:number,fallbackTop:number,fallbackBottom:number,style:Style['curves'],extraEndpointGap=0) {
  if(span.from>lastOrder || span.to<firstOrder) return undefined;
  const a=positions.get(span.start),b=positions.get(span.end);
  const continuesLeft=span.from<firstOrder,continuesRight=span.to>lastOrder;
  if((!continuesLeft && !a) || (!continuesRight && !b)) return undefined;
  const points=[...positions.values()].filter(p=>p.row===row && p.sequence>=span.startIndex && p.sequence<=span.endIndex);
  const sign=span.placement==='below' ? 1 : -1;
  const clearance=style.clearance+span.lane*style.laneGap;
  const height=span.kind==='grace-slur' ? style.graceHeight : span.kind==='tied' ? style.tieHeight : style.slurHeight;
  const sx=continuesLeft ? left+style.edgeInset : a!.anchorX;
  const ex=continuesRight ? right-style.edgeInset : b!.anchorX;
  if(ex<=sx) return undefined;
  // Equal clearance from each local note envelope allows octave dots to change
  // endpoint heights. Keep the arch balanced relative to that sloping baseline.
  const continuationBound=sign<0 ? Math.min(fallbackTop,...points.map(p=>p.top)) : Math.max(fallbackBottom,...points.map(p=>p.bottom));
  const startBound=continuesLeft ? continuationBound : (sign<0 ? a!.top : a!.bottom);
  const endBound=continuesRight ? continuationBound : (sign<0 ? b!.top : b!.bottom);
  let sy=startBound+sign*(clearance+extraEndpointGap);
  let ey=endBound+sign*(clearance+extraEndpointGap);
  let rise=height;
  const x1=sx+(ex-sx)*.3,x2=ex-(ex-sx)*.3;
  const controls=()=>({y1:sy+(ey-sy)*.3+sign*rise,y2:sy+(ey-sy)*.7+sign*rise});
  const cubic=(a:number,b:number,c:number,d:number,t:number)=>(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d;
  const collisions=()=>{
    const {y1,y2}=controls();let deficit=0;
    for(const p of points.filter(p=>p.anchorX>sx+.1 && p.anchorX<ex-.1)) {
      let lo=0,hi=1;
      for(let i=0;i<24;i++){const mid=(lo+hi)/2;if(cubic(sx,x1,x2,ex,mid)<p.anchorX)lo=mid;else hi=mid;}
      const actual=cubic(sy,y1,y2,ey,(lo+hi)/2);
      const bound=sign<0 ? p.top-clearance : p.bottom+clearance;
      deficit=Math.max(deficit,sign<0 ? actual-bound : bound-actual);
    }
    return deficit;
  };
  while(collisions()>.05 && rise<style.maximumHeight) rise=Math.min(style.maximumHeight,rise+style.collisionStep);
  const lift=collisions();
  if(lift>.05) {sy+=sign*lift;ey+=sign*lift;}
  const {y1,y2}=controls();
  return {sx,sy,x1,y1,x2,y2,ex,ey,startBound,endBound,endpointGap:Math.abs(sy-startBound),
    continuesLeft,continuesRight,placement:span.placement,kind:span.kind,lineType:span.lineType,lane:span.lane};
}

type CurveGeometry=NonNullable<ReturnType<typeof spanCurve>>;
export function curveYAt(c:CurveGeometry,x:number):number {
  const cubic=(a:number,b:number,c:number,d:number,t:number)=>(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d;
  let lo=0,hi=1;
  for(let i=0;i<24;i++){const t=(lo+hi)/2;if(cubic(c.sx,c.x1,c.x2,c.ex,t)<x)lo=t;else hi=t;}
  return cubic(c.sy,c.y1,c.y2,c.ey,(lo+hi)/2);
}
export function curveAvoidanceOffset(outer:CurveGeometry,inner:CurveGeometry,gap:number):number {
  if(outer.placement!==inner.placement) return 0;
  const left=Math.max(outer.sx,inner.sx),right=Math.min(outer.ex,inner.ex);
  if(right-left<.2) return 0;
  const cubic=(a:number,b:number,c:number,d:number,t:number)=>(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d;
  const yAt=(c:CurveGeometry,x:number)=>{
    let lo=0,hi=1;
    for(let i=0;i<24;i++){const t=(lo+hi)/2;if(cubic(c.sx,c.x1,c.x2,c.ex,t)<x)lo=t;else hi=t;}
    return cubic(c.sy,c.y1,c.y2,c.ey,(lo+hi)/2);
  };
  let offset=0;
  for(let i=0;i<=32;i++) {
    const x=left+(right-left)*i/32,oy=yAt(outer,x),iy=yAt(inner,x);
    offset=Math.max(offset,outer.placement==='below' ? iy+gap-oy : oy-iy+gap);
  }
  return offset;
}
