"""Verify resegmented 0.3.19 units preserve exactly the reviewed sentence/translation pairs."""
import argparse
from collections import Counter
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]
PRIOR = '0d4153e6ca43d5ac9438df7f6b428f44906da699'


def pair(text):
    source = re.search(r'### Sentence \(en\)\n\n```text\n(.*?)\n```', text, re.S)
    target = re.search(r'### Translation \(zh_Hant\)\n\n~~~jinja\n(.*?)\n~~~', text, re.S)
    assert source and target and target[1].strip(), 'Missing source or translation'
    return source[1], target[1]


def verify(before, after):
    old, new = Counter(before), Counter(after)
    assert not old - new, 'A reviewed sentence/translation pair was lost or changed'
    extra = Counter({('Currency: {projectCostItemCurrencyReply}.', '幣別：{projectCostItemCurrencyReply}'): 2})
    assert new - old == extra, 'Only two copies of the existing currency branch may be added'


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--build', type=Path, required=True); a = p.parse_args()
    data = subprocess.check_output(['git', '-C', str(ROOT), 'archive', PRIOR, 'translation'])
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        old = [pair(archive.extractfile(f).read().decode()) for f in archive if f.name.endswith('/translation.md')]
    files = sorted((ROOT / 'translation/tree').rglob('translation.md'))
    new = [pair(f.read_text()) for f in files]; assert len(old) == 720 and len(new) == 722
    verify(old, new)
    manifest = json.loads((a.build / 'manifest.json').read_text())
    hashes = {str(f.relative_to(ROOT / 'translation')): sha(f) for f in files}
    assert hashes == manifest['translation_tree_sha256'], 'Proof must match the tested package translation tree'
    report = {'passed': True, 'release_acceptance': False, 'prior_commit': PRIOR,
              'old_units': len(old), 'new_units': len(new), 'added_currency_copies': 2,
              'checker_sha256': sha(Path(__file__)), 'translation_tree_sha256': hashes,
              'package_sha256': {n: sha(a.build / n) for n in ['english.zip', 'chinese.zip']},
              'limits': ['Exact sentence/translation pairs, not a general linguistic quality score',
                         'Placeholders and punctuation are compared without normalization']}
    target = a.build / 'pdf-budget-translation-proof.json'; assert not target.exists()
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': True, 'old_units': len(old), 'new_units': len(new)}))


if __name__ == '__main__': main()
