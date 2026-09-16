"""0.3.27: Q13 only; all 731 source/translation pairs retained exactly."""
import argparse
from collections import Counter
import json
from pathlib import Path
from artifact_utils import sha
from probe_personal_data_translation import archived_pairs
from probe_pdf_budget_translation import pair

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'a09e7c0ff57cded1d11d9db5b6220b2b982279b8'
QUESTION = 'src/questions/13-persistent-identifier.html.j2'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    a = p.parse_args()
    prior = ROOT/'reviews/2026-09-16-word-short-budget'
    previous = json.loads((prior/'candidate-manifest.json').read_text())
    current = json.loads((a.build/'manifest.json').read_text())
    assert current['untranslated_units'] == []
    files = sorted((ROOT/'translation/tree').rglob('translation.md'))
    old_pairs = Counter(archived_pairs(BASELINE)); new_pairs = Counter(pair(f.read_text()) for f in files)
    assert old_pairs == new_pairs and sum(new_pairs.values()) == 731
    hashes = {str(f.relative_to(ROOT/'translation')): sha(f) for f in files}
    assert hashes == current['translation_tree_sha256']
    before = previous['translation_tree_sha256']
    unchanged = {n for n in before if n in hashes and before[n] == hashes[n]}
    assert len(unchanged) == 727
    assert len(before.keys()-hashes.keys()) == len(hashes.keys()-before.keys()) == 4
    prefix = 'tree/' + QUESTION + '/'
    assert all(n.startswith(prefix) for n in before.keys() ^ hashes.keys())
    assert all(before[n] == hashes[n] for n in before.keys() & hashes.keys())
    rows = []
    for row in json.loads((prior/'probes/word-short-budget-scope.json').read_text())['rows']:
        folder = a.build/row['language']; old = row['after']
        new = {str(f.relative_to(folder)): sha(f) for f in (folder/'src').rglob('*') if f.is_file()}
        assert old.keys() == new.keys()
        changed = [n for n in old if old[n] != new[n]]
        assert changed == [QUESTION], (row['language'], changed)
        locale = 'en' if row['language'] == 'en' else 'zh-Hant'
        assert sha(ROOT/'tests/fixtures'/('identifier-0.3.26.'+locale+'.html.j2')) == old[QUESTION]
        rows.append({'language': row['language'], 'before': old, 'after': new, 'changed': changed})
    report = {'passed': True, 'release_acceptance': False, 'rows': rows,
              'unchanged_translation_pairs': 731, 'unchanged_translation_files': 727, 'moved_q13_translation_units': 4,
              'checker_sha256': sha(Path(__file__)), 'translation_baseline': BASELINE,
              'package_sha256': {n: sha(a.build/n) for n in ['english.zip','chinese.zip']},
              'limits': ['HTML output delta is separately checked against frozen Q13 in the bilingual branch matrix',
                         'Version metadata changes; fonts, styles, Lua and all non-Q13 prepared source stay identical']}
    target = a.build/'identifier-concise-scope.json'; assert not target.exists()
    target.write_text(json.dumps(report, indent=2)+'\n')
    print('Q13-only source change; all 731 translation pairs exact, four unit paths moved.')


if __name__ == '__main__':
    main()
