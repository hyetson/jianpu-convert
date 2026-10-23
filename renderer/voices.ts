/** Display lanes are local; source staff:voice identities and chords stay intact. */
export interface VoiceMeasure {
  events:{voice:string;kind:string;marks:{hidden?:boolean}[]}[];
  directions:{voice?:string}[];
}
export function localVoiceRows(m:VoiceMeasure,voices:string[],primary:string,required:string[]=[]):string[] {
  const available=new Set(m.events.map(e=>e.voice));
  const visible=new Set(m.events.filter(e=>e.kind!=='rest' || e.marks.some(mark=>!mark.hidden)).map(e=>e.voice));
  for(const voice of [...required,...m.directions.flatMap(d=>d.voice?[d.voice]:[])]) if(available.has(voice)) visible.add(voice);
  if(!visible.size) visible.add(available.has(primary)?primary:voices.find(v=>available.has(v)) ?? primary);
  return [primary,...voices.filter(v=>v!==primary)].filter(v=>visible.has(v));
}
