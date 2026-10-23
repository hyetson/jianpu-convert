/** Horizontal coordinates and duration underlines; source events stay intact. */
import {STYLE_DEFAULTS, type Style} from './layout.js';
export interface RhythmEvent {
  id: string; start: string; duration: string; kind: string; noteType: string;
  dots: number; tuplet?: unknown;
  beams?: {number:number;value:string}[] | null;
  grace?:{position:string;anchorId:string}|null;
  pitches: {accidental: string; displayAccidental?: string}[];
}
export const quarters = (value: string): number => {
  const [n, d] = value.split('/').map(Number);
  return n / (d ?? 1);
};
export const underlineCount = (type: string): number =>
  ({eighth: 1, '16th': 2, '32nd': 3, '64th': 4, '128th': 5}[type] ?? 0);
export const meterWidthRatio=(length:number,bias=STYLE_DEFAULTS.spacing.meterWidthBias)=>(length+bias)/(4+bias);
export interface UnderlineGroup<T extends RhythmEvent> {events: T[]; segments: {level: number; first: string; last: string}[]}

/** Source beams are authoritative; absence of metadata permits beat fallback. */
export function inputBeamLinks(events:RhythmEvent[]):Set<number>[] {
  const links=Array.from({length:Math.max(1,...events.map(e=>underlineCount(e.noteType)))},()=>new Set<number>());
  for(let level=0;level<links.length;level++) {
    let previous=-1;
    for(let i=0;i<events.length;i++) {
      const event=events[i],value=event.beams?.find(b=>b.number===level+1)?.value;
      if(value==='begin') previous=i;
      else if(value==='continue' || value==='end') {
        if(previous>=0 && events.slice(previous,i+1).every(e=>underlineCount(e.noteType)>level) &&
          events.slice(previous,i).every((e,j)=>Math.abs(quarters(e.start)+quarters(e.duration)-quarters(events[previous+j+1].start))<1e-8))
          for(let j=previous;j<i;j++) links[level].add(j);
        previous=value==='continue' ? i : -1;
      } else if(event.kind!=='rest') previous=-1;
    }
  }
  return links;
}

/** Rests may share duration lines with adjacent notes within one metrical beat.
 * Beats without short rests retain explicit source groups, including cross-beat beams.
 */
export function resolvedBeamLinks(events:RhythmEvent[],beats:string,beatType:number):Set<number>[] {
  const links=inputBeamLinks(events);
  // Simple meters use the denominator; compound meters group three units.
  const numerator=Number(beats),beat=4/beatType*(beatType>=8 && numerator>3 && numerator%3===0 ? 3 : 1);
  const beatAt=(e:RhythmEvent)=>Math.floor((quarters(e.start)+1e-8)/beat);
  const eligible=(e:RhythmEvent)=>['note','rest'].includes(e.kind) && !e.tuplet && underlineCount(e.noteType)>0 &&
    quarters(e.duration)>0 && quarters(e.start)>=0 && quarters(e.start)+quarters(e.duration)<=(beatAt(e)+1)*beat+1e-8;
  const restBeats=new Set(events.filter(e=>e.kind==='rest' && eligible(e)).map(beatAt));
  for(let i=1;i<events.length;i++) {
    const a=events[i-1],b=events[i],sameBeat=beatAt(a)===beatAt(b);
    // A mixed note/rest beat must not continue into the neighbouring beat.
    if(!sameBeat && (restBeats.has(beatAt(a)) || restBeats.has(beatAt(b)))) for(const level of links) level.delete(i-1);
    const contiguous=Math.abs(quarters(a.start)+quarters(a.duration)-quarters(b.start))<1e-8;
    const mixedBeat=restBeats.has(beatAt(a));
    const fallback=beats==='4' && beatType===4 && a.beams==null && b.beams==null;
    if(sameBeat && contiguous && eligible(a) && eligible(b) && (mixedBeat || fallback))
      for(let level=0;level<Math.min(underlineCount(a.noteType),underlineCount(b.noteType));level++) links[level].add(i-1);
  }
  return links;
}

