"""Build a source/runtime bundle without environments, caches or source scores."""
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]
VERSION='0.1.0'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--overwrite',action='store_true')
    args=parser.parse_args()
    output=ROOT/'output/releases'/f'jianpu-single-voice-{VERSION}.zip'
    if output.exists() and not args.overwrite:raise FileExistsError(f'{output}; use --overwrite')
    paths=[]
    for name in ('README.md','THIRD_PARTY_NOTICES.md','.python-version','.node-version','convert-single.ps1','convert-dual.ps1','requirements.txt','requirements-lock.txt','package.json','package-lock.json','tsconfig.json'):
        paths.append(ROOT/name)
    for folder,glob in (('jianpu','*.py'),('renderer','*.ts'),('dist','*.js'),('tests','*.py'),('tests','*.mjs'),('docs','*.md'),
                        ('configs','*.json'),('scripts','*.py'),('scripts','*.ps1')):
        paths.extend(p for p in (ROOT/folder).glob(glob) if not p.name.endswith('.local.json'))
    for name in ('Bravura.otf','Bravura-LICENSE.txt'):
        paths.append(ROOT/'tools/fonts'/name)
    # Reference-score font subsets are local-only and have no redistribution grant.
    paths=sorted(set(p for p in paths if p.is_file()))
    files=[]
    for p in paths:
        relative=p.relative_to(ROOT).as_posix()
        assert not relative.startswith(('tmp/','output/','node_modules/','.venv/','example/'))
        files.append({'path':relative,'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    manifest={'name':'jianpu-single-voice','version':VERSION,'builtAt':datetime.now().isoformat(timespec='seconds'),
              'scope':'Windows source bundle and compiled renderer; dependencies and input/review score files are not bundled',
              'entryPoint':'convert-single.ps1','pythonEntryPoint':'python -m jianpu single','files':files}
    output.parent.mkdir(parents=True,exist_ok=True)
    staging=output.with_suffix('.zip.tmp')
    with zipfile.ZipFile(staging,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for item in files:archive.write(ROOT/item['path'],item['path'])
        archive.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(staging) as archive:
        assert archive.testzip() is None
        for item in files:assert hashlib.sha256(archive.read(item['path'])).hexdigest()==item['sha256']
    staging.replace(output)
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(f'{digest}  {output.name}\n',encoding='utf-8')
    print(json.dumps({'zip':str(output),'files':len(files),'bytes':output.stat().st_size,'sha256':digest}))


if __name__=='__main__':main()
