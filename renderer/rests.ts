import {quarters} from './rhythm.js';
export interface RestMeasure {
  number: string; length: string; beats: string; beatType: number; fifths: number; mode: string; implicit?: boolean;
  sourceRestCount?:number;
  events: {voice: string; kind: string; start: string; duration: string; marks: unknown[]}[];
  directions: {kind?:string;start?:string}[]; barlines: {style: string; repeat?: unknown; ending?: unknown}[];
}
export function fullMeasureRest(m: RestMeasure | undefined): boolean {
  if(!m || m.implicit || !m.events.length || m.events.some(e=>e.kind!=='rest')) return false;
  const length=quarters(m.length);
  const beats=m.beats.split('+').reduce((sum,b)=>sum+Number(b),0);
  if(!(length>0) || Math.abs(length-beats*4/m.beatType)>1e-8) return false;
  for(const voice of new Set(m.events.map(e=>e.voice))) {
    let end=0;
    for(const e of m.events.filter(e=>e.voice===voice).sort((a,b)=>quarters(a.start)-quarters(b.start))) {
      if(quarters(e.duration)<=0 || Math.abs(quarters(e.start)-end)>1e-8) return false;
      end+=quarters(e.duration);
    }
    if(Math.abs(end-length)>1e-8) return false;
  }
  return true;
}
export function compressibleRest(m: RestMeasure | undefined,allowInitialDirections=false): boolean {
  return fullMeasureRest(m) && !!m && !m.events.some(e=>e.marks.length) &&
    (!m.directions.length || allowInitialDirections && m.directions.every(d=>d.start==='0' && ['words','metronome','dynamics'].includes(d.kind ?? ''))) &&
    !m.barlines.some(b=>b.repeat || b.ending || !['regular','light-heavy'].includes(b.style));
}
export function restRunLength(measures: (RestMeasure | undefined)[][], start: number): number {
  const first=measures[start];
  if(!first?.length || !first.every(m=>compressibleRest(m,true))) return 0;
  let count=1;
  const sourceLimit=Math.min(...first.map(m=>m?.sourceRestCount || Infinity));
  while(start+count<measures.length && count<sourceLimit) {
    if(measures[start+count-1].some(m=>m?.barlines.some(b=>b.style!=='regular'))) break;
    const next=measures[start+count];
    if(next.length!==first.length || !next.every((m,i)=>{
      const previous=first[i];
      return compressibleRest(m) && !!m && !m.sourceRestCount && !!previous && Number(m.number)===Number(previous.number)+count &&
        m.beats===previous.beats && m.beatType===previous.beatType && m.fifths===previous.fifths && m.mode===previous.mode && m.length===previous.length;
    })) break;
    count++;
  }
  return count;
}
