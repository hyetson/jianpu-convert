"""Narrow, source-backed repair for OMR multi-rest counts in vector PDFs.

Only use digits centered above a MULTIPLE_REST detected by Audiveris. Require
one unambiguous word per symbol, and a one-to-one mapping to exported rests.
Raw OMR files are retained; the corrected XML and evidence are separate files.
This never supplies pitches, rhythms, cue notes, or guesses for scanned PDFs.
"""
from copy import deepcopy
from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET
import zipfile

from .model import Issue
from .musicxml import read_xml


def repair_rest_counts(pdf: Path, xml: Path, omr_folder: Path, part_id: str,
                       issues: list[Issue]) -> Path:
    import pdfplumber
    projects = list(omr_folder.glob('*.omr'))
    if len(projects) != 1:
        issues.append(Issue('warning','rest_evidence_unavailable',part_id,'','No unique OMR project for PDF evidence'))
        return xml
    root = read_xml(xml)
    parts = root.findall('part')
    if len(parts) != 1:
        return xml
    measures = parts[0].findall('measure')
    exported = [(i,m,int(m.findtext('attributes/measure-style/multiple-rest','0')))
                for i,m in enumerate(measures) if m.find('attributes/measure-style/multiple-rest') is not None]
    evidence = []
    with zipfile.ZipFile(projects[0]) as archive, pdfplumber.open(pdf) as document:
        sheets = sorted((n for n in archive.namelist() if re.fullmatch(r'sheet#\d+/sheet#\d+\.xml',n)),
                        key=lambda s:int(s.split('/')[0].split('#')[1]))
        for member in sheets:
            page_no = int(member.split('/')[0].split('#')[1])
            if page_no > len(document.pages):
                raise ValueError('OMR sheet index exceeds PDF pages')
            page = document.pages[page_no-1]
            sheet = ET.fromstring(archive.read(member))
            picture = sheet.find('picture')
            if picture is None:
                continue
            sx = int(picture.get('width','0'))/page.width
            sy = int(picture.get('height','0'))/page.height
            if min(sx,sy) <= 0:
                continue
            # A tempo "92" and a nearby rest count "11" can otherwise be
            # concatenated into "9211". Font/size boundaries keep them apart.
            words = [w for w in page.extract_words(extra_attrs=['fontname','size']) if w['text'].isdigit()]
            for system in sheet.findall('.//system'):
                rests = sorted(system.findall('.//inters/multiple-rest'),key=lambda r:int(r.find('bounds').get('x')))
                for rest in rests:
                    bounds = rest.find('bounds')
                    cx = (int(bounds.get('x'))+int(bounds.get('w'))/2)/sx
                    y = int(bounds.get('y'))/sy
                    candidates = [w for w in words
                                  if abs((w['x0']+w['x1'])/2-cx)<8 and -28<w['top']-y<0
                                  and 1<=int(w['text'])<=1000]
                    if len(candidates) != 1:
                        issues.append(Issue('error','rest_count_unverified',part_id,'',
                                            f'PDF page {page_no}: cannot verify rest count near ({cx:.1f},{y:.1f})'))
                        evidence.append({'page':page_no,'symbol':rest.get('id'),'count':None})
                    else:
                        w=candidates[0]
                        evidence.append({'page':page_no,'symbol':rest.get('id'),'count':int(w['text']),
                                         'word':w['text'],'box':[w['x0'],w['top'],w['x1'],w['bottom']]})
    evidence_path=omr_folder/'rest-count-evidence.json'
    evidence_path.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    if len(evidence)!=len(exported) or any(e['count'] is None for e in evidence):
        issues.append(Issue('error','rest_mapping',part_id,'',
                            f'OMR rest symbols ({len(evidence)}) do not map unambiguously to XML rests ({len(exported)}); no correction applied'))
        return xml
    rebuilt=[];corrections=[];offset=0;i=0;ei=0
    while i<len(measures):
        original=measures[i]
        if not original.get('number','').isdigit():
            issues.append(Issue('error','rest_numbering',part_id,'','Non-numeric bar numbering; correction refused'))
            return xml
        cursor=int(original.get('number'))+offset
        old_count=int(original.findtext('attributes/measure-style/multiple-rest','0'))
        if not old_count:
            m=deepcopy(original);m.set('number',str(cursor));rebuilt.append(m);i+=1;continue
        count=evidence[ei]['count'];ei+=1
        # Audiveris 5.11 exports a separate full-bar rest for every counted bar.
        group=measures[i:i+old_count]
        if len(group)!=old_count or any(not m.findall('note') or any(n.find('rest') is None for n in m.findall('note')) for m in group):
            issues.append(Issue('error','rest_export_structure',part_id,original.get('number',''),
                                'Exporter does not provide the expected explicit rest group; correction refused'))
            return xml
        for k in range(count):
            m=deepcopy(original if k==0 else group[min(k,len(group)-1)])
            m.set('number',str(cursor+k))
            if k==0:
                m.find('attributes/measure-style/multiple-rest').text=str(count)
            else:
                for node in list(m):
                    if node.tag!='note':m.remove(node)
            if k==count-1 and count>1:
                for b in group[-1].findall('barline'):m.append(deepcopy(b))
            rebuilt.append(m)
        if count!=old_count:
            corrections.append({'oldBar':original.get('number'),'newBar':cursor,'oldCount':old_count,
                                'newCount':count,'evidence':evidence[ei-1]})
        offset+=count-old_count;i+=old_count
    for m in measures:parts[0].remove(m)
    parts[0].extend(rebuilt)
    output=omr_folder/'corrected.musicxml'
    ET.ElementTree(root).write(output,encoding='utf-8',xml_declaration=True)
    (omr_folder/'rest-count-corrections.json').write_text(json.dumps(corrections,ensure_ascii=False,indent=2),encoding='utf-8')
    if corrections:
        issues.append(Issue('warning','rest_counts_corrected',part_id,'',
                            f'{len(corrections)} OMR rest counts corrected from localized source PDF digits; evidence retained'))
    return output
