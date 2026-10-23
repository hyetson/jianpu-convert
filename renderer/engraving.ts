/** SMuFL ranges: dynamics E520-E53D, time signatures E080, metronome ECA0. */
export function dynamicGlyph(text:string):string|null {
  const values:Record<string,number>={p:0xe520,m:0xe521,f:0xe522,r:0xe523,s:0xe524,z:0xe525,n:0xe526,
    pppppp:0xe527,ppppp:0xe528,pppp:0xe529,ppp:0xe52a,pp:0xe52b,mp:0xe52c,mf:0xe52d,pf:0xe52e,
    ff:0xe52f,fff:0xe530,ffff:0xe531,fffff:0xe532,ffffff:0xe533,fp:0xe534,fz:0xe535,sf:0xe536,
    sfp:0xe537,sfpp:0xe538,sfz:0xe539,sfzp:0xe53a,sffz:0xe53b,rf:0xe53c,rfz:0xe53d};
  if(values[text]!=null) return String.fromCodePoint(values[text]);
  return null;
}
export const meterDigits=(text:string)=>[...text].map(c=>c==='+'?'\uE08C':/\d/.test(c)?String.fromCodePoint(0xe080+Number(c)):c).join('');
export const metronomeGlyph=(unit:string)=>{
  const codes:Record<string,number>={breve:0xeca0,whole:0xeca2,half:0xeca3,quarter:0xeca5,eighth:0xeca7,'16th':0xeca9,'32nd':0xecab,'64th':0xecad,'128th':0xecaf};
  return codes[unit]!=null?String.fromCodePoint(codes[unit]):null;
};
export const isTempoTerm=(text:string)=>/^(rubato|moderato|allegro|allegretto|all[e]?rgo|andante|andantino|adagio|largo|lento|presto|prestissimo|vivace|pi[uù]\s+mosso|meno\s+mosso|a\s+tempo|tempo\b)/i.test(text.trim());
