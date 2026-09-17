"""Preserve the 0.3.20 prompt regression; current deltas need separate exact review."""
import argparse
from collections import Counter
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from artifact_utils import sha
from probe_pdf_budget_translation import pair
from probe_personal_data_translation import archived_pairs, verify_metadata_translation_chain

ROOT = Path(__file__).resolve().parents[1]
PRIOR = '39a3a42da718d29b59513153b8a2b15c8f53701c'
EN = 'Information not provided: the technical and procedural measures for protecting personal data.'
ZH = '尚待補充：保護個人資料所採取的技術與程序措施。'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True); p.add_argument('--english', type=Path, required=True); a = p.parse_args()
    data = subprocess.check_output(['git', '-C', str(ROOT), 'archive', PRIOR, 'translation'])
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        old = [pair(archive.extractfile(f).read().decode()) for f in archive if f.name.endswith('/translation.md')]
    files = sorted((ROOT/'translation/tree').rglob('translation.md')); new = [pair(f.read_text()) for f in files]
    # The immutable 0.3.20 tree still proves its original +1 delta. For the
    # current tree, allow only the separately reviewed Q7/Q9 and Q11 changes;
    # never silently relax to a subset or normalize away punctuation.
    baseline = archived_pairs('3c3d3b38d7346725b7dc2af87b9e8a75d57af7f9')
    assert len(old) == 722 and len(baseline) == 723
    assert not Counter(old) - Counter(baseline)
    assert Counter(baseline) - Counter(old) == Counter({(EN, ZH): 1})
    current_delta, followup_delta = verify_metadata_translation_chain(new)
    manifest = json.loads((a.build/'manifest.json').read_text())
    hashes = {str(f.relative_to(ROOT/'translation')): sha(f) for f in files}
    assert hashes == manifest['translation_tree_sha256']
    sys.path.insert(0, str(a.english.resolve()/'tests'))
    import test_science_europe_contract as adapter
    from test_personal_data_gaps import case, QUESTION, UUIDS
    rows = []
    for folder, text in [('en', EN), ('translated', ZH)]:
        env = Environment(loader=FileSystemLoader(a.build/folder), extensions=['jinja2.ext.do'])
        env.filters.update(reply_path=adapter.reply_path, reply_items=adapter.reply_items, reply_str_value=adapter.reply_str_value, markdown=lambda v: v)
        template = env.from_string("{% import 'src/uuids.j2' as uuids %}{% include '"+QUESTION+"' %}")
        for name, replies, expected in [('partial', case(), 1), ('legal-missing', case(legal=False), 1), ('empty', {}, 0),
                ('no', case(collect='collectPersonalNoAUuid'), 0), ('inactive', case(explore=False), 0),
                ('answered', case(safeguards=UUIDS['cpersGdprSafeguardsAUuid']), 0)]:
            soup = BeautifulSoup(template.render(repliesMap=replies), 'html.parser')
            assert not soup.select('p p, p div, p ul, p table'), (folder, name, 'Invalid paragraph nesting')
            nodes = soup.select('[data-fact-id="personal-data-safeguards"][data-status="missing"]')
            assert len(nodes) == expected
            if nodes: assert nodes[0].get_text() == text
            rows.append({'language': folder, 'case': name, 'gap_count': len(nodes)})
    report = {'passed': True, 'release_acceptance': False, 'prior_commit': PRIOR, 'old_units': len(old), 'new_units': len(new),
              'historical_0_3_20_units': len(baseline), 'current_reviewed_delta': current_delta,
              'followup_reviewed_delta': followup_delta,
              'rows': rows, 'checker_sha256': sha(Path(__file__)), 'translation_tree_sha256': hashes,
              'package_sha256': {n: sha(a.build/n) for n in ['english.zip', 'chinese.zip']},
              'limits': ['Selected safeguards parent question, not all Q7 follow-ups or all Science Europe obligations',
                         'Adapter checks, not native PDF or Microsoft Word visual acceptance']}
    target = a.build/'missing-info-translation-proof.json'; assert not target.exists()
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'passed': True, 'translation_units': len(new), 'branch_language_checks': len(rows)}))


if __name__ == '__main__': main()
