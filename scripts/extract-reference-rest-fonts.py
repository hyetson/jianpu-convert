"""Recover the count font subsets embedded in the user's reference PDF."""
from pathlib import Path
import hashlib
import json
import pdfplumber
from pdfminer.pdftypes import resolve1

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'example/丝绸之路_竹笛分谱.pdf'
folder=ROOT/'tools/fonts/reference-maestro'
folder.mkdir(parents=True,exist_ok=True)
resources={'FXF31':'counts-primary.ttf','FXF7':'counts-five.ttf','FXF85':'counts-eight.ttf'}
files=[]
with pdfplumber.open(source) as pdf:
    for page in pdf.pages:
        for name,ref in resolve1(page.page_obj.resources['Font']).items():
            if name not in resources:continue
            font=resolve1(ref)
            if 'CIDFont+F1' not in str(font.get('BaseFont')):raise ValueError(f'Unexpected font resource {name}')
            descendant=resolve1(resolve1(font['DescendantFonts'])[0])
            descriptor=resolve1(descendant['FontDescriptor'])
            data=resolve1(descriptor['FontFile2']).get_data()
            filename=resources.pop(name)
            (folder/filename).write_bytes(data)
            files.append({'resource':name,'file':filename,'sha256':hashlib.sha256(data).hexdigest()})
if resources:raise ValueError(f'Missing reference resources: {list(resources)}')
(folder/'SOURCE.json').write_text(json.dumps({'source':str(source.relative_to(ROOT)),
    'sourceSHA256':hashlib.sha256(source.read_bytes()).hexdigest(),'family':'Maestro',
    'copyright':'Copyright (c) 1999 Coda Music Technology','files':files},ensure_ascii=False,indent=2),encoding='utf-8')
print(folder)
