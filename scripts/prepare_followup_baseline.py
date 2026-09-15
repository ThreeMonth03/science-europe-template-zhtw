"""Replay immutable 0.3.14 packages against new fixtures, without editing old evidence."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from artifact_utils import sha


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--source',type=Path,required=True)
    a=p.parse_args(); m=json.loads((a.source/'manifest.json').read_text())
    assert m['status']=='candidate' and m['source']['version']=='0.3.14'
    assert m['source']['commit']=='98b153364844930de772cbdcb1e13eb14e3555b7'
    assert all(not v['dirty'] for v in m['checkouts'].values())
    for name in ['english.zip','chinese.zip']: assert sha(a.source/name)==m['sha256'][name]
    out=Path(tempfile.mkdtemp(prefix='baseline-followups-',dir=Path(__file__).resolve().parents[1]/'outputs'))
    for name in ['english.zip','chinese.zip']: shutil.copy2(a.source/name,out/name)
    for name in ['en','translated']: shutil.copytree(a.source/name,out/name)
    m['artifact_replay']={'source_build':str(a.source.resolve()),'source_manifest_sha256':sha(a.source/'manifest.json'),
                          'preparer_sha256':sha(Path(__file__)),
                          'note':'Exact existing candidate packages; checkouts describe their original build, not a new source build.'}
    (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    print(out)


if __name__=='__main__': main()
