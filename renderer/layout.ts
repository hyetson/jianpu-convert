/** Public layout options. Distances and font sizes are pt; *Ratio is unitless. */
export const STYLE_DEFAULTS = {
  typography: {titleSize:21,continuedTitleSize:13,subtitleSize:10,composerSize:10,statusSize:8,
    partLabelSize:10,annotationSize:8,pageNumberSize:9,tupletSize:7,microtoneSize:6,restCountSize:11,repeatSize:9},
  notation: {accidentalGap:.5,accidentalScale:.8,accidentalTopOffsetRatio:.12,
    upperDotGap:3,lowerDotGap:4,dotRadius:1,dotStackGap:3.5,
    underlineGap:3,underlineLayerGap:2.5,underlineWidth:.8,underlineLengthRatio:.7,underlineLeftExtension:1,
    dashLengthRatio:.5,dashWidth:.9,graceScale:.67,graceOffsetY:12,graceOffsetXRatio:.5},
  spacing: {columnWidthRatio:.95,minimumColumnWidthRatio:.8,beatGapRatio:.6,minimumBeatGapRatio:.28,
    leftPaddingRatio:.9,rightPaddingRatio:.75,durationSpacingRatio:1.35,augmentationSpaceRatio:.3,
    accidentalSpaceRatio:.3,doubleAccidentalSpaceRatio:.5,microtoneSpaceRatio:1.3,minimumCompressionRatio:.82,
    rowHeight:54,systemGap:31,baselineOffset:30,chordSpacingRatio:1.55,measureWidthRatio:9,meterWidthBias:1},
  context: {initialFontSize:14,changeFontSize:8,initialOffsetX:0,initialOffsetY:68,changeOffsetX:12,changeOffsetY:25},
  measureNumbers: {fontSize:9,minimumWidth:16,height:16,paddingX:4,paddingY:2,digitGap:.6,offsetY:35,lineWidth:.7},
  barlines: {halfHeightRatio:.8,lineWidth:.7},
  rests: {minimumMeasuresToCompress:4,widthRatio:6,minimumWidthRatio:5,symbolInset:6,
    lineWidth:2.2,capHeight:10,capWidth:1.3,countGap:4,countDigitGap:1.3,zeroInset:8},
  header: {subtitleOffsetY:29,composerOffsetY:47,statusOffsetY:65,continuedStatusOffsetY:20,
    firstSystemOffsetY:106,continuedSystemOffsetY:64,footerOffsetY:23},
  curves: {slurHeight:12,tieHeight:6,graceHeight:6,maximumHeight:44,clearance:3.5,laneGap:5,lineWidth:.7,edgeInset:12,
    dashLength:3,dashSpace:2,collisionStep:2,annotationGap:3,annotationStackGap:2},
  wedges: {height:8,offsetY:36,lineWidth:.7,edgeInset:3},
  meter: {heightRatio:1.18,stackGap:1.5,lineWidth:.6,leftInset:5,rightGap:9,initialGap:12},
  terms: {dynamicsSize:18,dynamicsGap:4,tempoSize:10,expressionSize:9,metronomeSize:12,metronomeTextSize:10,laneGap:14,offsetY:34},
  graces: {underlineGap:.7,anchorGap:1.2,anchorHeightRatio:.25,lineWidth:.55,bendInset:.5,minimumDrop:2.8,maximumWidthRatio:.65},
  techniques: {symbolSizeRatio:1,textSize:8,aboveGap:4,lineWidth:.7,tremoloWidth:9,tremoloGap:3,tremoloRise:4,
    arpeggioGap:4,arpeggioWidth:4,arpeggioWaveHeight:5,arpeggioArrowSize:3,ornamentGap:2,endpointLift:3,curveOverlap:1.5,textGap:3},
  tuplets: {numberSize:16,curveHeight:5,clearance:3,numberGap:2,lineWidth:.65},
  localVoices: {rowGap:72,labelSize:10,labelGap:10},
};
export type Style = typeof STYLE_DEFAULTS;
export interface LayoutOptions {
  fontSize?: number; margin?: number; pageSize?: 'A4'|'A3'; compressRests?: boolean; maxMeasuresPerSystem?: number;
  typography?: Partial<Style['typography']>; notation?: Partial<Style['notation']>;
  spacing?: Partial<Style['spacing']>; context?: Partial<Style['context']>;
  measureNumbers?: Partial<Style['measureNumbers']>; barlines?: Partial<Style['barlines']>; header?: Partial<Style['header']>;
  rests?: Partial<Style['rests']>;
  curves?: Partial<Style['curves']>;
  wedges?: Partial<Style['wedges']>;justifyLastSystem?:boolean;
  meter?:Partial<Style['meter']>;terms?:Partial<Style['terms']>;
  graces?:Partial<Style['graces']>;
  techniques?:Partial<Style['techniques']>;
  tuplets?:Partial<Style['tuplets']>;
  localVoices?:Partial<Style['localVoices']>;
  meterAwarePacking?:boolean;
}
export interface ResolvedLayout extends Style {
  fontSize: number; margin: number; pageSize: 'A4'|'A3'; compressRests: boolean; maxMeasuresPerSystem: number;
  justifyLastSystem:boolean;
  meterAwarePacking:boolean;
}

