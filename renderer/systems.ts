export interface Context {fifths: number; mode: string; beats: string; beatType: number}
export function contextChanges(previous: Context | undefined, current: Context) {
  return {key:!previous || previous.fifths!==current.fifths || previous.mode!==current.mode,
    meter:!previous || previous.beats!==current.beats || previous.beatType!==current.beatType};
}

/** Pack the requested number of complete measures, respecting readable widths. */
export function planSystems(bars: {width: number; minimumWidth: number;meterWeight?:number}[], available: number, maximum=4,meterAware=false,
  availableFor?:(indices:number[])=>number): number[][] {
  if (!(available>0) || !(maximum>=1)) throw new Error('Invalid system width or measure limit');
  const result: number[][]=[];
  for(let start=0;start<bars.length;) {
    const indices:number[]=[];let minimum=0,units=0;
    while(start<bars.length) {
      const cost=meterAware && maximum>1 ? bars[start].meterWeight ?? 1 : 1;
      if(indices.length && units+cost>maximum+1e-8) break;
      const width=bars[start].minimumWidth;
      const currentAvailable=availableFor?.([...indices,start]) ?? available;
      if(!(currentAvailable>0)) throw new Error('System labels leave no musical width');
      if(indices.length && minimum+width>currentAvailable) break;
      indices.push(start++);minimum+=width;units+=cost;
      // A single oversized measure still advances; the renderer reports it.
      if(minimum>currentAvailable) break;
    }
    result.push(indices);
  }
  return result;
}
