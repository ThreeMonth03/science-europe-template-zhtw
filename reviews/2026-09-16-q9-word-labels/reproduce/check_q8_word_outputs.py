"""Same-fixture Q8 Word style-only comparison plus unchanged native PDF/HTML."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from artifact_utils import sha
from check_budget_outputs import body, xml, question_body
from check_word_rhythm_outputs import inspect_preview
from check_narrative_outputs import compact
from probe_q8_list_continuity import locations

CASES = ['personal-transfer-complete', 'empty', 'negative', 'preservation-complete', 'q8-long-permissions', 'q8-many-references']


def compare_word(before, after, labels, question=8):
    left, right = body(before), body(after); assert len(left) == len(right)
    allowed = Counter(labels); changed = Counter(); in_q8 = False
    for old, new in zip(left, right):
        assert old.tag == new.tag
        if old.tag == qn('w:p'):
            a, b = Paragraph(old, before), Paragraph(new, after)
            if a.style.name == 'Heading 3': in_q8 = a.text.startswith(str(question)+'. ')
        if xml(old) == xml(new): continue
        assert in_q8 and old.tag == qn('w:p'), f'Non-Q{question} content/style changed'
        a, b = Paragraph(old, before), Paragraph(new, after)
        assert a.text == b.text and allowed[a.text] > changed[a.text]
        assert a.style.name == 'Compact' and b.style.name == 'Pilot List Lead'
        restored = copy.deepcopy(new); props = restored.find(qn('w:pPr'))
        style = props.find(qn('w:pStyle')); assert style is not None; props.remove(style)
        old_props = old.find(qn('w:pPr')); old_style = old_props.find(qn('w:pStyle')) if old_props is not None else None
        if old_style is not None: props.insert(0, copy.deepcopy(old_style))
        if old_props is None and not len(props) and not props.attrib: restored.remove(props)
        assert xml(old) == xml(restored), f'Only the Q{question} label paragraph style may change'
        changed[a.text] += 1
    assert changed == allowed, ('Expected label edits not applied', changed, allowed)
    links = lambda doc: sorted(r.target_ref for r in doc.part.rels.values() if r.is_external)
    assert links(before) == links(after)
    return sum(changed.values())


def eligible_pairs(soup):
    pairs = []
    for item in soup.select('#q-copyright-ipr .answer > ul > li'):
        if len(item.parent.find_all('li', recursive=False)) > 32: continue
        name = item.find('div', recursive=False)
        if name is None or name.attrs or name.find(True): continue
        tail = list(name.next_siblings)
        if any(getattr(n, 'name', None) for n in tail): continue
        label = name.get_text(); permission = ''.join(str(n) for n in tail).strip()
        width = lambda s: sum(2 if ord(c) >= 0x2E80 else 1 for c in s)
        if 0 < width(label) <= 80 and 0 < width(permission) <= 320: pairs.append((label, permission))
    return pairs


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ['build', 'prior', 'new-case-prior', 'english']: p.add_argument('--'+key, type=Path, required=True)
    p.add_argument('--cases', nargs='+', default=CASES); p.add_argument('--output', type=Path)
    a = p.parse_args()
    sys.path.insert(0, str(a.english.resolve()/'scripts'))
    import check_missing_info_outputs as missing
    missing.HERE = a.english.resolve()
    from check_budget_spacing_outputs import pdf_raw_page_texts
    from compare_runtime_outputs import markers
    import subprocess
    report = {'selected_checks_passed': False, 'release_acceptance': False, 'version': '0.3.22', 'rows': [],
              'checker_sha256': sha(Path(__file__)), 'package_sha256': {n: sha(a.build/n) for n in ['english.zip', 'chinese.zip']},
              'limits': ['Only bounded Q8 reference-name/permission pairs receive the Word keep rule',
                         'Long or complex answers are preserved, not made unbreakable', 'LibreOffice preview, not Microsoft Word acceptance']}
    target = a.output or a.build/'q8-word-report.json'; assert not target.exists()
    try:
        for case in a.cases:
            soups = []
            for language in ['english', 'chinese']:
                row, soup = missing.inspect(a.build, case, language); soups.append(soup)
                prior = a.new_case_prior if case.startswith('q8-') else a.prior
                stem = case+'-'+language; old, new = [r/'renders'/stem for r in [prior, a.build]]
                left = BeautifulSoup(old.with_suffix('.html').read_text(), 'html.parser')
                assert len(left.select('.question')) == 15
                assert [str(q) for q in left.select('.question')] == [str(q) for q in soup.select('.question')]
                before = json.loads(old.with_suffix('.html.fixture.json').read_text())
                for fmt in ['html', 'pdf', 'docx']:
                    after = json.loads(new.with_suffix('.'+fmt+'.fixture.json').read_text())
                    for key in ['events_sha256', 'recipe_sha256', 'km_sha256']: assert before[key] == after[key]
                    assert after['package_sha256'] == report['package_sha256'][language+'.zip']
                assert question_body(old.with_suffix('.pdf'), left) == question_body(new.with_suffix('.pdf'), soup)
                assert len(pdf_raw_page_texts(old.with_suffix('.pdf'))) == row['pages']
                pairs = eligible_pairs(soup)
                expected = 0 if case in ['empty','negative'] else 1 if case == 'q8-long-permissions' else 8 if case == 'q8-many-references' else 2
                assert len(pairs) == expected, (case, language, 'Unexpected eligibility')
                row['changed_q8_labels'] = compare_word(Document(old.with_suffix('.docx')), Document(new.with_suffix('.docx')), [label for label, _ in pairs])
                with zipfile.ZipFile(old.with_suffix('.docx')) as x, zipfile.ZipFile(new.with_suffix('.docx')) as y:
                    assert x.read('word/styles.xml') == y.read('word/styles.xml')
                preview = a.build/'word-preview'/(stem+'.pdf'); row['word_pages'] = inspect_preview(preview)
                pages = [s for s in subprocess.check_output(['pdftotext','-raw',str(preview),'-'],text=True).split('\f') if s.strip()]
                entries = locations(pages, soup.select_one('#q-copyright-ipr h3').get_text(), soup.select_one('#q-ethical-issues h3').get_text(), pairs)
                assert all(e['together'] for e in entries), (case, language, entries)
                row['q8_word_pairs'] = entries
                if case == 'q8-long-permissions':
                    paragraphs = soup.select_one('#q-copyright-ipr').select('p')
                    original = [compact(p.get_text()) for p in paragraphs if 'Q8-PARA-' in p.get_text()]
                    assert len(original) == 30
                    raw = list(map(compact, pages)); hits = []
                    for value in original:
                        found = [i for i, page in enumerate(raw, 1) if value in page]
                        # The same author restriction is also retained in Q1;
                        # only Q8's slice is compared by the whole Word XML check.
                        assert found; hits.extend(found)
                    row['long_authored_paragraphs_retained'] = 30
                    row['long_paragraph_pages_including_q1'] = sorted(set(hits))
                    assert len(set(hits)) > 1
                row['unchanged_question_html_pdf_and_word_text'] = True
                row['prior_artifact_sha256'] = {str(old.with_suffix('.'+f)): sha(old.with_suffix('.'+f)) for f in ['html','pdf','docx','html.fixture.json']}
                for file in [new.with_suffix('.docx'),new.with_suffix('.docx.fixture.json'),preview]: row['artifact_sha256'][str(file.relative_to(a.build))] = sha(file)
                report['rows'].append(row)
                print(json.dumps({k:row[k] for k in ['case','language','pages','word_pages','changed_q8_labels','errors','reading_issues']}), flush=True)
            assert markers(soups[0]) == markers(soups[1])
        report['selected_checks_passed'] = len(report['rows']) == len(a.cases)*2 and all(not r['errors'] and not r['reading_issues'] for r in report['rows'])
    except Exception as error:
        report['failure'] = str(error)
        raise
    finally:
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    assert report['selected_checks_passed'], 'See preserved diagnostics'


if __name__ == '__main__': main()