function positive(name: string,value: unknown,allowZero=false): asserts value is number {
  if(typeof value!=='number' || !Number.isFinite(value) || (allowZero ? value<0 : value<=0))
    throw new Error(`layout.${name} must be a finite ${allowZero ? 'nonnegative' : 'positive'} number`);
}

export function resolveLayout(options: LayoutOptions = {}): ResolvedLayout {
  if(!options || typeof options!=='object' || Array.isArray(options)) throw new Error('layout must be an object');
  const allowed=new Set(['fontSize','margin','pageSize','compressRests','maxMeasuresPerSystem','justifyLastSystem','meterAwarePacking',...Object.keys(STYLE_DEFAULTS)]);
  for(const key of Object.keys(options)) if(!allowed.has(key)) throw new Error(`Unknown layout option: ${key}`);
  const fontSize=options.fontSize ?? 13, margin=options.margin ?? 35;
  positive('fontSize',fontSize);positive('margin',margin);
  if(fontSize<8 || fontSize>36 || margin<15 || margin>100) throw new Error('layout.fontSize must be 8-36 pt; margin must be 15-100 pt');
  if(options.pageSize!==undefined && !['A4','A3'].includes(options.pageSize)) throw new Error('layout.pageSize must be A4 or A3');
  if(options.compressRests!==undefined && typeof options.compressRests!=='boolean') throw new Error('layout.compressRests must be boolean');
  if(options.justifyLastSystem!==undefined && typeof options.justifyLastSystem!=='boolean') throw new Error('layout.justifyLastSystem must be boolean');
  if(options.meterAwarePacking!==undefined && typeof options.meterAwarePacking!=='boolean') throw new Error('layout.meterAwarePacking must be boolean');
  if(options.maxMeasuresPerSystem!==undefined && (!Number.isInteger(options.maxMeasuresPerSystem) || options.maxMeasuresPerSystem<1))
    throw new Error('layout.maxMeasuresPerSystem must be a positive integer');
  const style=structuredClone(STYLE_DEFAULTS);
  // Keep the previous initial-context rule when the note font is larger.
  style.context.initialFontSize=Math.max(14,fontSize);
  for(const section of Object.keys(style) as (keyof Style)[]) {
    const overrides=options[section];
    if(overrides!==undefined && (!overrides || typeof overrides!=='object' || Array.isArray(overrides)))
      throw new Error(`layout.${section} must be an object`);
    const target=style[section] as Record<string,number>;
    for(const [key,value] of Object.entries(overrides ?? {})) {
      if(!Object.hasOwn(target,key)) throw new Error(`Unknown layout option: ${section}.${key}`);
      // Position offsets may be negative; widths, sizes and ratios cannot.
      if(key.includes('Offset') || key==='offsetY') {
        if(typeof value!=='number' || !Number.isFinite(value)) throw new Error(`layout.${section}.${key} must be finite`);
      } else positive(`${section}.${key}`,value,key.includes('Gap') || key==='paddingX' || key==='paddingY' || key==='underlineLeftExtension' || key==='meterWidthBias');
      target[key]=value;
    }
  }
  if(style.spacing.minimumCompressionRatio>1) throw new Error('layout.spacing.minimumCompressionRatio must be <= 1');
  if(style.spacing.minimumColumnWidthRatio>style.spacing.columnWidthRatio || style.spacing.minimumBeatGapRatio>style.spacing.beatGapRatio)
    throw new Error('Minimum spacing cannot exceed preferred spacing');
  if(style.measureNumbers.height<2*style.measureNumbers.paddingY) throw new Error('Measure-number box height must accommodate vertical padding');
  if(options.curves?.graceHeight===undefined) style.curves.graceHeight=Math.min(style.curves.graceHeight,style.curves.maximumHeight);
  if(style.curves.maximumHeight<Math.max(style.curves.slurHeight,style.curves.tieHeight,style.curves.graceHeight)) throw new Error('Maximum curve height cannot be below the initial curve height');
  if(style.meter.heightRatio*2*fontSize*style.barlines.halfHeightRatio<=2*style.meter.stackGap+style.meter.lineWidth)
    throw new Error('Meter height must accommodate its two digits and fraction gaps');
  if(!Number.isInteger(style.rests.minimumMeasuresToCompress) || style.rests.minimumMeasuresToCompress<2)
    throw new Error('layout.rests.minimumMeasuresToCompress must be an integer >= 2');
  if(style.rests.minimumWidthRatio>style.rests.widthRatio) throw new Error('Minimum rest width cannot exceed preferred rest width');
  return {...style,fontSize,margin,pageSize:options.pageSize ?? 'A4',compressRests:options.compressRests ?? true,
    maxMeasuresPerSystem:options.maxMeasuresPerSystem ?? 4,justifyLastSystem:options.justifyLastSystem ?? false,meterAwarePacking:options.meterAwarePacking ?? true};
}
