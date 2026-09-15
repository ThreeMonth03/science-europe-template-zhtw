"""Exact reviewed 0.3.21 translation delta and bilingual Q7/Q9 branch contracts."""
import argparse
from collections import Counter
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from bs4 import BeautifulSoup
from artifact_utils import sha
from probe_pdf_budget_translation import pair

ROOT = Path(__file__).resolve().parents[1]
DELTA = ROOT/'docs/personal-data-translation-delta.json'


def archived_pairs(ref):
    data = subprocess.check_output(['git', '-C', str(ROOT), 'archive', ref, 'translation'])
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        return [pair(archive.extractfile(f).read().decode()) for f in archive if f.name.endswith('/translation.md')]


def verify_tree(current):
    delta = json.loads(DELTA.read_text())
    old = Counter(archived_pairs(delta['baseline'])); new = Counter(current)
    assert sum(old.values()) == delta['baseline_units']
    assert sum(new.values()) == delta['current_units']
    assert old-new == Counter(map(tuple, delta['removed'])), 'Unreviewed lost/changed translation'
    assert new-old == Counter(map(tuple, delta['added'])), 'Unreviewed new translation'
    assert sum((old & new).values()) == delta['retained_units']
    return delta


EXPECTED = {
    'personal-followups-empty': {'personal-data-other-legal-basis', 'personal-data-identifiability',
                                'personal-data-additional-safeguards', 'personal-data-transfer'},
    'personal-transfer-missing': {'personal-data-legal-basis', 'personal-data-transfer-measures'},
    'personal-transfer-complete': set(), 'personal-transfer-no': set(),
    'personal-data-partial': {'personal-data-safeguards'}, 'empty': set(),
    'negative': set(), 'preservation-complete': set(),
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True); p.add_argument('--english', type=Path, required=True)
    a = p.parse_args()
    sys.path.insert(0, str(a.english.resolve()/'tests')); sys.path.insert(0, str(a.english.resolve()/'scripts'))
    import test_science_europe_contract as adapter
    from generate_personal_data_fixtures import personal_data_cases, personal_paths, IDS
    files = sorted((ROOT/'translation/tree').rglob('translation.md'))
    delta = verify_tree([pair(f.read_text()) for f in files])
    hashes = {str(f.relative_to(ROOT/'translation')): sha(f) for f in files}
    assert hashes == json.loads((a.build/'manifest.json').read_text())['translation_tree_sha256']
    rows = []; paths = personal_paths()
    for language, folder, locale in [('english', 'en', 'en'), ('chinese', 'translated', 'zh-Hant')]:
        adapter.ROOT = a.build/folder
        def render(question, replies):
            soup = BeautifulSoup(adapter.render_question('src/questions/'+question+'.html.j2', replies), 'html.parser')
            assert not soup.select('p p, p div, p ul, p ol, p table'), (language, question, 'Malformed block nesting')
            return soup
        cases = personal_data_cases(locale)
        for name, values in cases.items():
            replies = {k: ({'value': {'value': v['value']}} if v['type'] == 'IntegrationReply' else v['value']) for k, v in values.items()}
            if name in ['personal-transfer-complete', 'personal-transfer-no', 'personal-transfer-missing']:
                replies[paths['additional']] = '<p>Keep <strong>Original.csv</strong>.</p><p>Second.</p><ul><li>Keep order.</li></ul>'
            if name == 'personal-transfer-complete':
                replies[paths['measures']] = '<p>First.</p><p><a href="https://example.org/transfer?a=1&amp;b=2">Record</a>.</p><ul><li>Retain.</li></ul>'
            q7, q9 = [render(q, replies) for q in ['07-personal-data', '09-ethical-issues']]
            facts = {n['data-fact-id'] for n in q7.select('[data-fact-id][data-status="missing"]')}
            assert facts == EXPECTED[name], (language, name, facts)
            for field, fact in [('additional', 'personal-data-additional-safeguards'), ('measures', 'personal-data-transfer-measures')]:
                detail = q7.select_one('[data-fact-id="'+fact+'"][data-status="complete"]')
                if detail:
                    original = BeautifulSoup(replies[paths[field]], 'html.parser')
                    assert detail.decode_contents() == original.decode_contents(), (language, name, 'Author blocks changed')
                    assert detail.find_previous_sibling().get('class') == ['answer-lead']
            text = q9.get_text(' ', strip=True)
            assert 'We explored' not in text and '我們已檢視歐盟' not in text
            assert 'more important than the privacy' not in text and '高於資料主體的隱私利益' not in text
            if name == 'personal-followups-empty':
                phrase = delta['added'][-1][0 if language == 'english' else 1]
                assert phrase in text
                assert not any(v in text for v in ['consent-based:', '不受倫理法規', 'not subject to ethical legislation'])
            rows.append({'language': language, 'case': name, 'missing_facts': sorted(facts), 'passed': True})
        # Stale descendants are deliberately *not* valid native fixtures, but
        # must still never leak through a No/missing parent in adapter probes.
        for parent in ['parent', 'safeguards', 'transfer']:
            for choice in dict.fromkeys(['', IDS['collectPersonalNoAUuid'] if parent == 'parent' else
                                         IDS['cpersGdprSafeguardsTransferNoAUuid'] if parent == 'transfer' else '']):
                replies = {k: v['value'] for k, v in cases['personal-transfer-complete'].items()}
                replies[paths[parent]] = choice; replies[paths['measures']] = 'STALE-MEASURES'
                q7 = render('07-personal-data', replies)
                assert 'STALE-MEASURES' not in q7.get_text()
                rows.append({'language': language, 'case': 'stale-'+parent+'-'+('missing' if not choice else 'no'), 'passed': True})
    report = {'passed': True, 'release_acceptance': False, 'rows': rows,
              'translation_delta': delta, 'checker_sha256': sha(Path(__file__)), 'delta_sha256': sha(DELTA),
              'translation_tree_sha256': hashes,
              'package_sha256': {n: sha(a.build/n) for n in ['english.zip', 'chinese.zip']},
              'limits': ['Adapter probes use already-rendered HTML for block answers; native worker Markdown is checked separately',
                         'Selected Q7/Q9 paths, not a legal-compliance determination or full DMP acceptance']}
    target = a.build/'personal-data-translation-proof.json'; assert not target.exists()
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'passed': True, 'checks': len(rows), 'retained_pairs': delta['retained_units'], 'units': len(files)}))


if __name__ == '__main__': main()
