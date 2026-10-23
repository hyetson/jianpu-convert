import fs from 'node:fs';
import path from 'node:path';
import PDFDocument from 'pdfkit';
import {measureSpacing, offsetAt, underlineGroups,meterWidthRatio} from './rhythm.js';
import {contextChanges, planSystems} from './systems.js';
import {resolveLayout, type LayoutOptions} from './layout.js';
import {compressibleRest,fullMeasureRest,restRunLength} from './rests.js';
import {collectSpans,spanCurve,curveAvoidanceOffset,curveYAt,type SpanMark,type Anchor} from './spans.js';
import {collectWedges,wedgeOpening} from './wedges.js';
import {dynamicGlyph,meterDigits,metronomeGlyph,isTempoTerm} from './engraving.js';
import {graceHook} from './graces.js';
import {localVoiceRows} from './voices.js';
import {collectTuplets,tupletDigits,type TupletMark} from './tuplets.js';
import {INSTRUMENT_FAMILIES,resolveTechniquePolicy,suppressionReason,techniqueGlyph,techniqueText,tremoloStrokes,collectTremolos,
  type InstrumentFamily,type TechniqueMark,type TechniquePolicy} from './techniques.js';

interface Mark extends SpanMark,TechniqueMark,TupletMark {ornamentAccidental?:string}
interface Pitch { degree: number; octaveDots: number; accidental: string; displayAccidental?: string; step: string; octave: number; alter: string }
interface Event { id: string; voice: string; start: string; duration: string; kind: string; pitches: Pitch[]; noteType: string; dots: number; tuplet?: {actual: number; normal: number} | null; marks: Mark[];beams?:{number:number;value:string}[]|null;grace?:{position:string;anchorId:string;slash?:boolean}|null }
interface Direction { start: string; kind: string; text: string; number?: string; placement?: string;fontStyle?:string;fontWeight?:string;beatUnit?:string;beatDots?:number;perMinute?:string;voice?:string }
interface Measure { number: string; length: string; beats: string; beatType: number; fifths: number; mode: string; implicit: boolean; synthetic: boolean; sourceRestCount?:number;events: Event[]; directions: Direction[]; barlines: {style: string; repeat?: {direction: string} | null; ending?: {number: string; type: string} | null}[] }
interface Part { id: string; name: string; instrumentFamily?:InstrumentFamily; measures: Measure[] }
interface Score { title: string; subtitle: string; composer: string; draft: boolean; recognitionSource: boolean; bars: string[]; parts: Part[]; fonts: {text: string; music: string; numbers?: string; restCounts?: string|string[];measureNumbers?:string|string[];termsRegular?:string;termsBold?:string;termsItalic?:string;termsBoldItalic?:string}; layout: LayoutOptions; issues: {severity: string; code: string; measure: string; part: string; message: string}[] }
interface Score {techniques?:TechniquePolicy;dynamicsPlacement?:'below'|'source';workflow?:string;localVoices?:{primaryVoice?:string}}
interface Row { part: Part; voice: string; label: string; chordSize: number }
interface Bar { number: string; count: number; measures: (Measure | undefined)[]; times: number[]; columns: number[]; minimumColumns: number[]; leftPadding: number; rightPadding: number; width: number; minimumWidth: number; compressed: boolean; order: number;graceOffsets:Map<string,number>;graceTimes:Map<string,number>;meterInset:number;meterWeight:number;idealWidth:number }
interface Position extends Anchor {y:number;tail?:{right:number;y:number}}
interface GlyphFont {ascent: number; unitsPerEm: number; glyphForCodePoint(code: number): {id:number;advanceWidth:number;bbox: {minX: number; minY: number; maxX: number; maxY: number}}}

const q = (v: string): number => { const [n, d] = v.split('/').map(Number); return n / (d ?? 1); };
const keys: Record<number, string> = {'-7':'Cb','-6':'Gb','-5':'Db','-4':'Ab','-3':'Eb','-2':'Bb','-1':'F',0:'C',1:'G',2:'D',3:'A',4:'E',5:'B',6:'F#',7:'C#'};
const minorKeys: Record<number, string> = {'-7':'Ab','-6':'Eb','-5':'Bb','-4':'F','-3':'C','-2':'G','-1':'D',0:'A',1:'E',2:'B',3:'F#',4:'C#',5:'G#',6:'D#',7:'A#'};
const keyLabel = (m: Measure): string => m.mode === 'minor' ? `6=${minorKeys[m.fifths] ?? '?'}` : `1=${keys[m.fifths] ?? '?'}`;
const accidentalGlyph=(p: Pick<Pitch,'accidental'|'displayAccidental'>): string | null=>{
  const alteration=q(p.accidental);
  return p.displayAccidental==='natural'?'\uE261':alteration===1?'\uE262':alteration===-1?'\uE260':alteration===2?'\uE263':alteration===-2?'\uE264':null;
};

