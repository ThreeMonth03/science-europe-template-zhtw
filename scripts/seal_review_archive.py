"""Create an immutable checksum inventory for one completed local review archive."""
import argparse
import json
from pathlib import Path
from artifact_utils import sha

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);a=p.parse_args()
    folder=a.archive.resolve();reviews=(ROOT/'reviews').resolve()
    assert folder.parent==reviews and folder.is_dir(), 'Select one existing review folder'
    assert (folder/'README.md').is_file() and (folder/'inventory.json').is_file()
    assert not any(v.is_symlink() for v in folder.rglob('*')), 'Archive must contain actual local artifacts'
    target=folder/'checksums.json';assert not target.exists(), 'Never reseal or overwrite a frozen archive'
    values={str(v.relative_to(folder)):sha(v) for v in sorted(folder.rglob('*')) if v.is_file()}
    with target.open('x') as stream:stream.write(json.dumps(values,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(archive=folder.name,files=len(values),sha256=sha(target))))


if __name__=='__main__':main()
