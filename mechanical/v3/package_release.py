"""从Git提交打包，并逐文件对照Git blob核验；不包含未提交内容。"""
from pathlib import Path
import hashlib,json,subprocess,zipfile

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]


def git(*args):return subprocess.check_output(['git',*args],cwd=REPO)


def main():
    output=ROOT.parents[3]/'outputs';output.mkdir(exist_ok=True)
    bundle=output/'mini-gantry-v3-R1.zip';prefix='mini-gantry/'
    selected=['.gitattributes','.gitignore','pyproject.toml','mechanical/v3']
    commit=git('rev-parse','HEAD').decode().strip()
    subprocess.run(['git','archive','--format=zip','--prefix='+prefix,'--output',str(bundle),'HEAD',*selected],cwd=REPO,check=True)
    entries={}
    for item in git('ls-tree','-rz','--full-tree','HEAD','--',*selected).split(b'\0'):
        if not item:continue
        meta,path=item.split(b'\t',1);mode,kind,oid=meta.decode().split();assert kind=='blob';entries[path.decode('utf-8')]=oid
    delivered=output/'mini-gantry-v3';delivered.mkdir(exist_ok=True)
    with zipfile.ZipFile(bundle) as z:
        assert z.testzip() is None
        names={n[len(prefix):] for n in z.namelist() if not n.endswith('/')};assert names==set(entries)
        proc=subprocess.Popen(['git','cat-file','--batch'],cwd=REPO,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
        for name,oid in entries.items():
            proc.stdin.write((oid+'\n').encode());proc.stdin.flush();header=proc.stdout.readline().decode().split();assert header[1]=='blob'
            content=proc.stdout.read(int(header[2]));assert proc.stdout.read(1)==b'\n'
            assert content==z.read(prefix+name),name
        proc.stdin.close();assert proc.wait(timeout=15)==0
        audit=json.loads(z.read(prefix+'mechanical/v3/validation/release_audit.json'))
        for row in audit['files']:
            content=z.read(prefix+'mechanical/v3/'+row['file'])
            assert hashlib.sha256(content).hexdigest()==row['sha256'],row['file']
        copies={'drawings/manufacturing.pdf':'V3-R1_加工图.pdf','drawings/assembly_and_procurement.pdf':'V3-R1_装配与采购.pdf',
                'drawings/assembly.png':'assembly.png','cad/mini_gantry_v3.step':'mini_gantry_v3.step','cad/camera_adapter_blank.stl':'camera_adapter_blank.stl'}
        for src,dst in copies.items():(delivered/dst).write_bytes(z.read(prefix+'mechanical/v3/'+src))
        for name in names:
            if not name.startswith('mechanical/v3/SolidWorksV3/'):continue
            dest=delivered/'SolidWorksV3'/Path(name).name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(z.read(prefix+name))
    report=dict(status='PASS_GIT_ARCHIVE_CRC_AND_BLOB_IDENTITY',commit=commit,zip=bundle.name,files=len(entries),
                bytes=bundle.stat().st_size,sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),
                delivered_files=[str(p.relative_to(output)) for p in delivered.rglob('*') if p.is_file()])
    (output/'mini-gantry-v3-package-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='delivered_files'},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
