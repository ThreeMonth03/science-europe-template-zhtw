"""Replay exact 0.3.15 artifacts for budget fixtures, never modify old outputs."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from artifact_utils import sha


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--source',type=Path,required=True)
    a=p.parse_args(); m=json.loads((a.source/'manifest.json').read_text())
    assert m['status']=='candidate' and m['source']['version']=='0.3.15'
    assert m['source']['commit']=='b1391c059c23c97095b8c748d527d13516c8a74f'
    assert all(not v['dirty'] for v in m['checkouts'].values())
    for name in ['english.zip','chinese.zip']: assert sha(a.source/name)==m['sha256'][name]
    out=Path(tempfile.mkdtemp(prefix='baseline-budget-',dir=Path(__file__).resolve().parents[1]/'outputs'))
    for name in ['english.zip','chinese.zip']: shutil.copy2(a.source/name,out/name)
    for name in ['en','translated']: shutil.copytree(a.source/name,out/name)
    m['artifact_replay']={'source_build':str(a.source.resolve()),'source_manifest_sha256':sha(a.source/'manifest.json'),
        'preparer_sha256':sha(Path(__file__)), 'note':'Exact old packages; checkouts record their original build, not a fresh build.'}
    (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n'); print(out)


if __name__=='__main__': main()
