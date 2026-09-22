"""Freeze PUBLIC synthetic evidence only; never accepts private audit directories."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(build, native, output):
    assert not output.exists()
    report = json.loads((native / 'report.json').read_text())
    manifest = json.loads((build / 'manifest.json').read_text())
    assert report['passed'] and report['synthetic_only'] and not report['native_word']
    assert manifest['status'] == 'prototype' and not manifest['source_integrated']
    assert report['checker_sha256'] == sha(HERE / 'identifier_native.py')
    assert report['packages']['after'] == {language: manifest['sha256'][language + '.zip'] for language in ['english', 'chinese']}
    output.mkdir(parents=True)
    for name in ['manifest.json', 'migration.json', 'english-branch-checks.json', 'chinese-branch-checks.json']:
        target = output / 'build' / name; target.parent.mkdir(exist_ok=True)
        shutil.copyfile(build / name, target)
    names = ['report.json'] + [f'{lang}-{case}-{phase}.pdf' for lang in ['english', 'chinese']
        for case in ['boundary', 'authored'] for phase in ['before', 'after']]
    for name in names:
        target = output / 'native' / name; target.parent.mkdir(exist_ok=True)
        shutil.copyfile(native / name, target)
    inventory = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    (output / 'checksums.json').write_text(json.dumps(inventory, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(public_synthetic_only=True, files=len(inventory), seal_sha256=sha(output / 'checksums.json'))))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ['build', 'native', 'output']: p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args(); collect(a.build, a.native, a.output)