export function underlineGroups<T extends RhythmEvent>(events: T[], beats: string, beatType: number): UnderlineGroup<T>[] {
  // Grace notes have their own beam stream even at a main note's onset.
  if(events.some(e=>e.kind==='grace') && events.some(e=>e.kind!=='grace'))
    return [...underlineGroups(events.filter(e=>e.kind!=='grace'),beats,beatType),...underlineGroups(events.filter(e=>e.kind==='grace'),beats,beatType)];
  const groups: {event:T;index:number}[][] = [];
  const ordered = [...events].sort((a,b) => quarters(a.start)-quarters(b.start));
  const source=resolvedBeamLinks(ordered,beats,beatType);
  for (const [index,event] of ordered.entries()) {
    if (!underlineCount(event.noteType)) continue;
    if (source[0].has(index-1)) groups.at(-1)!.push({event,index});
    else groups.push([{event,index}]);
  }
  return groups.map(entries => {
    const group=entries.map(e=>e.event);
    const segments: UnderlineGroup<T>['segments'] = [];
    for (let level=0; level<Math.max(...group.map(e => underlineCount(e.noteType))); level++) {
      let first: RhythmEvent | undefined, last: RhythmEvent | undefined;
      const flush = () => {if (first && last) segments.push({level, first:first.id, last:last.id}); first=last=undefined;};
      for (const {event,index} of entries) {
        const linked=source[level]?.has(index-1);
        if (first && !linked) flush();
        if (underlineCount(event.noteType)>level) {first ??= event; last=event;}
        else flush();
      }
      flush();
    }
    return {events:group, segments};
  });
}

