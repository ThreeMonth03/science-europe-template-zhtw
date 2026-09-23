"""Read-only seal/receipt validation; does not re-render or import private code."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def verify(root, seal_name, expected_sha=None, expected_count=None):
    root = root.resolve()
    seal = root / seal_name
    if expected_sha is not None:
        assert sha(seal) == expected_sha, 'Seal checksum mismatch'
    rows = read(seal)['files']
    names = {r['path'] for r in rows}
    assert len(names) == len(rows) and seal_name not in names
    if expected_count is not None:
        assert len(rows) == expected_count
    for row in rows:
        target = root / row['path']
        assert not Path(row['path']).is_absolute() and not target.is_symlink()
        assert target.resolve().is_relative_to(root)
        assert target.is_file() and sha(target) == row['sha256'], 'Evidence file changed'
    assert {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()} == names | {seal_name}, 'Evidence inventory changed'
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private', type=Path)
    parser.add_argument('--initial-private', type=Path)
    args = parser.parse_args()
    result = dict(public_files=verify(ROOT, 'checksums.json'))
    report, receipt = read(ROOT / 'summary.json'), read(ROOT / 'private-evidence-receipt.json')
    assert report['status'] == 'prototype-validated-not-integrated'
    assert not report['release_acceptance'] and not report['native_ms_word']
    assert report['paired_rebuild_bitwise_identical'] and report['chinese_rerun_child_exit_code'] == 0
    assert read(ROOT / 'completion-checks.json')['passed']
    assert read(ROOT / 'chinese-test-exit.json')['child_exit_code'] == 0
    assert (ROOT / 'build-manifest.json').read_bytes() == (ROOT / 'rebuild-manifest.json').read_bytes()
    for path, key in [(args.private, 'final'), (args.initial_private, 'rejected_initial')]:
        if path is not None:
            item = receipt[key]
            result[key + '_private_files'] = verify(path, 'evidence-sha256.json', item['seal_sha256'], item['file_count'])
    if args.private is not None:
        public_text = '\n'.join(p.read_text() for p in ROOT.rglob('*') if p.is_file())
        for name in ['P19', 'P21']:
            context = read(args.private / 'candidate' / 'contexts' / (name + '.json'))
            project = context['project']
            for key in ['uuid', 'name']:
                value = project.get(key)
                if isinstance(value, str) and len(value) >= 8:
                    assert value not in public_text, 'Private project identifier in public archive'
    print(json.dumps(dict(passed=True,**result)))


if __name__ == '__main__':
    main()
