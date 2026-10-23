import {quarters} from './rhythm.js';

export interface TupletMark {
  kind:string;type?:string;number?:string;hidden?:boolean;placement?:string;
  tupletActual?:number;tupletNormal?:number;lineShape?:string;bracket?:string;showNumber?:string;
}
interface Event {id:string;voice:string;kind:string;start:string;duration:string;noteType:string;tuplet?:{actual:number;normal:number}|null;marks:TupletMark[]}
export interface TupletGroup {start:string;end:string;actual:number;normal:number;events:string[];placement:string;
  lineShape:string;bracket:boolean;showNumber:string;source:'explicit'|'time-modification';duration:number}

/** Display spans are distinct from time modification and from musical slurs. */
export function collectTuplets(measures:{number:string;events:Event[]}[],voice:string) {
  const events=measures.flatMap(m=>m.events.filter(e=>e.voice===voice && e.kind!=='grace').map(e=>({e,bar:m.number})));
  const pending=new Map<string,{index:number;mark:TupletMark}>(),groups:TupletGroup[]=[],warnings:string[]=[],covered=new Set<number>();
  const finish=(from:number,to:number,mark:TupletMark,source:TupletGroup['source'])=>{
    for(let i=from;i<=to;i++) covered.add(i);
    const e=events[from].e,actual=mark.tupletActual ?? e.tuplet?.actual,normal=mark.tupletNormal ?? e.tuplet?.normal;
    if(!Number.isInteger(actual) || !actual || !Number.isInteger(normal) || !normal) {warnings.push(`${e.id}: tuplet ratio missing; display omitted`);return;}
    if(mark.hidden) return;
    groups.push({start:e.id,end:events[to].e.id,actual,normal,events:events.slice(from,to+1).map(x=>x.e.id),
      placement:mark.placement==='below'?'below':'above',lineShape:mark.lineShape ?? 'curved',bracket:mark.bracket!=='no',
      showNumber:mark.showNumber ?? 'actual',source,duration:events.slice(from,to+1).reduce((sum,x)=>sum+quarters(x.e.duration),0)});
  };
  for(const [{e},index] of events.map((x,i)=>[x,i] as const)) {
    for(const mark of e.marks.filter(m=>m.kind==='tuplet')) {
      const key=mark.number ?? '1';
      if(mark.type==='start') {
        if(pending.has(key)) warnings.push(`${e.id}: overlapping tuplet ${key}`);
        pending.set(key,{index,mark});
      }
      if(mark.type==='stop') {
        const start=pending.get(key);pending.delete(key);
        if(start) finish(start.index,index,start.mark,'explicit');
        else warnings.push(`${e.id}: unmatched tuplet stop ${key}`);
      }
    }
  }
  pending.forEach(({index})=>{covered.add(index);warnings.push(`${events[index].e.id}: tuplet has no end; display omitted`);});
  // Only infer equal-type, contiguous complete groups. Mixed/nested tuplets
  // require explicit endpoints; counting every N notes would invent groups.
  for(let i=0;i<events.length;i++) {
    const first=events[i].e,ratio=first.tuplet;
    if(covered.has(i) || !ratio) continue;
    const group=events.slice(i,i+ratio.actual);
    const valid=group.length===ratio.actual && group.every((x,j)=>!covered.has(i+j) && x.bar===events[i].bar &&
      x.e.tuplet?.actual===ratio.actual && x.e.tuplet?.normal===ratio.normal && x.e.noteType===first.noteType &&
      quarters(x.e.duration)===quarters(first.duration) && (!j || Math.abs(quarters(group[j-1].e.start)+quarters(group[j-1].e.duration)-quarters(x.e.start))<1e-8));
    if(valid) {finish(i,i+ratio.actual-1,{kind:'tuplet'},'time-modification');i+=ratio.actual-1;}
    else {covered.add(i);warnings.push(`${first.id}: incomplete tuplet needs explicit endpoints`);}
  }
  return {groups,warnings};
}
export const tupletDigits=(text:string)=>[...text].map(c=>c===':'?'\uE88A':/\d/.test(c)?String.fromCodePoint(0xe880+Number(c)):c).join('');
