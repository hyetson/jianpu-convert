"""Check every generated page and render it for visual QA, without changing PDF."""
import argparse
import json
from pathlib import Path
import pdfplumber
import pypdfium2 as pdfium
from pdfminer.pdftypes import resolve1

parser=argparse.ArgumentParser()
parser.add_argument('pdf',type=Path)
parser.add_argument('--preview-dir',type=Path,required=True)
args=parser.parse_args()
args.preview_dir.mkdir(parents=True,exist_ok=True)
stats=[]
with pdfplumber.open(args.pdf) as pdf:
    for i,page in enumerate(pdf.pages):
        embedded=[]
        for font in resolve1(page.page_obj.resources.get('Font',{})).values():
            font=resolve1(font)
            descendants=resolve1(font.get('DescendantFonts',[]))
            for obj in descendants or [font]:
                descriptor=resolve1(resolve1(obj).get('FontDescriptor',{}))
                embedded.append(any(key in descriptor for key in ('FontFile','FontFile2','FontFile3')))
        if not page.chars:raise SystemExit(f'Page {i+1} has no text')
        if page.images:raise SystemExit(f'Page {i+1} includes raster images; expected vector rendering')
        if embedded and not all(embedded):raise SystemExit(f'Page {i+1} includes a nonembedded font')
        stats.append({'page':i+1,'characters':len(page.chars),'rasterImages':len(page.images),'embeddedFonts':len(embedded)})
doc=pdfium.PdfDocument(str(args.pdf))
for i in range(len(doc)):
    page=doc[i];bitmap=page.render(scale=1.5)
    bitmap.to_pil().save(args.preview_dir/f'page-{i+1:03}.png')
    bitmap.close();page.close()
doc.close()
(args.preview_dir/'verification.json').write_text(json.dumps({'pdf':str(args.pdf.resolve()),'pages':stats},indent=2),encoding='utf-8')
print(json.dumps({'pages':len(stats),'vector':True,'preview':str(args.preview_dir.resolve())}))