async function render(score: Score, output: string): Promise<void> {
  const layout=resolveLayout(score.layout);
  const policy=resolveTechniquePolicy(score.techniques),tech=layout.techniques;
  const dynamicsPlacement=score.dynamicsPlacement ?? 'below';
  if(!['below','source'].includes(dynamicsPlacement)) throw new Error('dynamicsPlacement must be below or source');
  for(const part of score.parts) if(part.instrumentFamily!==undefined && !INSTRUMENT_FAMILIES.includes(part.instrumentFamily))
    throw new Error(`Invalid instrumentFamily for ${part.id}`);
  const {typography:t,notation:n,spacing:s,context:c,measureNumbers:mn,barlines:bl,header:h}=layout;
  const baseFont = layout.fontSize;
  let font = baseFont;
  const margin = layout.margin;
  const doc = new PDFDocument({size: layout.pageSize, margin, autoFirstPage: false, bufferPages: true,
    info: {Title: score.title, Author: score.composer, Subject: 'Numbered notation - staff PDF conversion review'}});
  doc.registerFont('text', score.fonts.text);
  doc.registerFont('music', score.fonts.music);
  doc.registerFont('numbers',score.fonts.numbers ?? score.fonts.text);
  const termFonts={regular:'Times-Roman',bold:'Times-Bold',italic:'Times-Italic',boldItalic:'Times-BoldItalic'};
  for(const [style,key] of Object.entries({regular:'termsRegular',bold:'termsBold',italic:'termsItalic',boldItalic:'termsBoldItalic'})) {
    const file=score.fonts[key as keyof typeof score.fonts];
    if(typeof file==='string') {const name='term-'+style;doc.registerFont(name,file);termFonts[style as keyof typeof termFonts]=name;}
  }
  // PDFKit's line boxes include font ascent/descent. Its pinned embedded-font
  // adapter supplies glyph ink bounds for symbol alignment instead.
  const activeGlyphFont=()=> (doc as unknown as {_font:{font:GlyphFont}})._font.font;
  doc.font('text'); const textFont=activeGlyphFont();
  doc.font('music'); const musicFont=activeGlyphFont();
  doc.font('numbers'); const numberFont=activeGlyphFont();
  const loadFaces=(paths:string|string[],prefix:string)=>(Array.isArray(paths)?paths:[paths]).map((file,i)=>{
    const name=prefix+i;doc.registerFont(name,file);doc.font(name);return {name,font:activeGlyphFont()};
  });
  const countFaces=loadFaces(score.fonts.restCounts ?? score.fonts.text,'restCounts');
  const measureFaces=loadFaces(score.fonts.measureNumbers ?? score.fonts.text,'measureNumbers');
  const styledDigits=(text:string,faces:typeof countFaces,size:number,gap:number)=>{
    let cursor=0;
    return [...text].map(char=>{
      const face=faces.find(f=>f.font.glyphForCodePoint(char.codePointAt(0)!).id!==0);
      if(!face) throw new Error(`Missing ornamental digit ${char}; configure the corresponding fonts`);
      const glyph=face.font.glyphForCodePoint(char.codePointAt(0)!);
      const unit=size/face.font.unitsPerEm;
      const result={...face,char,x:cursor,left:cursor+glyph.bbox.minX*unit,right:cursor+glyph.bbox.maxX*unit,
        top:-glyph.bbox.maxY*unit,bottom:-glyph.bbox.minY*unit};
      cursor+=glyph.advanceWidth*unit+gap;
      return result;
    });
  };
  const countGlyphs=(text:string)=>styledDigits(text,countFaces,t.restCountSize,layout.rests.countDigitGap);
  const glyphBounds=(face: GlyphFont,value: string,x: number,y: number,size: number)=>{
    const box=face.glyphForCodePoint(value.codePointAt(0)!).bbox;
    const unit=size/face.unitsPerEm;
    const baseline=y+face.ascent*unit;
    return {left:x+box.minX*unit,right:x+box.maxX*unit,
      top:baseline-box.maxY*unit,bottom:baseline-box.minY*unit,
      centerX:x+(box.minX+box.maxX)*unit/2,centerY:baseline-(box.minY+box.maxY)*unit/2};
  };
  const digitBounds=(value: string,x: number,y: number,size: number)=>glyphBounds(numberFont,value,x,y,size);
  const musicRun=(value:string,size:number)=>{
    let cursor=0;const boxes=[];
    for(const char of value) {
      const glyph=musicFont.glyphForCodePoint(char.codePointAt(0)!),unit=size/musicFont.unitsPerEm;
      if(!glyph.id) throw new Error(`Missing SMuFL glyph ${char.codePointAt(0)!.toString(16)}`);
      boxes.push({left:cursor+glyph.bbox.minX*unit,right:cursor+glyph.bbox.maxX*unit,top:-glyph.bbox.maxY*unit,bottom:-glyph.bbox.minY*unit});
      cursor+=glyph.advanceWidth*unit;
    }
    return {left:Math.min(...boxes.map(b=>b.left)),right:Math.max(...boxes.map(b=>b.right)),top:Math.min(...boxes.map(b=>b.top)),bottom:Math.max(...boxes.map(b=>b.bottom))};
  };
  const musicInk=(value:string,left:number,top:number,size:number)=>{
    const box=musicRun(value,size),width=box.right-box.left,height=box.bottom-box.top;
    doc.font('music').fontSize(size).text(value,left-box.left,top-box.top,{lineBreak:false,baseline:'alphabetic'});
    return {left,right:left+width,top,bottom:top+height};
  };
  const meterMetrics=(m:Measure,size:number)=>{
    const height=2*size*bl.halfHeightRatio*layout.meter.heightRatio;
    const glyphHeight=(height-2*layout.meter.stackGap-layout.meter.lineWidth)/2;
    const top=meterDigits(m.beats),bottom=meterDigits(String(m.beatType));
    const box=musicRun(meterDigits('0123456789'),1),fontSize=glyphHeight/(box.bottom-box.top);
    const a=musicRun(top,fontSize),b=musicRun(bottom,fontSize);
    return {height,glyphHeight,fontSize,top,bottom,width:Math.max(a.right-a.left,b.right-b.left)+2};
  };
  fs.mkdirSync(path.dirname(path.resolve(output)), {recursive: true});
  const stream = fs.createWriteStream(output, {flags: 'wx'});
  const completion = new Promise<void>((resolve, reject) => { stream.on('finish', resolve); stream.on('error', reject); doc.on('error', reject); });
  doc.pipe(stream);
  const warnings: string[] = [];
  const rows: Row[] = [];
  for (const part of score.parts) {
    const voices = [...new Set(part.measures.flatMap(m => m.events.map(e => e.voice)))].sort();
    if (!voices.length) voices.push('1:1');
    for (const voice of voices) rows.push({part, voice, label: part.name + (voices.length > 1 ? ` [${voice}]` : ''),
      chordSize: Math.max(1, ...part.measures.flatMap(m => m.events.filter(e => e.voice === voice).map(e => e.pitches.length)))});
  }
  if (!rows.length || rows.length > 12) throw new Error('Renderer supports 1-12 independent rows');
  const singleVoice=rows.length===1;
  const localMode=score.workflow==='local-dual-voice';
  if(localMode && (score.parts.length!==1 || rows.length>2)) throw new Error('Local dual-voice mode requires one part and at most two staff:voice streams');
  const primaryVoice=score.localVoices?.primaryVoice ?? rows[0].voice;
  if(localMode && !rows.some(r=>r.voice===primaryVoice)) throw new Error(`Primary voice ${primaryVoice} is absent`);
  const alignDigitX=(value:string,x:number,y:number,size:number)=>localMode?
    x+digitBounds('0',0,y,size).centerX-digitBounds(value,0,y,size).centerX:x;
  const lookup = score.parts.map(p => new Map(p.measures.map(m => [m.number, m])));
  const alignedMeasures=score.bars.map(number=>lookup.map(p=>p.get(number)));
  const bars: Bar[] = [];
  for (let i = 0; i < score.bars.length; i++) {
    const number = score.bars[i];
    const measures = lookup.map(p => p.get(number));
    let count = 1;
    if (layout.compressRests && measures.every(m=>compressibleRest(m,true))) count=restRunLength(alignedMeasures,i);
    const compressed = count >= layout.rests.minimumMeasuresToCompress;
    const length=Math.max(1,...measures.map(m=>m?q(m.length):0)),meterWeight=meterWidthRatio(length,s.meterWidthBias);
    const meterInset=Math.max(0,...measures.map((m,part)=>{
      if(!m) return 0;const index=score.parts[part].measures.indexOf(m);
      return index>0 && contextChanges(score.parts[part].measures[index-1],m).meter ? meterMetrics(m,baseFont).width+layout.meter.leftInset+layout.meter.rightGap : 0;
    }));
    const spacing = measureSpacing(measures.flatMap(m => m?.events ?? []),
      length,baseFont,s,p=>{
        const glyph=accidentalGlyph(p);
        if(!glyph) return 0;
        const box=musicFont.glyphForCodePoint(glyph.codePointAt(0)!).bbox;
        return (box.maxX-box.minX)*baseFont*n.accidentalScale/musicFont.unitsPerEm+n.accidentalGap;
      },n,e=>(e as Event).marks.some(m=>m.kind==='arpeggiate' && !m.hidden) ? tech.arpeggioGap+tech.arpeggioWidth+tech.arpeggioArrowSize : 0,
      measures.find((m):m is Measure=>!!m) ?? {beats:'4',beatType:4});
    const countWidth=compressed ? (()=>{const glyphs=countGlyphs(String(count));return Math.max(...glyphs.map(g=>g.right))-Math.min(...glyphs.map(g=>g.left))+2*layout.rests.symbolInset;})() : 0;
    bars.push({...spacing,number,count:compressed ? count : 1,measures,
      width:meterInset+(compressed ? Math.max(baseFont*layout.rests.widthRatio*meterWeight,countWidth) : spacing.width),
      minimumWidth:meterInset+(compressed ? Math.max(baseFont*layout.rests.minimumWidthRatio*meterWeight,countWidth) : spacing.minimumWidth),compressed,order:i,meterInset,meterWeight});
    if (compressed) i += count - 1;
  }
  const spanRows=rows.map(row=>{
    const result=collectSpans(row.part.measures,row.voice,score.bars),tuplet=collectTuplets(row.part.measures,row.voice);
    result.warnings.push(...tuplet.warnings);
    const order=new Map(row.part.measures.flatMap(m=>m.events.map(e=>[e.id,score.bars.indexOf(m.number)] as const)));
    for(const group of tuplet.groups) {
      const existing=group.bracket ? result.spans.find(s=>s.kind==='slur' && s.start===group.start && s.end===group.end && s.placement===group.placement && !s.tuplet) : undefined;
      if(existing) existing.tuplet=group;
      else result.spans.push({kind:'tuplet',start:group.start,end:group.end,from:order.get(group.start)!,to:order.get(group.end)!,
        startIndex:result.sequence.get(group.start)!,endIndex:result.sequence.get(group.end)!,placement:group.placement,lineType:'solid',lane:0,tuplet:group});
    }
    return result;
  });
  const spans=spanRows.flatMap((result,row)=>{
    warnings.push(...result.warnings.map(w=>`${rows[row].label}: ${w}`));
    return result.spans.filter(span=>span.kind!=='grace-slur').map(span=>({...span,row}));
  });
  const localRows=new Map(localMode ? score.bars.map((number,order)=>{
    const m=lookup[0].get(number);
    const required=spans.filter(s=>s.from<=order && s.to>=order).map(s=>rows[s.row].voice);
    return [number,m?localVoiceRows(m,rows.map(r=>r.voice),primaryVoice,required):[primaryVoice]] as const;
  }) : []);
  const wedgeParts=score.parts.map(p=>collectWedges(p.measures,score.bars));
  const wedges=wedgeParts.flatMap((result,part)=>{
    warnings.push(...result.warnings);
    return result.spans.map(span=>({...span,row:rows.findIndex(r=>r.part===score.parts[part]),part}));
  });
  const tx = (value: string, x: number, y: number, size = font, opts: Record<string, unknown> = {}) => {
    doc.font('text').fontSize(size).fillColor('black').text(value, x, y, {lineBreak:false, ...opts});
  };
  const txNumber=(value: string,x: number,y: number,size=font)=>{
    doc.font('numbers').fontSize(size).fillColor('black').text(value,x,y,{lineBreak:false});
  };
  const line = (x1: number,y1: number,x2: number,y2: number,width=.7) => {
    doc.lineWidth(width).strokeColor('black').moveTo(x1,y1).lineTo(x2,y2).stroke();
  };
  const barline=(x: number,y: number,width=bl.lineWidth)=>{
    const middle=digitBounds('1',0,y,font).centerY;
    line(x,middle-font*bl.halfHeightRatio,x,middle+font*bl.halfHeightRatio,width);
  };
  const boxedNumber=(value: string,x: number,y: number)=>{
    const glyphs=styledDigits(value,measureFaces,mn.fontSize,mn.digitGap);
    const minX=Math.min(...glyphs.map(g=>g.left)),maxX=Math.max(...glyphs.map(g=>g.right));
    const minY=Math.min(...glyphs.map(g=>g.top)),maxY=Math.max(...glyphs.map(g=>g.bottom));
    const width=Math.max(mn.minimumWidth,maxX-minX+mn.paddingX*2),height=Math.max(mn.height,maxY-minY+2*mn.paddingY);
    const left=x-width/2;
    doc.lineWidth(mn.lineWidth).strokeColor('black').rect(left,y,width,height).stroke();
    for(const glyph of glyphs) doc.font(glyph.name).fontSize(mn.fontSize).text(glyph.char,
      x-(minX+maxX)/2+glyph.x,y+height/2-(minY+maxY)/2,{lineBreak:false,baseline:'alphabetic'});
    return width;
  };
  let pageY = 0;
  const addPage = () => {
    doc.addPage();
    const first = doc.bufferedPageRange().count === 1;
    tx(score.title, margin, margin, first ? t.titleSize : t.continuedTitleSize, {width:doc.page.width-margin*2, align:'center'});
    if (first) {
      tx(score.subtitle, margin, margin+h.subtitleOffsetY, t.subtitleSize, {width:doc.page.width-margin*2, align:'center'});
      tx(score.composer ? score.composer + ' 曲' : '', margin, margin+h.composerOffsetY, t.composerSize, {width:doc.page.width-margin*2, align:'right'});
    }
    const label = score.draft ? '校对初稿 · 未校验通过' : score.recognitionSource ? '自动识谱初稿 · 请与原谱核对' : '简谱转换';
    tx(label, margin, margin+(first ? h.statusOffsetY : h.continuedStatusOffsetY), t.statusSize, {width:doc.page.width-margin*2, align:'right'});
    pageY = margin + (first ? h.firstSystemOffsetY : h.continuedSystemOffsetY);
  };
  addPage();
  const labelWidth = singleVoice || localMode ? 0 : Math.max(42, Math.min(90, Math.max(...rows.map(r => {doc.font('text').fontSize(t.partLabelSize); return doc.widthOfString(r.label)+15;}))));
  const orderedVoices=[primaryVoice,...rows.map(r=>r.voice).filter(v=>v!==primaryVoice)];
  const localVoiceLabel=(voice:string)=>score.parts[0].name+(voice===primaryVoice?'I':'II');
  doc.font('text').fontSize(layout.localVoices.labelSize);
  const localLabelWidth=localMode?Math.max(...orderedVoices.map(v=>doc.widthOfString(localVoiceLabel(v))))+layout.localVoices.labelGap:0;
  const available = doc.page.width - 2*margin - labelWidth;
  const plannedSystems=planSystems(bars,available,layout.maxMeasuresPerSystem,layout.meterAwarePacking,localMode?
    indices=>indices.some(i=>localRows.get(bars[i].number)!.length===2)?available-localLabelWidth:available:undefined);
  let systems = 0;
  const systemLayout: {bars: string[]; width: number; fontSize: number; spacingRatio: number; height: number;visibleLanes:number}[] = [];
  const voiceLayout:Record<string,unknown>[]=[],eventLayout:Record<string,unknown>[]=[],voiceLabelLayout:Record<string,unknown>[]=[];
  const contextAnnotations: {part: string; voice: string; bar: string; text: string; fontSize: number; x: number; y: number}[]=[];
  let connectedUnderlineGroups = 0;
  const restLayout: {bar:string;count:number;style:string;zeros?:number}[]=[];
  const curveSegments:Record<string,unknown>[]=[];
  type CurveRequest={span:typeof spans[number];positions:Map<string,Position>;firstOrder:number;lastOrder:number;
    left:number;right:number;top:number;bottom:number;style:typeof layout.curves;page:number;system:number};
  const curveRequests:CurveRequest[]=[];
  interface UpperAnnotation {event:string;kind:string;row:number;system:number;page:number;left:number;right:number;top:number;bottom:number;noteTop?:number;details?:Record<string,unknown>;draw:(shift:number)=>void}
  const upperAnnotations:UpperAnnotation[]=[];
  const staticUpperText:{page:number;system:number;row:number;left:number;right:number;top:number;bottom:number}[]=[];
  const annotationLayout:Record<string,unknown>[]=[],underlineLayout:Record<string,unknown>[]=[],wedgeSegments:Record<string,unknown>[]=[];
  const meterLayout:Record<string,unknown>[]=[],directionLayout:Record<string,unknown>[]=[],graceLayout:Record<string,unknown>[]=[];
  const graceConnectors:Record<string,unknown>[]=[];
  const measureLayout:Record<string,unknown>[]=[];
  const techniqueLayout:Record<string,unknown>[]=[];
  const tupletLayout:Record<string,unknown>[]=[];
  type Box={left:number;right:number;top:number;bottom:number};
  const deferredDirections:{row:number;system:number;page:number;box:Box;boxes:Box[];draw:(shift:number)=>void}[]=[];
  const noteSymbols:Record<string,unknown>[]=[];
  const techniquePositions=new Map<string,Position & {page:number;system:number;size:number;bar:string}>();
  const tremoloPairs=score.parts.flatMap(part=>{
    const collected=collectTremolos(part.measures);warnings.push(...collected.warnings);
    return collected.pairs;
  });
  const drawMeter=(m:Measure,left:number,cy:number,size:number,initial:boolean,row:number,system:number)=>{
    const metrics=meterMetrics(m,size),top=cy-metrics.height/2;
    for(const [value,yy] of [[metrics.top,top],[metrics.bottom,top+metrics.glyphHeight+2*layout.meter.stackGap+layout.meter.lineWidth]] as [string,number][]) {
      const b=musicRun(value,metrics.fontSize),width=b.right-b.left;
      musicInk(value,left+(metrics.width-width)/2,yy,metrics.fontSize);
    }
    line(left,cy,left+metrics.width,cy,layout.meter.lineWidth);
    meterLayout.push({bar:m.number,beats:m.beats,beatType:m.beatType,initial,row,system,page:doc.bufferedPageRange().count,left,right:left+metrics.width,top,bottom:top+metrics.height,height:metrics.height,fontSize:metrics.fontSize,format:'fraction'});
    return metrics.width;
  };
  const engraveDirections=(m:Measure,row:number,system:number,y:number,size:number,xAt:(time:number)=>number,
    lowerAt?:(time:number)=>{cx:number;bottom:number;event?:string})=>{
    const wordBounds=new Map<number,{left:number;right:number;top:number;bottom:number}>();let lane=0;
    const directionGroups=new Map<number,{boxes:Box[];draws:((shift:number)=>void)[]}>();
    const upperTop=(left:number,width:number,top:number,height:number)=>{
      let placed=top;
      for(let attempt=0;attempt<staticUpperText.length+1;attempt++) {
        const previous=placed;
        for(const b of staticUpperText) if(b.row===row && b.system===system && b.page===doc.bufferedPageRange().count &&
          left<b.right && left+width>b.left && placed<b.bottom+2 && placed+height>b.top-2) placed=Math.min(placed,b.top-height-2);
        if(previous===placed) break;
      }
      return placed;
    };
    for(const d of [...m.directions].sort((a,b)=>q(a.start)-q(b.start) || Number(a.kind==='metronome')-Number(b.kind==='metronome'))) {
      if(d.kind==='wedge') continue;
      let dx=xAt(q(d.start));const page=doc.bufferedPageRange().count;
      const placement=d.kind==='dynamics' && dynamicsPlacement==='below' ? 'below' : d.placement;
      const fallback=digitBounds('0',dx,y,size);
      const lower=lowerAt?.(q(d.start)) ?? {cx:fallback.centerX,bottom:fallback.bottom};
      const callbacks:((shift:number)=>void)[]=[],extraBoxes:Box[]=[];
      const dyn=d.kind==='dynamics' ? dynamicGlyph(d.text) : null;
      let box:{left:number;right:number;top:number;bottom:number},face:string,drawSize:number;
      const yy=y-layout.terms.offsetY-lane*layout.terms.laneGap;
      if(dyn) {
        face='music';drawSize=layout.terms.dynamicsSize*size/baseFont;
        const ink=musicRun(dyn,drawSize);
        if(placement!=='above') dx=lower.cx-(ink.right-ink.left)/2;
        const top=placement==='above'?upperTop(dx,ink.right-ink.left,yy,ink.bottom-ink.top):lower.bottom+layout.terms.dynamicsGap;
        box={left:dx,right:dx+ink.right-ink.left,top,bottom:top+ink.bottom-ink.top};
        callbacks.push(shift=>{musicInk(dyn,dx,top+shift,drawSize);});
        if(placement==='above') lane++;
      } else if(d.kind==='metronome') {
        const [unit,rate]=d.text.split('='),glyph=metronomeGlyph(d.beatUnit ?? unit);
        const paired=wordBounds.get(q(d.start));
        if(paired) dx=paired.right+8;
        let top=paired ? paired.top : yy;
        const notes=glyph ? glyph+'\uECB7'.repeat(d.beatDots ?? 0) : '';
        if(!paired && notes) {const ink=musicRun(notes,layout.terms.metronomeSize);top=upperTop(dx,ink.right-ink.left+35,top,Math.max(ink.bottom-ink.top,layout.terms.metronomeTextSize*1.2));}
        const noteInk=notes?musicRun(notes,layout.terms.metronomeSize):{left:0,right:0,top:0,bottom:0};
        const noteBox={left:dx,right:dx+noteInk.right-noteInk.left,top,bottom:top+noteInk.bottom-noteInk.top};
        if(notes) callbacks.push(shift=>{musicInk(notes,dx,top+shift,layout.terms.metronomeSize);});
        const label=`= ${d.perMinute || rate || '?'}`;
        drawSize=layout.terms.metronomeTextSize*size/baseFont;face=termFonts.regular;
        doc.font(face).fontSize(drawSize);const width=doc.widthOfString(label),fontFace=activeGlyphFont();
        const inks=typeof fontFace.glyphForCodePoint==='function' ? [...label].filter(c=>c!==' ').map(c=>fontFace.glyphForCodePoint(c.codePointAt(0)!).bbox) : [];
        const unitScale=drawSize/(fontFace.unitsPerEm || 1000);
        const minY=inks.length ? Math.min(...inks.map(b=>-b.maxY*unitScale)) : -(doc as unknown as {_font:{capHeight:number}})._font.capHeight*drawSize/1000;
        const maxY=inks.length ? Math.max(...inks.map(b=>-b.minY*unitScale)) : 0;
        const baseline=noteBox.bottom-maxY;
        const textX=noteBox.right+3,textFace=face,textSize=drawSize;
        callbacks.push(shift=>{doc.font(textFace).fontSize(textSize).text(label,textX,baseline+shift,{lineBreak:false,baseline:'alphabetic'});});
        const textBox={left:noteBox.right+3,right:noteBox.right+3+width,top:baseline+minY,bottom:baseline+maxY};
        box={left:dx,right:textBox.right,top:Math.min(noteBox.top,textBox.top),bottom:Math.max(noteBox.bottom,textBox.bottom)};
        directionLayout.push({bar:m.number,kind:'metronome-components',text:d.text,row,system,page,noteBox,textBox});
        extraBoxes.push(noteBox,textBox);
        if(!paired) lane++;
      } else {
        const tempo=isTempoTerm(d.text),latin=/^[\u0000-\u024f\s]+$/.test(d.text);
        const bold=d.fontWeight==='bold' || (!d.fontWeight && tempo),italic=d.fontStyle==='italic' || (!d.fontStyle && !tempo);
        face=latin ? (bold ? (italic?termFonts.boldItalic:termFonts.bold) : italic?termFonts.italic:termFonts.regular) : 'text';
        drawSize=tempo?layout.terms.tempoSize:layout.terms.expressionSize;
        const label=d.kind==='rehearsal'?`[${d.text}]`:d.text;
        doc.font(face).fontSize(drawSize);const width=doc.widthOfString(label);
        if(d.kind==='dynamics' && placement!=='above') dx=lower.cx-width/2;
        const top=d.kind==='dynamics' && placement!=='above'?lower.bottom+layout.terms.dynamicsGap:upperTop(dx,width,yy,drawSize*1.2);
        const textFace=face,textSize=drawSize;
        callbacks.push(shift=>{doc.font(textFace).fontSize(textSize).text(label,dx,top+shift,{lineBreak:false});});
        box={left:dx,right:dx+width,top,bottom:top+drawSize*1.2};
        if(d.kind!=='dynamics') {wordBounds.set(q(d.start),box);lane++;}
        if(['bracket','dashes'].includes(d.kind)) warnings.push(`Bar ${m.number}: ${d.kind} requires manual review`);
      }
      const record={bar:m.number,kind:d.kind,text:d.text,font:face,fontSize:drawSize,row,system,page,...box,
        ...(d.kind==='dynamics'?{placement:placement ?? 'below',sourcePlacement:d.placement ?? null,start:d.start,
          anchorEvent:lower.event,anchorX:lower.cx,anchorBottom:lower.bottom}: {})};
      directionLayout.push(record);
      if(d.kind!=='dynamics' || placement==='above') {
        const staticBox={row,system,page,...box};staticUpperText.push(staticBox);
        const key=q(d.start);if(!directionGroups.has(key)) directionGroups.set(key,{boxes:[],draws:[]});
        const group=directionGroups.get(key)!;group.boxes.push(record,staticBox,...extraBoxes);group.draws.push(...callbacks);
      } else callbacks.forEach(draw=>draw(0));
    }
    for(const group of directionGroups.values()) {
      const box={left:Math.min(...group.boxes.map(b=>b.left)),right:Math.max(...group.boxes.map(b=>b.right)),
        top:Math.min(...group.boxes.map(b=>b.top)),bottom:Math.max(...group.boxes.map(b=>b.bottom))};
      deferredDirections.push({row,system,page:doc.bufferedPageRange().count,box,boxes:group.boxes,draw:shift=>group.draws.forEach(draw=>draw(shift))});
    }
  };
  const frames:{row:number;lane?:number;order:number;length:number;absolute:number;page:number;system:number;left:number;right:number;y:number;font:number;xAt:(time:number)=>number}[]=[];
  for (const indices of plannedSystems) {
    const systemBars=indices.map(i=>bars[i]);
    const pairedSystem=localMode && systemBars.some(b=>localRows.get(b.number)!.length===2);
    const systemLabelWidth=pairedSystem?localLabelWidth:labelWidth;
    const systemAvailable=available-(systemLabelWidth-labelWidth);
    const displayedVoices=(bar:Bar)=>pairedSystem?orderedVoices.filter(v=>bar.measures[0]?.events.some(e=>e.voice===v)):localRows.get(bar.number)!;
    const voiceLane=(bar:Bar,voice:string)=>pairedSystem?orderedVoices.indexOf(voice):displayedVoices(bar).indexOf(voice);
    const totalWidth=systemBars.reduce((sum,b)=>sum+b.width,0);
    const isLast=indices===plannedSystems.at(-1);
    const systemWidth=isLast && !layout.justifyLastSystem ? Math.min(systemAvailable,totalWidth) : systemAvailable;
    const minimumWidth=systemBars.reduce((sum,b)=>sum+b.minimumWidth,0);
    const denseScale=Math.min(1,systemAvailable/minimumWidth);
    // Interpolate white space down to its lower bound without shrinking digits.
    const compression=totalWidth>systemAvailable ? Math.min(1,(totalWidth-systemAvailable)/Math.max(1e-8,totalWidth-minimumWidth)) : 0;
    const adjustedWidth=totalWidth-compression*(totalWidth-minimumWidth);
    const scale=systemWidth/adjustedWidth;
    font=baseFont*denseScale;
    if(denseScale<1) warnings.push(`Bar ${systemBars[0].number} exceeds minimum readable width; inspect dense notation`);
    if(font<8) throw new Error(`Bar ${systemBars[0].number} cannot fit legibly; use A3 or correct merged OMR bars`);
    const activeRows=rows.map((_,i)=>i).filter(ri=>{
      const row=rows[ri];
      if(localMode) return systemBars.some(b=>displayedVoices(b).includes(row.voice));
      const partHasNotes=systemBars.some(b=>row.part.measures.find(m=>m.number===b.number)?.events.some(e=>e.kind!=='rest'));
      const voiceHasNotes=systemBars.some(b=>row.part.measures.find(m=>m.number===b.number)?.events.some(e=>e.voice===row.voice && e.kind!=='rest'));
      return voiceHasNotes || (!partHasNotes && rows.findIndex(r=>r.part.id===row.part.id)===ri);
    });
    const activeSet=new Set(activeRows);
    const chordSizes = rows.map(r => Math.max(1,...systemBars.flatMap(b =>
      r.part.measures.find(m => m.number===b.number)?.events.filter(e=>e.voice===r.voice).map(e=>e.pitches.length) ?? [])));
    const rowHeights = rows.map((_,ri) => activeSet.has(ri) ? s.rowHeight + (chordSizes[ri]-1)*font*s.chordSpacingRatio : 0);
    const laneCount=localMode ? Math.max(...systemBars.map(b=>localRows.get(b.number)!.length)) : activeRows.length;
    const laneChords=Array.from({length:laneCount},(_,lane)=>Math.max(1,...systemBars.flatMap(b=>{
      const voice=localMode?(pairedSystem?orderedVoices[lane]:localRows.get(b.number)?.[lane]):undefined;
      return voice?b.measures[0]?.events.filter(e=>e.voice===voice).map(e=>e.pitches.length) ?? []:[];
    })));
    const laneHeights=laneChords.map((chord,i)=>(i<laneCount-1?Math.max(s.rowHeight,layout.localVoices.rowGap):s.rowHeight)+(chord-1)*font*s.chordSpacingRatio);
    const height = (localMode?laneHeights:rowHeights).reduce((a,b) => a+b,0) + s.systemGap;
    if (height > doc.page.height - margin*2 - 80) throw new Error('System is taller than a page; use fewer voices or A3');
    if (pageY + height > doc.page.height - margin - 25) addPage();
    const baselines: number[] = [];
    let ry = pageY;
    rows.forEach((row, ri) => {baselines.push(ry+s.baselineOffset+(chordSizes[ri]-1)*font*s.chordSpacingRatio); ry += rowHeights[ri];});
    let laneY=pageY;
    const laneBaselines=laneChords.map((chord,i)=>{const y=laneY+s.baselineOffset+(chord-1)*font*s.chordSpacingRatio;laneY+=laneHeights[i];return y;});
    if(localMode) rows.forEach((row,ri)=>{const lane=Math.max(0,...systemBars.map(b=>voiceLane(b,row.voice)));baselines[ri]=laneBaselines[lane];});
    const left = margin + systemLabelWidth;
    const right = left+systemWidth;
    systemLayout.push({bars:systemBars.map(b=>b.number),width:systemWidth,fontSize:font,spacingRatio:systemWidth/totalWidth,height,visibleLanes:laneCount});
    const top = (pairedSystem?Math.min(...laneBaselines):baselines[activeRows[0]])-22;
    const bottom = (pairedSystem?Math.max(...laneBaselines):baselines[activeRows.at(-1)!]) + font + 8;
    // Connect this system's part rows, but retain every row's own musical time.
    if(!singleVoice && !localMode) {
      line(margin+labelWidth-6, top, margin+labelWidth-6, bottom, 1.1);
      rows.forEach((row, ri) => {
        if(!activeSet.has(ri)) return;
        tx(row.label, margin, baselines[ri], t.partLabelSize, {width:labelWidth-10, align:'right'});
      });
    }
    if(pairedSystem) {
      for(const [lane,voice] of orderedVoices.entries()) {
        const text=localVoiceLabel(voice),size=layout.localVoices.labelSize;
        doc.font('text').fontSize(size);const width=doc.widthOfString(text);
        const x=left-layout.localVoices.labelGap-width;
        const y=digitBounds('0',0,laneBaselines[lane],font).centerY-glyphBounds(textFont,text,0,0,size).centerY;
        tx(text,x,y,size);
        voiceLabelLayout.push({text,voice,lane,system:systems+1,page:doc.bufferedPageRange().count,x,y,right:x+width,musicLeft:left,fontSize:size});
      }
      const groupTop=digitBounds('0',0,laneBaselines[0],font).centerY-font*bl.halfHeightRatio;
      const groupBottom=digitBounds('0',0,laneBaselines.at(-1)!,font).centerY+font*bl.halfHeightRatio;
      line(left,groupTop,left,groupBottom,bl.lineWidth);
    }
    const numberBoxWidth=boxedNumber(systemBars[0].number,left,(localMode?laneBaselines[0]-(laneChords[0]-1)*font*s.chordSpacingRatio:baselines[activeRows[0]]-(chordSizes[activeRows[0]]-1)*font*s.chordSpacingRatio)-mn.offsetY);
    let x = left;
    const positions = new Map<string, Position>();
    for (const bar of systemBars) {
      const columns=bar.columns.map((column,i)=>column-compression*(column-bar.minimumColumns[i]));
      const width = (bar.width-compression*(bar.width-bar.minimumWidth))*scale;
      const measureLeft=x;
      measureLayout.push({bar:bar.number,count:bar.count,page:doc.bufferedPageRange().count,system:systems+1,left:x,right:x+width,width,
        contentWidth:width-scale*bar.meterInset,preferredWidth:bar.width,minimumWidth:bar.minimumWidth,idealWidth:bar.idealWidth,meterWeight:bar.meterWeight,
        beats:bar.measures.find(m=>m)?.beats,beatType:bar.measures.find(m=>m)?.beatType,compressed:bar.compressed});
      rows.forEach((row, ri) => {
        if(!activeSet.has(ri)) return;
        const lane=localMode?voiceLane(bar,row.voice):ri;
        if(localMode && !displayedVoices(bar).includes(row.voice)) return;
        const m = row.part.measures.find(m => m.number === bar.number);
        const y = localMode?laneBaselines[lane]:baselines[ri];
        const meterPrefix=scale*bar.meterInset;
        barline(x,y);
        if (!m) {tx('缺失小节 ?',x+8,y,t.repeatSize); return;}
        const shownDirections=localMode?m.directions.filter(d=>d.voice?d.voice===row.voice:displayedVoices(bar)[0]===row.voice):m.directions;
        const directionMeasure=localMode?{...m,directions:shownDirections}:m;
        if(localMode) {
          voiceLayout.push({bar:bar.number,voice:row.voice,row:ri,lane,y,left:x,right:x+width,page:doc.bufferedPageRange().count,system:systems+1,dual:localRows.get(bar.number)!.length===2,pairedSystem});
          barline(x+width,y);
        }
        const mi=row.part.measures.indexOf(m);
        const changes=contextChanges(row.part.measures[mi-1],m);
        const annotation=[changes.key ? keyLabel(m) : '',changes.meter ? `${m.beats}/${m.beatType}` : ''].filter(Boolean).join('  ');
        if(annotation && (!localMode || lane===0)) {
          const initial=mi===0;
          const annotationSize=initial ? c.initialFontSize : c.changeFontSize;
          doc.font('text').fontSize(annotationSize);
          const annotationX=x+(initial ? c.initialOffsetX : c.changeOffsetX);
          const annotationY=y-(chordSizes[ri]-1)*font*s.chordSpacingRatio-(initial ? c.initialOffsetY : c.changeOffsetY);
          if(initial) {
            const key=keyLabel(m);tx(key,annotationX,annotationY,annotationSize);
            doc.font('text').fontSize(annotationSize);
            drawMeter(m,annotationX+doc.widthOfString(key)+layout.meter.initialGap,annotationY+annotationSize*.6,font,true,ri,systems+1);
          } else {
            if(changes.key) tx(keyLabel(m),annotationX,annotationY,annotationSize);
            if(changes.meter) drawMeter(m,x+layout.meter.leftInset,digitBounds('1',0,y,font).centerY,font,false,ri,systems+1);
          }
          contextAnnotations.push({part:row.part.id,voice:row.voice,bar:bar.number,text:annotation,fontSize:annotationSize,x:annotationX,y:annotationY});
        }
        if (bar.compressed) {
          const part=score.parts.indexOf(row.part),length=q(m.length);
          for(let i=0;i<bar.count;i++) {
            const number=score.bars[bar.order+i];
            frames.push({row:ri,lane,order:bar.order+i,length,absolute:wedgeParts[part].offsets.get(number)!,page:doc.bufferedPageRange().count,
              system:systems+1,left:measureLeft+width*i/bar.count,right:measureLeft+width*(i+1)/bar.count,y,font,
              xAt:time=>measureLeft+width*(i+time/length)/bar.count});
          }
          const r=layout.rests;
          const yy=digitBounds('1',0,y,font).centerY;
          line(x+meterPrefix+r.symbolInset,yy,x+width-r.symbolInset,yy,r.lineWidth);
          line(x+meterPrefix+r.symbolInset,yy-r.capHeight/2,x+meterPrefix+r.symbolInset,yy+r.capHeight/2,r.capWidth);
          line(x+width-r.symbolInset,yy-r.capHeight/2,x+width-r.symbolInset,yy+r.capHeight/2,r.capWidth);
          const glyphs=countGlyphs(String(bar.count));
          const center=(Math.min(...glyphs.map(g=>g.left))+Math.max(...glyphs.map(g=>g.right)))/2;
          const bottom=Math.max(...glyphs.map(g=>g.bottom));
          const baseline=yy-r.countGap-bottom;
          for(const glyph of glyphs) doc.font(glyph.name).fontSize(t.restCountSize).text(glyph.char,x+(width+meterPrefix)/2-center+glyph.x,baseline,{lineBreak:false,baseline:'alphabetic'});
          for(const event of m.events.filter(e=>e.voice===row.voice)) positions.set(event.id,{x:x+width/2,y,
            anchorX:x+width/2,top:baseline+Math.min(...glyphs.map(g=>g.top)),bottom:yy+r.capHeight/2,
            sequence:spanRows[ri].sequence.get(event.id)!,row:ri,order:bar.order});
          const last=row.part.measures.find(m=>m.number===score.bars[bar.order+bar.count-1]);
          if(last?.barlines.some(b=>b.style==='light-heavy')) barline(x+width-3,y,1.6);
          engraveDirections(directionMeasure,ri,systems+1,y,font,()=>measureLeft+meterPrefix+12);
          restLayout.push({bar:bar.number,count:bar.count,style:'multi-measure'});return;
        }
        const rawTimeX = (t: number) => {
          return measureLeft+scale*(bar.meterInset+bar.leftPadding+offsetAt(t,bar.times,columns));
        };
        const voiceEvents=m.events.filter(e => e.voice === row.voice);
        const zeroCount=(!localMode || !pairedSystem) && fullMeasureRest({...m,events:voiceEvents}) && m.beatType===4 && !voiceEvents.some(e=>e.marks.length) ? Number(m.beats) : 0;
        if(Number.isInteger(zeroCount) && zeroCount>0) {
          const inset=layout.rests.zeroInset;
          const digit=digitBounds('0',0,0,font);
          const middle=digitBounds('1',0,y,font).centerY;
          for(let beat=0;beat<zeroCount;beat++) {
            const cx=x+meterPrefix+inset+(width-meterPrefix-2*inset)*(beat+.5)/zeroCount;
            txNumber('0',cx-digit.centerX,middle-digit.centerY,font);
          }
          restLayout.push({bar:bar.number,count:1,style:'zeros',zeros:zeroCount});
          for(const event of voiceEvents) positions.set(event.id,{x:x+width/2,y,anchorX:x+width/2,
            top:middle-digit.centerY+digit.top,bottom:middle-digit.centerY+digit.bottom,
            sequence:spanRows[ri].sequence.get(event.id)!,row:ri,order:bar.order});
        }
        // Center the visible note group, including accidentals, underlines and
        // continuation dashes. Keep the relative rhythmic spacing unchanged.
        const extents: {left:number;right:number}[]=[];
        for(const event of localMode?m.events.filter(e=>displayedVoices(bar).includes(e.voice)):voiceEvents) {
          const small=event.kind==='grace'; const size=small ? font*n.graceScale : font;
          const ex=alignDigitX(String(event.pitches[0]?.degree ?? 0),rawTimeX(bar.graceTimes.get(event.id) ?? q(event.start))+(bar.graceOffsets.get(event.id) ?? 0),y,size);
          const values=event.pitches.length ? event.pitches : [{degree:0,accidental:'0'}];
          for(const p of values) {
            const digit=digitBounds(String(p.degree),ex,y,size);
            let left=digit.left;
            if('displayAccidental' in p || q(p.accidental)!==0) {
              const glyph=accidentalGlyph(p as Pitch);
              if(glyph) {
                const symbol=musicFont.glyphForCodePoint(glyph.codePointAt(0)!).bbox;
                left=digit.left-n.accidentalGap-(symbol.maxX-symbol.minX)*size*n.accidentalScale/musicFont.unitsPerEm;
              } else if(q(p.accidental)!==0) left=ex-13;
            }
            extents.push({left,right:digit.right});
          }
          if(event.marks.some(m=>m.kind==='arpeggiate' && !m.hidden)) extents.push({
            left:Math.min(...extents.slice(-values.length).map(e=>e.left))-tech.arpeggioGap-tech.arpeggioWidth*1.5-tech.arpeggioArrowSize,right:ex});
          if(event.noteType in {eighth:1,'16th':1,'32nd':1,'64th':1,'128th':1}) extents.push({left:ex-n.underlineLeftExtension,right:ex+size*n.underlineLengthRatio});
          if(q(event.duration)<2 && event.dots) extents.push({left:ex,right:ex+size*(n.underlineLengthRatio+event.dots*s.augmentationSpaceRatio)});
          if(!small && q(event.duration)>=2) {
            const count=Math.min(7,Math.floor(q(event.duration))-1);
            for(let d=0;d<count;d++) {
              const dx=rawTimeX(q(event.start)+d+1);
              const glyph=event.kind==='rest' ? digitBounds('0',dx,y,size) : {left:dx,right:dx+size*n.dashLengthRatio};
              extents.push(glyph);
            }
          }
        }
        const centerShift=(singleVoice || localMode) && extents.length ? x+(width+meterPrefix)/2-(Math.min(...extents.map(e=>e.left))+Math.max(...extents.map(e=>e.right)))/2 : 0;
        const timeX=(t: number)=>rawTimeX(t)+centerShift;
        const part=score.parts.indexOf(row.part),frameFont=font;
        frames.push({row:ri,lane,order:bar.order,length:q(m.length),absolute:wedgeParts[part].offsets.get(bar.number)!,page:doc.bufferedPageRange().count,
          system:systems+1,left:measureLeft,right:measureLeft+width,y,font,xAt:time=>time>=q(m.length)-1e-8 ? measureLeft+width : localMode?digitBounds('0',timeX(time),y,frameFont).centerX:digitBounds(String(voiceEvents.find(e=>e.kind!=='grace' && Math.abs(q(e.start)-time)<1e-8)?.pitches[0]?.degree ?? 0),timeX(time),y,frameFont).centerX});
        const groups=underlineGroups(zeroCount>0 ? [] : voiceEvents,m.beats,m.beatType);
        const underlineGeometry=new Map<string,{y:number;bottom:number}>();
        for(const group of groups) {
          const small=group.events[0].kind==='grace';
          const size=small ? font*n.graceScale : font;
          const beamY=Math.max(...group.events.map(e=>digitBounds(String(e.pitches[0]?.degree ?? 0),0,y+(small ? -n.graceOffsetY : 0),size).bottom))+n.underlineGap;
          const beamBottom=beamY+Math.max(...group.segments.map(s=>s.level))*n.underlineLayerGap;
          group.events.forEach(e=>underlineGeometry.set(e.id,{y:beamY,bottom:beamBottom}));
        }
        for (const event of zeroCount>0 ? [] : voiceEvents) {
          let ex=timeX(bar.graceTimes.get(event.id) ?? q(event.start));
          ex+=bar.graceOffsets.get(event.id) ?? 0;
          const small=event.kind==='grace';
          const size=small ? font*n.graceScale : font;
          const ey=small ? y-n.graceOffsetY : y;
          ex=alignDigitX(String(event.pitches[0]?.degree ?? 0),ex,ey,size);
          const firstDigit=digitBounds(String(event.pitches[0]?.degree ?? 0),ex,ey,size);
          const position:Position={x:ex,y,anchorX:firstDigit.centerX,top:firstDigit.top,bottom:firstDigit.bottom,
            sequence:spanRows[ri].sequence.get(event.id)!,row:ri,order:bar.order};
          positions.set(event.id,position);
          if (event.kind==='rest') {
            txNumber('0',ex,ey,size);
            if (q(event.duration)>=2) {
              const n=Math.min(7,Math.floor(q(event.duration))-1);
              for(let d=0;d<n;d++) txNumber('0',timeX(q(event.start)+d+1),y,size);
            }
          } else if (!event.pitches.length) txNumber('?',ex,ey,size);
          else {
            const pitches=[...event.pitches].sort((a,b) => (a.octave*7+a.degree)-(b.octave*7+b.degree));
            pitches.forEach((p,pi) => {
              const py=ey-pi*size*s.chordSpacingRatio;
              const digit=digitBounds(String(p.degree),ex,py,size);
              position.top=Math.min(position.top,digit.top);position.bottom=Math.max(position.bottom,digit.bottom);
              const alteration=q(p.accidental);
              if(alteration || p.displayAccidental==='natural') {
                const glyph=accidentalGlyph(p);
                if(glyph) {
                  const accidentalSize=size*n.accidentalScale;
                  const symbol=musicFont.glyphForCodePoint(glyph.codePointAt(0)!).bbox;
                  const unit=accidentalSize/musicFont.unitsPerEm;
                  const targetCenterY=digit.top+size*n.accidentalTopOffsetRatio;
                  position.top=Math.min(position.top,targetCenterY-(symbol.maxY-symbol.minY)*unit/2);
                  const ax=digit.left-n.accidentalGap-symbol.maxX*unit;
                  const ay=targetCenterY+(symbol.minY+symbol.maxY)*unit/2;
                  doc.font('music').fontSize(accidentalSize).text(glyph,ax,ay,{lineBreak:false,baseline:'alphabetic'});
                }
                else tx(String(alteration),ex-13,py-3,t.microtoneSize);
              }
              txNumber(String(p.degree),ex,py,size);
              const dotDirection=p.octaveDots>=0 ? -1 : 1;
              const dotStart=p.octaveDots>=0 ? digit.top-n.upperDotGap : Math.max(digit.bottom,underlineGeometry.get(event.id)?.bottom ?? digit.bottom)+n.lowerDotGap;
              if(p.octaveDots>0) position.top=Math.min(position.top,dotStart-(Math.min(5,p.octaveDots)-1)*n.dotStackGap-n.dotRadius);
              if(p.octaveDots<0) position.bottom=Math.max(position.bottom,dotStart+(Math.min(5,-p.octaveDots)-1)*n.dotStackGap+n.dotRadius);
              for(let dot=0;dot<Math.min(5,Math.abs(p.octaveDots));dot++) {
                const cy=dotStart+dotDirection*dot*n.dotStackGap;
                doc.circle(digit.centerX,cy,n.dotRadius).fill();
                noteSymbols.push({event:event.id,kind:'octave-dot',direction:dotDirection,cx:digit.centerX,cy,row:ri,page:doc.bufferedPageRange().count,system:systems+1});
              }
            });
            const duration=q(event.duration);
            if(!small && duration>=2) {
              const dashes=Math.min(7,Math.floor(duration)-1);
              const middle=digitBounds(String(pitches[0].degree),ex,y,size).centerY;
              for(let d=0;d<dashes;d++) {
                const dashX=timeX(q(event.start)+d+1);
                line(dashX,middle,dashX+size*n.dashLengthRatio,middle,n.dashWidth);
                position.tail={right:dashX+size*n.dashLengthRatio,y:middle};
              }
            }
          }
          position.bottom=Math.max(position.bottom,underlineGeometry.get(event.id)?.bottom ?? position.bottom);
          techniquePositions.set(event.id,{...position,page:doc.bufferedPageRange().count,system:systems+1,size,bar:m.number});
          if(small) graceLayout.push({event:event.id,bar:m.number,anchor:event.grace?.anchorId,position:event.grace?.position ?? 'before',duration:event.duration,start:event.start,
            x:ex,top:position.top,bottom:position.bottom,row:ri,page:doc.bufferedPageRange().count,system:systems+1,measureLeft:measureLeft+meterPrefix,measureRight:measureLeft+width});
          if(q(event.duration)<2 && event.dots) {
            txNumber('.'.repeat(event.dots),ex+size*n.underlineLengthRatio,ey,size);
            noteSymbols.push({event:event.id,kind:'augmentation-dot',count:event.dots,row:ri,page:doc.bufferedPageRange().count,system:systems+1});
          }
          const queueText=(label:string,my:number,textSize:number,kind:string)=>{
            doc.font('text').fontSize(textSize);
            upperAnnotations.push({event:event.id,kind,row:ri,system:systems+1,page:doc.bufferedPageRange().count,
              left:ex,right:ex+doc.widthOfString(label),top:my,bottom:my+textSize*1.2,noteTop:position.top,
              draw:shift=>tx(label,ex,my+shift,textSize),details:{mode:'text',label,attachment:'note'}});
          };
          let markLane=0;
          const arpeggios=new Set<string>();
          for(const mark of event.marks) {
            if(['slur','tied','grace-slur'].includes(mark.kind)) continue;
            const reason=suppressionReason(mark,row.part.instrumentFamily ?? 'unknown',policy);
            if(reason) {
              techniqueLayout.push({event:event.id,bar:m.number,part:row.part.id,family:row.part.instrumentFamily ?? 'unknown',kind:mark.kind,action:'suppress',reason,row:ri,page:doc.bufferedPageRange().count,system:systems+1});
              continue;
            }
            const my=position.top-tech.ornamentGap-tech.textSize*1.2-markLane*10;
            if(mark.kind==='tuplet') continue;
            const queue=(left:number,right:number,top:number,bottom:number,draw:(shift:number)=>void,details?:Record<string,unknown>)=>
              upperAnnotations.push({event:event.id,kind:mark.kind,row:ri,system:systems+1,page:doc.bufferedPageRange().count,left,right,top,bottom,noteTop:position.top,draw,
                details:{attachment:'note',noteTop:position.top,baseBottom:bottom,...details}});
            if(mark.kind==='staccato') {
              const cy=position.top-tech.ornamentGap-1.1-markLane*10;
              queue(firstDigit.centerX-1.1,firstDigit.centerX+1.1,cy-1.1,cy+1.1,shift=>doc.circle(firstDigit.centerX,cy+shift,1.1).fill());
            } else if(mark.kind==='tenuto') {
              const yy=position.top-tech.ornamentGap-.4-markLane*10;
              queue(ex,ex+size*.6,yy-.4,yy+.4,shift=>line(ex,yy+shift,ex+size*.6,yy+shift));
            }
            else if(['inverted-mordent','mordent','fermata','trill-mark'].includes(mark.kind)) {
              const glyphs:Record<string,string>={'inverted-mordent':'\uE56C','mordent':'\uE56D','fermata':'\uE4C0','trill-mark':'\uE566'};
              const glyph=glyphs[mark.kind],box=musicRun(glyph,size),width=box.right-box.left,height=box.bottom-box.top;
              const left=firstDigit.centerX-width/2,bottom=position.top-tech.ornamentGap-markLane*10,top=bottom-height;
              const accidental=({flat:'\uE260',sharp:'\uE262',natural:'\uE261'} as Record<string,string>)[mark.ornamentAccidental ?? ''];
              const ab=accidental?musicRun(accidental,size*.65):null;
              const aw=ab?ab.right-ab.left:0,ah=ab?ab.bottom-ab.top:0;
              const ax=firstDigit.centerX-aw/2,at=top-1-ah;
              queue(Math.min(left,ax),Math.max(left+width,ax+aw),ab?at:top,bottom,shift=>{
                musicInk(glyph,left,top+shift,size);
                if(accidental) musicInk(accidental,ax,at+shift,size*.65);
              },{mode:'music-glyph',glyphCode:glyph.codePointAt(0)!.toString(16),attachment:'note',noteTop:position.top,
                baseBottom:bottom,ornamentAccidental:mark.ornamentAccidental ?? null});
            }
            else if(mark.kind==='arpeggiate') {
              const key=(mark.number ?? '1')+':'+(mark.direction ?? '');
              if(arpeggios.has(key)) continue;arpeggios.add(key);
              const chord=event.pitches.map((p,i)=>digitBounds(String(p.degree),ex,ey-i*size*s.chordSpacingRatio,size));
              const top=Math.min(...chord.map(p=>p.top)),bottom=Math.max(...chord.map(p=>p.bottom));
              const accidentalLeft=Math.min(...event.pitches.map(p=>{
                const digit=digitBounds(String(p.degree),ex,ey,size),glyph=accidentalGlyph(p);
                if(!glyph) return digit.left;
                const box=musicFont.glyphForCodePoint(glyph.codePointAt(0)!).bbox;
                return digit.left-n.accidentalGap-(box.maxX-box.minX)*size*n.accidentalScale/musicFont.unitsPerEm;
              }),firstDigit.left);
              const ax=accidentalLeft-tech.arpeggioGap-tech.arpeggioWidth/2;
              doc.save().lineWidth(tech.lineWidth).strokeColor('black');
              const waves=Math.max(1,Math.ceil((bottom-top)/tech.arpeggioWaveHeight)),step=(bottom-top)/waves;
              doc.moveTo(ax,top);
              for(let i=0;i<waves;i++) {
                const yy=top+i*step;
                doc.bezierCurveTo(ax-tech.arpeggioWidth,yy+step/4,ax+tech.arpeggioWidth,yy+3*step/4,ax,yy+step);
              }
              doc.stroke();
              if(mark.direction==='up' || mark.direction==='down') {
                const yy=mark.direction==='up'?top:bottom,d=mark.direction==='up'?1:-1,a=tech.arpeggioArrowSize;
                doc.moveTo(ax-a,yy+d*a).lineTo(ax,yy).lineTo(ax+a,yy+d*a).stroke();
              }
              doc.restore();
              techniqueLayout.push({event:event.id,bar:m.number,kind:mark.kind,action:'draw',mode:'vector-arpeggio',direction:mark.direction || null,
                left:ax-tech.arpeggioWidth,right:ax+tech.arpeggioWidth,top,bottom,row:ri,page:doc.bufferedPageRange().count,system:systems+1});
            } else if(mark.kind==='tremolo') {
              if(mark.type==='start' || mark.type==='stop') continue;
              const strokes=tremoloStrokes(mark);
              if(strokes===null) {
                queueText(techniqueText(mark),my,tech.textSize,mark.kind);
                warnings.push(`${event.id}: unmeasured or invalid tremolo rendered as text`);
              } else {
                const left=firstDigit.centerX-tech.tremoloWidth/2,right=left+tech.tremoloWidth;
                const top=position.top-tech.aboveGap-tech.tremoloRise-(strokes-1)*tech.tremoloGap-markLane*10;
                queue(left,right,top,top+tech.tremoloRise+(strokes-1)*tech.tremoloGap,
                  shift=>{for(let i=0;i<strokes;i++) line(left,top+shift+tech.tremoloRise+i*tech.tremoloGap,right,top+shift+i*tech.tremoloGap,tech.lineWidth);},
                  {mode:'vector-tremolo',strokes,type:mark.type || 'single'});
              }
            } else if(techniqueGlyph(mark)) {
              const glyph=techniqueGlyph(mark)!,sz=size*tech.symbolSizeRatio,box=musicRun(glyph,sz);
              const width=box.right-box.left,height=box.bottom-box.top,left=firstDigit.centerX-width/2;
              const top=position.top-tech.ornamentGap-height-markLane*10;
              queue(left,left+width,top,top+height,shift=>{musicInk(glyph,left,top+shift,sz);},
                {mode:'music-glyph',glyphCode:glyph.codePointAt(0)!.toString(16),fontSize:sz,attachment:'note',noteTop:position.top,baseBottom:top+height});
            } else {
              const labels:Record<string,string>={'trill-mark':'tr','tremolo':'///','fermata':'延长','accent':'>','strong-accent':'^','breath-mark':',','double-tongue':'双吐','triple-tongue':'三吐','up-bow':'上弓','down-bow':'下弓'};
              queueText(mark.kind==='harmonic' ? techniqueText(mark) : mark.label || labels[mark.kind] || techniqueText(mark),my,tech.textSize,mark.kind);
              if(!(mark.kind in labels) && !['fingering','pluck','other-technical'].includes(mark.kind)) warnings.push(`Bar ${bar.number}: ${mark.kind} rendered as text`);
            }
            markLane++;
          }
        }
        for (const group of groups) {
          if(group.events.length>1) connectedUnderlineGroups++;
          const small=group.events[0].kind==='grace';
          const size=small ? font*n.graceScale : font;
          const underlineY=underlineGeometry.get(group.events[0].id)!.y;
          for(const segment of group.segments) {
            const first=positions.get(segment.first)!; const last=positions.get(segment.last)!;
            line(first.x-n.underlineLeftExtension,underlineY+segment.level*n.underlineLayerGap,last.x+size*n.underlineLengthRatio,underlineY+segment.level*n.underlineLayerGap,n.underlineWidth);
            underlineLayout.push({bar:bar.number,row:ri,level:segment.level,start:segment.first,end:segment.last,
              source:group.events.length>1 && group.events.some(e=>e.kind==='rest') ? 'rest-beat' : group.events.some(e=>e.beams!=null)?'input':'fallback',
              group:group.events.map(e=>({id:e.id,kind:e.kind,start:e.start,duration:e.duration})),
              x1:first.x-n.underlineLeftExtension,x2:last.x+size*n.underlineLengthRatio});
          }
        }
        engraveDirections(directionMeasure,ri,systems+1,y-(chordSizes[ri]-1)*font*s.chordSpacingRatio,font,timeX,time=>{
          const event=voiceEvents.find(e=>e.kind!=='grace' && Math.abs(q(e.start)-time)<1e-8) ??
            voiceEvents.find(e=>e.kind!=='grace' && q(e.start)<=time && q(e.start)+q(e.duration)>time);
          const anchor=event ? positions.get(event.id) : undefined;
          const ink=digitBounds(localMode?'0':String(event?.pitches[0]?.degree ?? 0),timeX(time),y,font);
          return {cx:ink.centerX,bottom:anchor?.bottom ?? ink.bottom,event:event?.id};
        });
        for(const b of m.barlines) {
          if(b.repeat) tx(b.repeat.direction==='backward'?':||':'||:',x+width-16,y,t.repeatSize);
          if(b.ending) tx(`[${b.ending.number}]`,x+4,y-18,t.annotationSize);
          if(['light-heavy','light-light'].includes(b.style)) barline(x+width-3,y,b.style==='light-heavy'?1.6:.7);
        }
        if(score.issues.some(i => i.severity==='error' && i.measure===bar.number && [row.part.id,'all'].includes(i.part))) {
          doc.strokeColor('#b91c1c').lineWidth(.6).rect(x+1,y-5,width-2,font+13).stroke(); doc.strokeColor('black');
        }
      });
      x+=width;
    }
    if(!localMode) rows.forEach((_,ri) => {if(activeSet.has(ri)) barline(right,baselines[ri]);});
    if(localMode) for(const [id,p] of positions) eventLayout.push({event:id,...p,page:doc.bufferedPageRange().count,system:systems+1});
    const firstOrder=systemBars[0].order;
    const lastBar=systemBars.at(-1)!;
    const lastOrder=lastBar.order+lastBar.count-1;
    for(const grace of graceLayout.filter(g=>g.system===systems+1)) {
      const anchor=positions.get(grace.anchor as string);
      if(anchor) {grace.anchorX=anchor.anchorX;grace.anchorTop=anchor.top;grace.anchorBottom=anchor.bottom;}
    }
    const graceGroups=new Map<string,Event[]>();
    for(const row of rows) for(const event of row.part.measures.flatMap(m=>m.events).filter(e=>e.kind==='grace' && e.voice===row.voice && positions.has(e.id) && e.grace)) {
      const key=event.grace!.anchorId+':'+event.grace!.position;
      if(!graceGroups.has(key)) graceGroups.set(key,[]);graceGroups.get(key)!.push(event);
    }
    for(const group of graceGroups.values()) {
      const nearest=group[0].grace!.position==='after'?group[0]:group.at(-1)!;
      const small=positions.get(nearest.id)!,anchor=positions.get(nearest.grace!.anchorId);
      const main=score.parts.flatMap(p=>p.measures.flatMap(m=>m.events)).find(e=>e.id===nearest.grace!.anchorId);
      if(!anchor || !main) continue;
      const tiny=digitBounds(String(nearest.pitches[0].degree),small.x,small.y-n.graceOffsetY,font*n.graceScale);
      const principal=digitBounds(String(main.pitches[0].degree),anchor.x,anchor.y,font);
      const hook=graceHook({position:nearest.grace!.position,fontSize:font,grace:{centerX:tiny.centerX,bottom:small.bottom},principal,tail:anchor.tail},layout.graces);
      doc.save().lineWidth(layout.graces.lineWidth).moveTo(hook.sx,hook.sy).bezierCurveTo(hook.x1,hook.y1,hook.x2,hook.y2,hook.ex,hook.ey).stroke().restore();
      graceConnectors.push({...hook,events:group.map(e=>e.id),anchor:main.id,page:doc.bufferedPageRange().count,system:systems+1,row:small.row,graceBottom:small.bottom,principal});
    }
    for(const span of spans.filter(s => s.from<=lastOrder && s.to>=firstOrder)) {
      if(!activeSet.has(span.row)) continue;
      const fallback=digitBounds('1',0,localMode?(frames.find(f=>f.system===systems+1 && f.row===span.row)?.y ?? baselines[span.row]):baselines[span.row],font);
      curveRequests.push({span,positions,firstOrder,lastOrder,left,right,top:fallback.top,bottom:fallback.bottom,
        style:{...layout.curves,...(span.tuplet ? {slurHeight:layout.tuplets.curveHeight,clearance:layout.tuplets.clearance,lineWidth:layout.tuplets.lineWidth}:{}),
          edgeInset:Math.max(layout.curves.edgeInset,numberBoxWidth/2+layout.curves.clearance)},
        page:doc.bufferedPageRange().count,system:systems+1});
    }
    pageY+=height; systems++;
  }
  // Double-note tremolos retain their endpoints even at system/page breaks.
  for(const pair of tremoloPairs) {
    const a=techniquePositions.get(pair.start),b=techniquePositions.get(pair.end);
    if(!a || !b || a.row!==b.row) {warnings.push(`${pair.start}: double-note tremolo anchors unavailable`);continue;}
    const segments=new Map<string,typeof frames>();
    for(const f of frames.filter(f=>f.row===a.row && f.order>=a.order && f.order<=b.order)) {
      const key=`${f.page}:${f.system}`;if(!segments.has(key)) segments.set(key,[]);segments.get(key)!.push(f);
    }
    for(const group of segments.values()) {
      const f=group[0],last=group.at(-1)!;
      const continuesLeft=f.system!==a.system,continuesRight=f.system!==b.system;
      const left=continuesLeft ? f.left+layout.curves.edgeInset : a.anchorX+a.size*.4;
      const right=continuesRight ? last.right-layout.curves.edgeInset : b.anchorX-b.size*.4;
      const anchors=[...techniquePositions.values()].filter(p=>p.row===a.row && p.system===f.system && p.order>=a.order && p.order<=b.order);
      const top=Math.min(...anchors.map(p=>p.top))-tech.aboveGap-tech.tremoloRise-(pair.strokes-1)*tech.tremoloGap;
      if(right<=left) {warnings.push(`${pair.start}: insufficient double-note tremolo space`);continue;}
      upperAnnotations.push({event:pair.start,kind:'tremolo',row:a.row,system:f.system,page:f.page,left,right,top,
        bottom:top+tech.tremoloRise+(pair.strokes-1)*tech.tremoloGap,
        details:{mode:'vector-tremolo',type:'double',start:pair.start,end:pair.end,strokes:pair.strokes,continuesLeft,continuesRight},
        draw:shift=>{for(let i=0;i<pair.strokes;i++) line(left,top+shift+tech.tremoloRise+i*tech.tremoloGap,right,top+shift+i*tech.tremoloGap,tech.lineWidth);}});
    }
  }
  // Resolve every segment before painting: if one segment needs more clearance,
  // apply the same extra gap to the whole phrase, including across page breaks.
  const curveFor=(r:CurveRequest,extra=0)=>{
    const positions=r.span.tuplet ? new Map([...r.positions].map(([id,p])=>{
      const marks=upperAnnotations.filter(a=>a.event===id && a.page===r.page && a.system===r.system);
      return [id,{...p,top:Math.min(p.top,...marks.map(a=>a.top-tech.endpointLift))}];
    })) : r.positions;
    const curve=spanCurve(r.span,positions,r.span.row,r.firstOrder,r.lastOrder,r.left,r.right,r.top,r.bottom,r.style,extra);
    if(curve && r.span.tuplet?.lineShape==='straight') {
      const yy=r.span.placement==='below'?Math.max(curve.sy,curve.ey):Math.min(curve.sy,curve.ey);
      curve.sy=curve.ey=curve.y1=curve.y2=yy;
    }
    return curve;
  };
  const extraGaps=new Map<typeof spans[number],number>();
  for(const request of curveRequests) {
    const curve=curveFor(request);
    if(curve) extraGaps.set(request.span,Math.max(extraGaps.get(request.span) ?? 0,
      curve.endpointGap-request.style.clearance-request.span.lane*request.style.laneGap));
  }
  const routed=new Map<CurveRequest,NonNullable<ReturnType<typeof spanCurve>>>();
  for(const span of [...spans].sort((a,b)=>a.lane-b.lane || (a.endIndex-a.startIndex)-(b.endIndex-b.startIndex))) {
    const requests=curveRequests.filter(r=>r.span===span);
    let extra=extraGaps.get(span) ?? 0;
    for(let attempt=0;attempt<20;attempt++) {
      let deficit=0;
      for(const request of requests) {
        const curve=curveFor(request,extra);if(!curve) continue;
        for(const [previous,inner] of routed) if(previous.page===request.page && previous.system===request.system && previous.span.row===span.row)
          deficit=Math.max(deficit,curveAvoidanceOffset(curve,inner,request.style.laneGap));
      }
      if(deficit<.05) break;
      extra+=deficit+.1;
    }
    for(const request of requests) {const curve=curveFor(request,extra);if(curve) routed.set(request,curve);}
  }
  for(const request of curveRequests) {
    const curve=routed.get(request);
    if(!curve) continue;
    doc.switchToPage(request.page-1);
    const tuplet=request.span.tuplet;
    const label=tuplet && tuplet.showNumber!=='none' ? String(tuplet.actual)+(tuplet.showNumber==='both'?':'+tuplet.normal:'') : '';
    const glyph=tupletDigits(label),numberSize=layout.tuplets.numberSize;
    const ink=label?musicRun(glyph,numberSize):{left:0,right:0,top:0,bottom:0};
    const width=ink.right-ink.left,height=ink.bottom-ink.top,cx=(curve.sx+curve.ex)/2,cy=curveYAt(curve,cx);
    const numberBox={left:cx-width/2,right:cx+width/2,top:cy-height/2,bottom:cy+height/2};
    const paintCurve=(left=0,right=doc.page.width)=>{
      doc.save().rect(left,0,right-left,doc.page.height).clip().lineWidth(request.style.lineWidth).strokeColor('black');
      if(['dashed','dotted'].includes(curve.lineType)) doc.dash(curve.lineType==='dotted' ? .7 : request.style.dashLength,{space:request.style.dashSpace});
      doc.moveTo(curve.sx,curve.sy).bezierCurveTo(curve.x1,curve.y1,curve.x2,curve.y2,curve.ex,curve.ey).stroke().restore();
    };
    if(!tuplet || tuplet.bracket) {
      if(label) {paintCurve(0,numberBox.left-layout.tuplets.numberGap);paintCurve(numberBox.right+layout.tuplets.numberGap);}
      else paintCurve();
      if(tuplet?.lineShape==='straight') {
        const sign=curve.placement==='below'?-1:1;
        line(curve.sx,curve.sy,curve.sx,curve.sy+3*sign,request.style.lineWidth);
        line(curve.ex,curve.ey,curve.ex,curve.ey+3*sign,request.style.lineWidth);
      }
    }
    if(label) musicInk(glyph,numberBox.left,numberBox.top,numberSize);
    if(tuplet) tupletLayout.push({start:tuplet.start,end:tuplet.end,events:tuplet.events,actual:tuplet.actual,normal:tuplet.normal,
      duration:tuplet.duration,label,font:'music',fontSize:numberSize,lineShape:tuplet.lineShape,bracket:tuplet.bracket,source:tuplet.source,
      row:request.span.row,page:request.page,system:request.system,sx:curve.sx,ex:curve.ex,cx,cy,...numberBox,
      continuesLeft:curve.continuesLeft,continuesRight:curve.continuesRight});
    curveSegments.push({...curve,row:request.span.row,system:request.system,page:request.page,start:request.span.start,end:request.span.end});
  }
  for(const span of wedges) {
    const matching=frames.filter(f=>(localMode?(span.voice?rows[f.row].voice===span.voice:f.lane===0):f.row===span.row) && f.order>=span.start.order && f.order<=span.end.order);
    const segments=new Map<string,typeof frames>();
    for(const f of matching) {const key=`${f.page}:${f.system}`;if(!segments.has(key)) segments.set(key,[]);segments.get(key)!.push(f);}
    for(const group of segments.values()) {
      const first=group[0],last=group.at(-1)!;
      const startAbsolute=Math.max(span.start.absolute,first.absolute),endAbsolute=Math.min(span.end.absolute,last.absolute+last.length);
      if(endAbsolute<=startAbsolute) continue;
      const continuedLeft=span.start.absolute<first.absolute,continuedRight=span.end.absolute>last.absolute+last.length;
      const sx=continuedLeft?first.left+layout.wedges.edgeInset:first.xAt(startAbsolute-first.absolute);
      const ex=continuedRight?last.right-layout.wedges.edgeInset:last.xAt(endAbsolute-last.absolute);
      const sy=first.y+(span.placement==='above'?-layout.wedges.offsetY:first.font+layout.wedges.offsetY);
      const startOpening=wedgeOpening(span,startAbsolute,layout.wedges.height),endOpening=wedgeOpening(span,endAbsolute,layout.wedges.height);
      doc.switchToPage(first.page-1);
      line(sx,sy-startOpening/2,ex,sy-endOpening/2,layout.wedges.lineWidth);
      line(sx,sy+startOpening/2,ex,sy+endOpening/2,layout.wedges.lineWidth);
      wedgeSegments.push({id:span.id,type:span.type,row:span.row,page:first.page,system:first.system,start:span.start,end:span.end,
        startAbsolute,endAbsolute,sx,ex,sy,startOpening,endOpening,continuedLeft,continuedRight});
    }
  }
  for(const mark of upperAnnotations.sort((a,b)=>b.bottom-a.bottom)) {
    let shift=0;
    for(const [request,curve] of routed) {
      if(request.page!==mark.page || request.system!==mark.system || request.span.row!==mark.row || curve.placement==='below') continue;
      // Note ornaments stay near their note envelope. Only actual endpoints
      // receive a small lift; passing phrase arches no longer push them away.
      if(mark.noteTop!==undefined && mark.event!==request.span.start && mark.event!==request.span.end) continue;
      const left=Math.max(mark.left,curve.sx),right=Math.min(mark.right,curve.ex);
      if(right<left) continue;
      const top=Math.min(...Array.from({length:9},(_,i)=>curveYAt(curve,left+(right-left)*i/8)));
      const wanted=top+(mark.noteTop!==undefined ? tech.curveOverlap : -layout.curves.annotationGap)-mark.bottom;
      shift=Math.min(shift,mark.noteTop!==undefined ? Math.max(-tech.endpointLift,wanted) : wanted);
    }
    const obstacles=annotationLayout as unknown as typeof staticUpperText;
    for(let attempt=0;attempt<obstacles.length+1;attempt++) {
      const previous=shift;
      for(const other of obstacles) if(other.page===mark.page && other.system===mark.system && other.row===mark.row && other.left<mark.right && other.right>mark.left &&
        mark.top+shift<other.bottom+layout.curves.annotationStackGap && mark.bottom+shift>other.top-layout.curves.annotationStackGap)
        shift=Math.min(shift,other.top-layout.curves.annotationStackGap-mark.bottom);
      if(previous===shift) break;
    }
    doc.switchToPage(mark.page-1);mark.draw(shift);
    annotationLayout.push({event:mark.event,kind:mark.kind,row:mark.row,page:mark.page,system:mark.system,left:mark.left,right:mark.right,
      top:mark.top+shift,bottom:mark.bottom+shift,shift,...mark.details});
    if(mark.details) techniqueLayout.push({event:mark.event,kind:mark.kind,row:mark.row,page:mark.page,system:mark.system,left:mark.left,right:mark.right,
      top:mark.top+shift,bottom:mark.bottom+shift,action:'draw',...mark.details});
  }
  // Text is the outer layer: move it above note ornaments and tuplet labels,
  // preserving paired tempo words/metronome alignment as one group.
  const placedText:(Box & {row:number;system:number;page:number})[]=[];
  for(const group of deferredDirections.sort((a,b)=>b.box.bottom-a.box.bottom)) {
    let shift=0;const box=group.box;
    const obstacles=[...annotationLayout,...tupletLayout] as unknown as (Box & {row:number;system:number;page:number})[];
    for(const other of obstacles) if(other.row===group.row && other.system===group.system && other.page===group.page &&
      other.left<box.right && other.right>box.left) shift=Math.min(shift,other.top-tech.textGap-box.bottom);
    for(const [request,curve] of routed) {
      if(request.page!==group.page || request.system!==group.system || request.span.row!==group.row || curve.placement==='below') continue;
      const left=Math.max(box.left,curve.sx),right=Math.min(box.right,curve.ex);
      if(right>=left) shift=Math.min(shift,Math.min(...Array.from({length:9},(_,i)=>curveYAt(curve,left+(right-left)*i/8)))-tech.textGap-box.bottom);
    }
    for(let attempt=0;attempt<=placedText.length;attempt++) {
      const before=shift;
      for(const other of placedText) if(other.row===group.row && other.system===group.system && other.page===group.page &&
        other.left<box.right && other.right>box.left && box.top+shift<other.bottom+2 && box.bottom+shift>other.top-2)
        shift=Math.min(shift,other.top-2-box.bottom);
      if(before===shift) break;
    }
    doc.switchToPage(group.page-1);group.draw(shift);
    for(const b of new Set(group.boxes)) {b.top+=shift;b.bottom+=shift;}
    placedText.push({...box,top:box.top+shift,bottom:box.bottom+shift,row:group.row,system:group.system,page:group.page});
  }
  const range=doc.bufferedPageRange();
  for(let p=range.start;p<range.start+range.count;p++) {
    doc.switchToPage(p);
    tx(String(p+1),margin,doc.page.height-margin-h.footerOffsetY,t.pageNumberSize,{width:doc.page.width-margin*2,align:'center'});
  }
  doc.end(); await completion;
  const result={pages:range.count,systems,rows:rows.length,bars:score.bars.length,
    noteEvents:score.parts.reduce((n,p)=>n+p.measures.reduce((n,m)=>n+m.events.filter(e=>e.kind!=='rest').length,0),0),
    singleVoice,localDualVoice:localMode,voiceLayout,voiceLabelLayout,eventLayout,layoutResolved:layout,techniquePolicy:policy,techniqueLayout,tupletLayout,noteSymbols,fonts:score.fonts,systemLayout,measureLayout,contextAnnotations,meterLayout,directionLayout,graceLayout,graceConnectors,restLayout,curveSegments,annotationLayout,underlineLayout,wedgeSegments,connectedUnderlineGroups,warnings:[...new Set(warnings)],output:path.resolve(output)};
  fs.writeFileSync(output.replace(/\.pdf$/i,'.render.json'),JSON.stringify(result,null,2),'utf8');
  console.log(JSON.stringify(result));
}

const [input,output]=process.argv.slice(2);
if(!input || !output) { console.error('Usage: node dist/render.js score.json output.pdf'); process.exitCode=2; }
else { render(JSON.parse(fs.readFileSync(input,'utf8')) as Score,output).catch(error=>{console.error(error);process.exitCode=1;}); }
