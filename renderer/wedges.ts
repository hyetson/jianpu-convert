import {quarters} from './rhythm.js';
export interface WedgeDirection {kind:string;text:string;number?:string;start:string;placement?:string;voice?:string}
export interface WedgePoint {order:number;time:number;absolute:number}
export interface WedgeSpan {id:string;type:string;placement:string;start:WedgePoint;end:WedgePoint;voice?:string}
export function collectWedges(measures:{number:string;length:string;directions:WedgeDirection[]}[],bars:string[]) {
  const offsets=new Map<string,number>();let total=0;
  for(const m of measures) {offsets.set(m.number,total);total+=quarters(m.length);}
  const pending=new Map<string,Omit<WedgeSpan,'end'>>(),spans:WedgeSpan[]=[],warnings:string[]=[];
  for(const m of measures) for(const d of [...m.directions].sort((a,b)=>quarters(a.start)-quarters(b.start))) {
    if(d.kind!=='wedge') continue;
    const key=d.number ?? '1',point={order:bars.indexOf(m.number),time:quarters(d.start),absolute:offsets.get(m.number)!+quarters(d.start)};
    if(d.text==='stop') {
      const start=pending.get(key);
      if(start && point.absolute>start.start.absolute) {spans.push({...start,end:point});pending.delete(key);}
      else warnings.push(`Bar ${m.number}: unmatched wedge stop ${key}`);
    } else if(['crescendo','diminuendo'].includes(d.text)) {
      if(pending.has(key)) warnings.push(`Bar ${m.number}: overlapping wedge ${key}`);
      pending.set(key,{id:`${m.number}:${d.start}:${key}`,type:d.text,placement:d.placement ?? 'below',start:point,...(d.voice?{voice:d.voice}:{})});
    } else if(d.text==='continue' && !pending.has(key)) warnings.push(`Bar ${m.number}: unmatched wedge continuation ${key}`);
  }
  pending.forEach(w=>warnings.push(`Bar ${bars[w.start.order]}: wedge has no end; omitted`));
  return {spans,warnings,offsets};
}
export function wedgeOpening(span:WedgeSpan,absolute:number,height:number) {
  const progress=Math.max(0,Math.min(1,(absolute-span.start.absolute)/(span.end.absolute-span.start.absolute)));
  return height*(span.type==='crescendo' ? progress : 1-progress);
}
