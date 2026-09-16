"""0.3.25 scope: one PDF helper addition and CSS block, no translation changes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from artifact_utils import sha
from probe_q8_word_scope import verify_translations

ROOT = Path(__file__).resolve().parents[1]


def prior_helper(source):
    start = '{%- macro short_table(original, rows) -%}'
    end = '{%- macro ordinary(header, rows) -%}'
    assert source.count(start) == source.count(end) == 1
    before, rest = source.split(start); _, after = rest.split(end)
    restored = before+end+after
    new = '{{ short_table(original, rows) }}'
    assert restored.count(new) == 1
    return restored.replace(new, '{{ original }}', 1)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ['build', 'english']: p.add_argument('--'+key, type=Path, required=True)
    a = p.parse_args(); sys.path.insert(0, str(a.english.resolve()/'scripts'))
    from probe_short_budget import split_css
    prior = ROOT/'reviews/2026-09-16-empty-pdf-reading'
    old = json.loads((prior/'candidate-manifest.json').read_text()); new = json.loads((a.build/'manifest.json').read_text())
    verify_translations(old, new); rows = []
    for row in json.loads((prior/'probes/empty-pdf-scope.json').read_text())['rows']:
        folder = a.build/row['language']; before = row['after']
        after = {str(f.relative_to(folder)): sha(f) for f in (folder/'src').rglob('*') if f.is_file()}
        assert before.keys() == after.keys()
        changed = sorted(name for name in before if before[name] != after[name])
        assert changed == ['src/budget-reading.html.j2', 'src/layout.css'], (row['language'], changed)
        css, _ = split_css((folder/'src/layout.css').read_text())
        helper = prior_helper((folder/'src/budget-reading.html.j2').read_text())
        for name, restored in [('src/layout.css', css), ('src/budget-reading.html.j2', helper)]:
            assert hashlib.sha256(restored.encode()).hexdigest() == before[name], (row['language'], name, 'Unexpected change')
        rows.append({'language': row['language'], 'changed': changed, 'before': before, 'after': after})
    report = {'passed': True, 'release_acceptance': False, 'unchanged_translation_files': 731, 'rows': rows,
        'checker_sha256': sha(Path(__file__)), 'prior_manifest_sha256': sha(prior/'candidate-manifest.json'),
        'prior_scope_sha256': sha(prior/'probes/empty-pdf-scope.json'),
        'package_sha256': {n: sha(a.build/n) for n in ['english.zip', 'chinese.zip']}}
    out = a.build/'short-budget-scope.json'; assert not out.exists()
    out.write_text(json.dumps(report, indent=2)+'\n')
    print('Short-budget scope passed: 731 translations unchanged; bounded helper and CSS only.')


if __name__ == '__main__': main()
