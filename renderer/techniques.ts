/** Instrument-dependent display policy; source marks are never deleted. */
export const INSTRUMENT_FAMILIES=['wind','bowed','plucked','struck-string','unknown'] as const;
export type InstrumentFamily=typeof INSTRUMENT_FAMILIES[number];
export interface TechniquePolicy {windStaccato?:'hide'|'show'}
export interface TechniqueMark {
  kind:string;label?:string;type?:string;number?:string;hidden?:boolean;direction?:string;
  tremoloStrokes?:number;harmonic?:{kind?:string;pitchRole?:string};
}
export function resolveTechniquePolicy(policy:TechniquePolicy={}) {
  if(!policy || typeof policy!=='object' || Array.isArray(policy)) throw new Error('techniques must be an object');
  for(const key of Object.keys(policy)) if(key!=='windStaccato') throw new Error(`Unknown technique policy: ${key}`);
  if(policy.windStaccato!==undefined && !['hide','show'].includes(policy.windStaccato)) throw new Error('techniques.windStaccato must be hide or show');
  return {windStaccato:policy.windStaccato ?? 'hide'};
}
export function suppressionReason(mark:TechniqueMark,family:InstrumentFamily,policy:ReturnType<typeof resolveTechniquePolicy>):string|null {
  if(mark.hidden) return 'source-print-object-no';
  return family==='wind' && mark.kind==='staccato' && policy.windStaccato==='hide' ? 'wind-staccato-hidden' : null;
}
export function techniqueGlyph(mark:TechniqueMark):string|null {
  const codes:Record<string,number>={'double-tongue':0xe5f0,'triple-tongue':0xe5f2,'down-bow':0xe610,'up-bow':0xe612,
    harmonic:0xe614,'snap-pizzicato':0xe631,'left-hand-pizzicato':0xe633,damp:0xe638,'damp-all':0xe639};
  // A circle alone cannot describe the touching/sounding roles of an artificial harmonic.
  if(mark.kind==='harmonic' && mark.harmonic?.kind==='artificial') return null;
  return codes[mark.kind]!=null ? String.fromCodePoint(codes[mark.kind]) : null;
}
export function tremoloStrokes(mark:TechniqueMark):number|null {
  const value=mark.tremoloStrokes ?? Number(mark.label);
  return (mark.tremoloStrokes!=null || !!mark.label?.trim()) && Number.isInteger(value) && value>=1 && value<=8 && mark.type!=='unmeasured' ? value : null;
}
export function techniqueText(mark:TechniqueMark):string {
  if(mark.kind==='harmonic') return mark.harmonic?.kind==='artificial' ? '人工泛音' : '泛音';
  if(mark.kind==='tremolo') return mark.type==='unmeasured' ? '自由震音' : '震音（待核）';
  return mark.label || ({'breath-mark':'换气','fingering':'指法（待核）','pluck':'拨弦指法（待核）','other-technical':'技法（待核）'}[mark.kind] ?? mark.kind);
}
interface MarkedEvent {id:string;voice:string;marks:TechniqueMark[]}
export function collectTremolos(measures:{events:MarkedEvent[]}[]) {
  const pending=new Map<string,{event:string;strokes:number}>(),pairs:{start:string;end:string;strokes:number}[]=[],warnings:string[]=[];
  for(const m of measures) for(const e of m.events) for(const mark of e.marks) {
    if(mark.kind!=='tremolo' || mark.hidden || !['start','stop'].includes(mark.type ?? '')) continue;
    const key=e.voice+':'+(mark.number ?? '1'),strokes=tremoloStrokes(mark);
    if(mark.type==='start') {
      if(pending.has(key)) warnings.push(`${e.id}: overlapping double-note tremolo`);
      pending.delete(key);
      if(strokes===null) warnings.push(`${e.id}: invalid double-note tremolo stroke count`);
      else pending.set(key,{event:e.id,strokes});
    } else {
      const start=pending.get(key);pending.delete(key);
      if(!start || strokes===null || strokes!==start.strokes || start.event===e.id) warnings.push(`${e.id}: unmatched or inconsistent double-note tremolo`);
      else pairs.push({start:start.event,end:e.id,strokes});
    }
  }
  pending.forEach(p=>warnings.push(`${p.event}: double-note tremolo has no end`));
  return {pairs,warnings};
}
