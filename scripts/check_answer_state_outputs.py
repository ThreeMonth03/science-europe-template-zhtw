"""Native answer-state checks and a narrowly allowed 0.3.8 -> 0.3.9 comparison."""
import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString
from docx import Document
from check_narrative_outputs import compact, pdf_text, page_bounds, sha
from check_word_rhythm_outputs import assert_styles, inspect_preview
from compare_runtime_outputs import markers

OLD_LEAD = {
    'english': 'The mapped answers describe storage arrangements and backup needs, but do not establish all operational details:',
    'chinese': '上述對應回答已說明儲存安排與備份需求，但尚無法據此確認所有執行細節：',
}
LEAD = {
    'english': 'The fields mapped by this template are insufficient to establish the following operational details:',
    'chinese': '本模板目前對應的欄位不足以確認以下執行細節：',
}
SUPPORT = {
    'english': {
        'complete': 'We will be able to support this repository for a sufficiently long time.',
        'explicit-no': 'We will not be able to support this repository for a sufficiently long time.',
        'missing': 'Whether we will be able to support this repository for a sufficiently long time has not been specified.',
    },
    'chinese': {
        'complete': '我們能夠長期維運此資料儲存庫。',
        'explicit-no': '我們無法長期維運此資料儲存庫。',
        'missing': '尚未說明能否長期維運此資料儲存庫。',
    },
}


def canonical(node):
    if isinstance(node, NavigableString): return compact(str(node)) or None
    return (node.name, sorted(node.attrs.items()), [v for c in node.children if (v := canonical(c)) is not None])


def compare_prior(before, after, language):
    old, new = copy.deepcopy(before), copy.deepcopy(after)
    assert len(old.select('.question')) == len(new.select('.question')) == 15
    a, b = [s.select_one('#q-store-backup .storage-detail-limits > p') for s in (old, new)]
    assert a.get_text() == OLD_LEAD[language] and b.get_text() == LEAD[language]
    a.string = LEAD[language]
    for n in new.select('#q-data-preservation [data-fact-id="repository-long-term-support"]'):
        assert n.name == 'span' and n.get('data-requirement-id') == 'SE-5b'
        assert n.get_text() == SUPPORT[language][n['data-status']]
        assert n.parent.name == 'li' and n.parent.get('class') == ['repository-distribution']
        if n['data-status'] == 'complete': n.unwrap()
        else: n.decompose()
    for li in new.select('#q-data-preservation li.repository-distribution'):
        assert set(li.attrs) == {'class', 'data-item-id'}
        li.attrs.clear()
    old.smooth(); new.smooth()
    assert markers(old) == markers(new), 'Unexpected fact-marker change'
    for a, b in zip(old.select('.question'), new.select('.question')):
        assert a['id'] == b['id'] and canonical(a) == canonical(b), (a['id'], 'Unexpected question change')
        assert [str(n) for n in a.select('.answer-detail')] == [str(n) for n in b.select('.answer-detail')], 'Authored HTML changed'
    return 15