export function measureSpacing(events: RhythmEvent[], length: number, font: number, spacing: Style['spacing'] = STYLE_DEFAULTS.spacing,
  accidentalClearance?: (pitch: RhythmEvent['pitches'][number])=>number,
  graceStyle:Pick<Style['notation'],'graceScale'|'graceOffsetXRatio'>=STYLE_DEFAULTS.notation,
  markClearance?:(event:RhythmEvent)=>number,
  meter:{beats:string;beatType:number}={beats:'4',beatType:4}) {
  // Integer positions also anchor continuation dashes and long rests.
  const graceTimes=new Map<string,number>();
  for(const e of events.filter(e=>e.kind==='grace')) {
    const anchor=events.find(a=>a.id===e.grace?.anchorId);
    graceTimes.set(e.id,anchor ? quarters(anchor.start)+(e.grace?.position==='after' ? Math.max(0,Math.ceil(quarters(anchor.duration))-1) : 0) : quarters(e.start));
  }
  const times = [...new Set([0, ...events.map(e => graceTimes.get(e.id) ?? quarters(e.start)),
    ...Array.from({length:Math.max(0,Math.ceil(length)-1)}, (_,i) => i+1)])].sort((a,b)=>a-b);
  const accidentalWidth = (at: number) => Math.max(0,...events.filter(e=>quarters(e.start)===at).flatMap(e=>e.pitches.map(p=>{
    const alter=Math.abs(quarters(p.accidental));
    const ratio=p.displayAccidental==='natural' || alter===1 ? spacing.accidentalSpaceRatio : alter===2 ? spacing.doubleAccidentalSpaceRatio : alter ? spacing.microtoneSpaceRatio : 0;
    return Math.max(font*ratio,accidentalClearance?.(p) ?? 0)+(markClearance?.(e) ?? 0);
  })));
  const graceOffsets=new Map<string,number>(),graceLead=new Map<number,number>(),graceTail=new Map<number,number>();
  for(const at of times) {
    const group=events.filter(e=>e.kind==='grace' && graceTimes.get(e.id)===at && e.grace?.position!=='after');
    let offset=-font*graceStyle.graceOffsetXRatio;
    for(const e of [...group].reverse()) {
      graceOffsets.set(e.id,offset);
      const extra=Math.max(0,...e.pitches.map(p=>Math.abs(quarters(p.accidental)) ? font*graceStyle.graceScale*spacing.accidentalSpaceRatio : 0));
      offset-=font*graceStyle.graceScale*spacing.columnWidthRatio+extra;
    }
    if(group.length) graceLead.set(at,-graceOffsets.get(group[0].id)!+accidentalWidth(at)*graceStyle.graceScale);
    const after=events.filter(e=>e.kind==='grace' && graceTimes.get(e.id)===at && e.grace?.position==='after');
    let tail=font*1.2;
    for(const e of after) {
      const extra=Math.max(0,...e.pitches.map(p=>Math.abs(quarters(p.accidental)) ? font*graceStyle.graceScale*spacing.accidentalSpaceRatio : 0));
      tail+=extra;graceOffsets.set(e.id,tail);tail+=font*graceStyle.graceScale*spacing.columnWidthRatio;
    }
    if(after.length) graceTail.set(at,tail);
  }
  const lead=(at:number)=>graceLead.get(at) ?? 0;
  const ordered=[...events].sort((a,b)=>quarters(a.start)-quarters(b.start));
  const sourceLinks=resolvedBeamLinks(ordered,meter.beats,meter.beatType)[0];
  const joinedTimes=new Set([...sourceLinks].map(i=>quarters(ordered[i+1].start)));
  const groupStarts=new Set(ordered.filter(e=>e.beams?.some(b=>b.number===1 && b.value==='begin')).map(e=>quarters(e.start)));
  const separated=(at:number,next:number)=>!joinedTimes.has(next) && (Math.floor(next)>Math.floor(at) || groupStarts.has(next));
  const leftPadding = font*spacing.leftPaddingRatio + accidentalWidth(0)+lead(0);
  const rightPadding = font*spacing.rightPaddingRatio;
  const columns = times.map((at,i) => {
    const next = times[i+1];
    const simultaneous = events.filter(e => quarters(e.start)===at);
    const glyph = Math.max(font*spacing.columnWidthRatio,...simultaneous.map(e => font*(spacing.columnWidthRatio+(quarters(e.duration)<2 ? e.dots*spacing.augmentationSpaceRatio : 0))));
    if (next === undefined) return Math.max(glyph,font*spacing.durationSpacingRatio*Math.sqrt(Math.max(.25,length-at)))+(graceTail.get(at) ?? 0);
    const beatGap = separated(at,next) ? font*spacing.beatGapRatio : 0;
    return Math.max(glyph+accidentalWidth(next)+beatGap+lead(next),font*spacing.durationSpacingRatio*Math.sqrt(next-at))+(graceTail.get(at) ?? 0);
  });
  const idealWidth=font*spacing.measureWidthRatio*meterWidthRatio(length,spacing.meterWidthBias);
  const extra=Math.max(0,idealWidth-leftPadding-columns.reduce((a,b)=>a+b,0)-rightPadding);
  for(let i=0;i<columns.length;i++) columns[i]+=extra*Math.max(0,(times[i+1] ?? length)-times[i])/length;
  const width = leftPadding + columns.reduce((a,b)=>a+b,0) + rightPadding;
  // Compression spends white space only; keep glyphs, accidental clearance,
  // augmentation dots and the distinction between intra-beat and beat gaps.
  const minimumColumns=times.map((at,i)=>{
    const next=times[i+1];
    const glyph=Math.max(font*spacing.minimumColumnWidthRatio,...events.filter(e=>quarters(e.start)===at).map(e=>
      font*(spacing.minimumColumnWidthRatio+(quarters(e.duration)<2 ? e.dots*spacing.augmentationSpaceRatio : 0))));
    const clearance=next===undefined ? 0 : accidentalWidth(next)+lead(next)+(separated(at,next) ? font*spacing.minimumBeatGapRatio : 0);
    return Math.min(columns[i],Math.max(columns[i]*spacing.minimumCompressionRatio,glyph+clearance+(graceTail.get(at) ?? 0)));
  });
  const minimumWidth=leftPadding+minimumColumns.reduce((a,b)=>a+b,0)+rightPadding;
  return {times,columns,minimumColumns,leftPadding,rightPadding,width,minimumWidth,graceOffsets,graceTimes,idealWidth};
}

export function offsetAt(time: number, times: number[], columns: number[]): number {
  let offset=0;
  for(let i=0;i<times.length;i++) {
    if(time<=times[i]) return offset;
    if(i+1<times.length && time<times[i+1]) return offset+columns[i]*(time-times[i])/(times[i+1]-times[i]);
    offset+=columns[i];
  }
  return offset;
}
