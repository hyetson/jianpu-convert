import type {Style} from './layout.js';
export interface GraceHookInput {
  position:string;fontSize:number;grace:{centerX:number;bottom:number};
  principal:{left:number;right:number;top:number;bottom:number};tail?:{right:number;y:number};
}
/** A small under-grace hook, independent of phrase/tie arches and their lanes. */
export function graceHook(input:GraceHookInput,style:Style['graces']) {
  const {grace,principal,position,fontSize,tail}=input;
  const under=grace.bottom+style.underlineGap;
  const nearY=principal.top+(principal.bottom-principal.top)*style.anchorHeightRatio;
  if(position==='after') {
    const ex=grace.centerX,ey=under;
    const sx=Math.max((tail?.right ?? principal.right)+style.anchorGap,ex-fontSize*style.maximumWidthRatio);
    const sy=tail?.y ?? nearY;
    return {sx,sy,x1:ex+style.bendInset,y1:sy,x2:ex,y2:ey+(sy-ey)*.65,ex,ey,position,kind:'grace-hook'};
  }
  const sx=grace.centerX,sy=under,ex=principal.left-style.anchorGap;
  const ey=Math.max(nearY,Math.min(principal.bottom-style.anchorGap,sy+style.minimumDrop));
  return {sx,sy,x1:sx,y1:sy+(ey-sy)*.65,x2:sx-style.bendInset,y2:ey,ex,ey,position,kind:'grace-hook'};
}