def expected_support(replies, ids):
    def path(*names): return '.'.join(ids.get(n, n) for n in names)
    data = path('preservingCUuid', 'producedDataQUuid')
    result = []
    for dataset in replies.get(data, []):
        pub = path(data, dataset, 'isPublishedDataQUuid')
        if replies.get(pub) != ids['isPublishedDataYesAUuid']: continue
        dist = path(pub, 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
        for item in replies.get(dist, []):
            kind = path(dist, item, 'publishedDataRepositoryKindQUuid')
            if replies.get(kind) != ids['publishedDataRepositorySpecialAUuid']: continue
            value = replies.get(path(kind, 'publishedDataRepositorySpecialAUuid', 'specialRepoLongTermSupportQUuid'))
            state = {ids['specialRepoLongTermSupportYesAUuid']: 'complete', ids['specialRepoLongTermSupportNoAUuid']: 'explicit-no'}.get(value, 'missing')
            result.append((dataset, item, state))
    return result


def inspect(build, english, case, language, ids):
    stem = f'{case}-{language}'; base = build / 'renders' / stem
    locale = 'en' if language == 'english' else 'zh-Hant'
    fixture = english / 'fixtures/pilot' / locale / (case + '.events.json')
    recipe = fixture.with_name(case + '.json')
    for suffix in ['.html', '.pdf', '.docx']:
        side = json.loads(base.with_suffix(suffix + '.fixture.json').read_text())
        assert side['events_sha256'] == sha(fixture) and side['recipe_sha256'] == sha(recipe)
        assert side['package_sha256'] == sha(build / (language + '.zip'))
    replies = {e['path']: e['value']['value'] for e in json.loads(fixture.read_text())}
    expected = expected_support(replies, ids)
    soup = BeautifulSoup(base.with_suffix('.html').read_text(), 'html.parser')
    q5 = soup.find(id='q-store-backup'); q11 = soup.find(id='q-data-preservation')
    assert q5.select_one('.storage-detail-limits > p').get_text() == LEAD[language]
    nodes = q11.select('[data-fact-id="repository-long-term-support"]')
    assert [(n.find_parent(class_='dataset-section')['data-item-id'], n.parent['data-item-id'], n['data-status']) for n in nodes] == expected
    assert not soup.select('p p, p div, p ul, p table')
    document = Document(base.with_suffix('.docx')); assert_styles(document)
    paragraphs = [p.text for p in document.paragraphs]
    pdf = compact(pdf_text(base.with_suffix('.pdf')))
    preview = build / 'word-preview' / (stem + '.pdf')
    preview_text = compact(pdf_text(preview))  # Required, not silently skipped.
    for text in [LEAD[language]] + [SUPPORT[language][state] for _, _, state in expected]:
        assert compact(text) in pdf and compact(text) in preview_text
        assert any(compact(text) in compact(p) for p in paragraphs), ('Word text lost', text)
    for n in nodes:
        assert n.get_text() == SUPPORT[language][n['data-status']]
        # Support and the existing repository/service prose stay in one list paragraph.
        assert any(compact(n.parent.get_text()) == compact(p) for p in paragraphs), 'Repository prose fragmented'
    return soup, {'case': case, 'language': language, 'passed': True, 'support_states': expected,
                  'pdf_pages': page_bounds(base.with_suffix('.pdf')), 'word_preview_pages': inspect_preview(preview)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--english', type=Path, required=True)
    parser.add_argument('--prior', type=Path, required=True)
    parser.add_argument('--cases', nargs='+', required=True)
    parser.add_argument('--new-cases', nargs='*', default=[])
    args = parser.parse_args()
    sys.path.insert(0, str(args.english.resolve() / 'scripts'))
    from generate_pilot_fixtures import IDS
    assert set(args.new_cases) <= set(args.cases)
    report = {'selected_checks_passed': False, 'release_acceptance': False, 'rows': [],
              'checker_sha256': sha(Path(__file__)),
              'helper_sha256': {n: sha(Path(__file__).with_name(n)) for n in ['check_narrative_outputs.py', 'check_word_rhythm_outputs.py', 'compare_runtime_outputs.py']},
              'package_sha256': {n: sha(args.build / n) for n in ['english.zip', 'chinese.zip']},
              'prior_package_sha256': {n: sha(args.prior / n) for n in ['english.zip', 'chinese.zip']},
              'artifact_sha256': {str(p.relative_to(args.build)): sha(p) for folder in ['renders', 'word-preview'] for p in sorted((args.build / folder).glob('*')) if p.is_file()},
              'prior_artifact_sha256': {}, 'new_cases_without_prior': args.new_cases,
              'limits': ['Selected synthetic Q5/Q11 states only', 'Historical HTML comparison permits only the exact Q5 lead and Q11 support additions', 'LibreOffice is not Microsoft Word acceptance', 'No full SE coverage or release acceptance']}
    target = args.build / 'answer-state-report.json'
    target.write_text(json.dumps(report, indent=2) + '\n')
    try:
        for case in args.cases:
            pair = []
            for language in ['english', 'chinese']:
                soup, row = inspect(args.build, args.english, case, language, IDS); pair.append(soup)
                row['controlled_question_comparisons'] = 0
                if case not in args.new_cases:
                    stem = f'{case}-{language}'
                    old, new = [root / 'renders' / (stem + '.html') for root in [args.prior, args.build]]
                    a, b = [json.loads(p.with_suffix('.html.fixture.json').read_text()) for p in [old, new]]
                    for key in ['recipe_sha256', 'events_sha256', 'km_sha256']: assert a[key] == b[key], (stem, key)
                    for p in [old, old.with_suffix('.html.fixture.json')]: report['prior_artifact_sha256'][str(p.relative_to(args.prior))] = sha(p)
                    row['controlled_question_comparisons'] = compare_prior(BeautifulSoup(old.read_text(), 'html.parser'), soup, language)
                report['rows'].append(row)
            assert markers(pair[0]) == markers(pair[1]), 'Bilingual markers differ'
    except Exception as e:
        report['failure'] = str(e); target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n'); raise
    report['selected_checks_passed'] = True
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': True, 'pairs': len(report['rows']), 'comparisons': sum(r['controlled_question_comparisons'] for r in report['rows'])}))


if __name__ == '__main__': main()
